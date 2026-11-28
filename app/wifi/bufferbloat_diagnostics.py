"""Sequential idle/download/upload/combined bufferbloat evaluator with NetGuard QoS coordination."""

from __future__ import annotations

import asyncio
import statistics
import time
import uuid
from typing import Any, Callable, List, Optional

from app.traffic.bufferbloat import BufferbloatEvaluator
from app.wifi.coordinator import (
    ApprovalRequiredError,
    CancellationToken,
    DiagnosticBusyError,
    DiagnosticCoordinator,
    MeetingSafetyFreezeError,
)
from app.wifi.models import BufferbloatDiagnosticsReport, BufferbloatPhaseResult, utc_now
from app.wifi.network_diagnostics import _compute_jitter, _percentile
from app.wifi.speed_test import (
    DEFAULT_DOWNLOAD_ENDPOINT,
    DEFAULT_UPLOAD_ENDPOINT,
    _stream_download_worker,
    _stream_upload_worker,
)


class BufferbloatDiagnosticsService:
    """Measures idle latency and loaded download/upload/combined latency spikes sequentially."""

    def __init__(
        self,
        *,
        platform: Any,
        coordinator: DiagnosticCoordinator,
        download_url: str = DEFAULT_DOWNLOAD_ENDPOINT,
        upload_url: str = DEFAULT_UPLOAD_ENDPOINT,
        download_worker_fn: Optional[Callable[[str, float, Optional[CancellationToken]], int]] = None,
        upload_worker_fn: Optional[Callable[[str, int, float, Optional[CancellationToken]], int]] = None,
    ) -> None:
        self._platform = platform
        self._coordinator = coordinator
        self._download_url = download_url
        self._upload_url = upload_url
        self._download_worker = download_worker_fn or _stream_download_worker
        self._upload_worker = upload_worker_fn or _stream_upload_worker

    async def _probe_pings_during_window(
        self,
        target_ip: str,
        duration_sec: float,
        interval_sec: float,
        token: Optional[CancellationToken],
    ) -> tuple[int, List[float]]:
        rtts: List[float] = []
        sent = 0
        deadline = time.monotonic() + duration_sec
        while time.monotonic() < deadline:
            if token and token.is_cancelled:
                break
            sent += 1
            try:
                res = self._platform.ping(target_ip, timeout_sec=0.8)
                if asyncio.iscoroutine(res) or hasattr(res, "__await__"):
                    res = await res
                if isinstance(res, tuple) and len(res) >= 2:
                    if bool(res[0]) and res[1] is not None:
                        rtts.append(float(res[1]))
                elif getattr(res, "success", False) and getattr(res, "latency_ms", None) is not None:
                    rtts.append(float(res.latency_ms))
            except Exception:
                pass
            await asyncio.sleep(interval_sec)
        return sent, rtts

    @staticmethod
    def _build_phase(
        *,
        phase: str,
        target_ip: str,
        started_at: Any,
        completed_at: Any,
        sent: int,
        rtts: List[float],
        idle_baseline_ms: Optional[float],
        throughput_mbps: Optional[float] = None,
    ) -> BufferbloatPhaseResult:
        recv = len(rtts)
        loss = round(((sent - recv) / max(1, sent)) * 100.0, 2)
        if not rtts:
            return BufferbloatPhaseResult(
                phase=phase,  # type: ignore[arg-type]
                target_ip=target_ip,
                started_at=started_at,
                completed_at=completed_at,
                packets_sent=sent,
                packets_received=0,
                packet_loss_pct=loss,
                throughput_mbps=throughput_mbps,
            )
        avg_v = round(statistics.fmean(rtts), 2)
        p95_v = _percentile(rtts, 95.0)
        delta: Optional[float] = None
        grade_str: Optional[str] = None
        if idle_baseline_ms is not None:
            # Evaluate loaded latency inflation cleanly with existing NetGuard BufferbloatEvaluator
            ref_val = p95_v if p95_v is not None else avg_v
            delta = round(max(0.0, ref_val - idle_baseline_ms), 2)
            grade_obj = BufferbloatEvaluator.calculate_grade(delta)
            grade_str = grade_obj.value
        return BufferbloatPhaseResult(
            phase=phase,  # type: ignore[arg-type]
            target_ip=target_ip,
            started_at=started_at,
            completed_at=completed_at,
            packets_sent=sent,
            packets_received=recv,
            packet_loss_pct=loss,
            avg_ms=avg_v,
            min_ms=round(min(rtts), 2),
            p95_ms=p95_v,
            max_ms=round(max(rtts), 2),
            jitter_ms=_compute_jitter(rtts),
            delta_over_idle_ms=delta,
            grade=grade_str,
            throughput_mbps=throughput_mbps,
        )

    async def run_bufferbloat_test(
        self,
        *,
        target_ip: str = "1.1.1.1",
        phase_duration_sec: float = 4.0,
        ping_interval_sec: float = 0.15,
        cooldown_sec: float = 1.0,
        include_upload: bool = True,
        include_combined: bool = False,
        compare_idle_without_qos: bool = False,
        explicit_qos_suspend_approval: bool = False,
    ) -> BufferbloatDiagnosticsReport:
        """Execute idle -> download load -> drain -> upload load -> optional combined load sequentially."""
        started = utc_now()
        run_id = uuid.uuid4().hex[:10]
        qos_info = self._coordinator.get_qos_status_summary()

        if self._platform is None or not hasattr(self._platform, "ping"):
            return BufferbloatDiagnosticsReport(
                run_id=run_id,
                started_at=started,
                completed_at=utc_now(),
                status="failed",
                target_ip=target_ip,
                qos_was_active=bool(qos_info["master_enabled"]),
                qos_policies_count=int(qos_info["active_policies_count"]),
                summary="Bufferbloat test unavailable: platform ping adapter is missing.",
                notes=["Bufferbloat diagnostics failed because no platform ICMP ping adapter was supplied."],
            )

        if compare_idle_without_qos and not explicit_qos_suspend_approval:
            return BufferbloatDiagnosticsReport(
                run_id=run_id,
                started_at=started,
                completed_at=utc_now(),
                status="failed",
                target_ip=target_ip,
                notes=[
                    "Explicit user confirmation is required before temporarily suspending NetGuard QoS for idle comparison."
                ],
            )

        try:
            async with self._coordinator.async_exclusive(
                "bufferbloat_test", "Sequential bufferbloat evaluation"
            ) as token:
                loop = asyncio.get_running_loop()

                # Phase 1: Idle baseline
                self._coordinator.update_progress(15.0, "idle_baseline")
                idle_t0 = utc_now()
                idle_sent, idle_rtts = await self._probe_pings_during_window(
                    target_ip, min(3.0, phase_duration_sec), ping_interval_sec, token
                )
                idle_phase = self._build_phase(
                    phase="idle",
                    target_ip=target_ip,
                    started_at=idle_t0,
                    completed_at=utc_now(),
                    sent=idle_sent,
                    rtts=idle_rtts,
                    idle_baseline_ms=None,
                )
                idle_ref_ms = idle_phase.p95_ms if idle_phase.p95_ms is not None else idle_phase.avg_ms
                if idle_ref_ms is None or idle_phase.packets_received == 0:
                    return BufferbloatDiagnosticsReport(
                        run_id=run_id,
                        started_at=started,
                        completed_at=utc_now(),
                        status="failed",
                        target_ip=target_ip,
                        idle_phase=idle_phase,
                        qos_was_active=bool(qos_info["master_enabled"]),
                        qos_policies_count=int(qos_info["active_policies_count"]),
                        summary="Bufferbloat test inconclusive: all idle baseline ICMP probes failed (100% loss).",
                        notes=[
                            f"Idle phase sent {idle_sent} ICMP probes to {target_ip} and received 0 replies; refusing to fabricate a 0 ms baseline.",
                            f"NetGuard QoS status during test: {qos_info['summary']}",
                        ],
                    )

                if token.is_cancelled:
                    return BufferbloatDiagnosticsReport(
                        run_id=run_id,
                        started_at=started,
                        completed_at=utc_now(),
                        status="cancelled",
                        target_ip=target_ip,
                        idle_phase=idle_phase,
                        notes=["Cancelled during idle baseline phase."],
                    )

                # Phase 2: Download Load + concurrent ICMP probe
                self._coordinator.update_progress(40.0, "download_load")
                dl_t0 = utc_now()
                dl_wall_t0 = time.monotonic()
                dl_load_future = loop.run_in_executor(
                    None, self._download_worker, self._download_url, phase_duration_sec, token
                )
                dl_ping_future = self._probe_pings_during_window(
                    target_ip, phase_duration_sec, ping_interval_sec, token
                )
                dl_res, ping_res = await asyncio.gather(
                    dl_load_future, dl_ping_future, return_exceptions=True
                )
                dl_bytes_res = dl_res if isinstance(dl_res, int) else 0
                dl_sent, dl_rtts = (
                    ping_res if isinstance(ping_res, tuple) and len(ping_res) == 2 else (0, [])
                )
                dl_elapsed = max(0.05, time.monotonic() - dl_wall_t0)
                dl_mbps = (
                    round((int(dl_bytes_res) * 8.0) / (dl_elapsed * 1_000_000.0), 2)
                    if isinstance(dl_bytes_res, int) and dl_bytes_res > 0
                    else None
                )
                dl_phase = self._build_phase(
                    phase="download_load",
                    target_ip=target_ip,
                    started_at=dl_t0,
                    completed_at=utc_now(),
                    sent=dl_sent,
                    rtts=dl_rtts,
                    idle_baseline_ms=idle_ref_ms,
                    throughput_mbps=dl_mbps,
                )

                await asyncio.sleep(cooldown_sec)

                # Phase 3: Upload Load + concurrent ICMP probe
                ul_phase: Optional[BufferbloatPhaseResult] = None
                if include_upload and not token.is_cancelled:
                    self._coordinator.update_progress(68.0, "upload_load")
                    ul_t0 = utc_now()
                    ul_wall_t0 = time.monotonic()
                    ul_load_future = loop.run_in_executor(
                        None,
                        self._upload_worker,
                        self._upload_url,
                        4_000_000,
                        phase_duration_sec,
                        token,
                    )
                    ul_ping_future = self._probe_pings_during_window(
                        target_ip, phase_duration_sec, ping_interval_sec, token
                    )
                    try:
                        ul_bytes_res = await ul_load_future
                    except Exception:
                        ul_bytes_res = 0
                    ul_sent, ul_rtts = await ul_ping_future
                    ul_elapsed = max(0.05, time.monotonic() - ul_wall_t0)
                    ul_mbps = (
                        round((int(ul_bytes_res) * 8.0) / (ul_elapsed * 1_000_000.0), 2)
                        if isinstance(ul_bytes_res, int) and ul_bytes_res > 0
                        else None
                    )
                    ul_phase = self._build_phase(
                        phase="upload_load",
                        target_ip=target_ip,
                        started_at=ul_t0,
                        completed_at=utc_now(),
                        sent=ul_sent,
                        rtts=ul_rtts,
                        idle_baseline_ms=idle_ref_ms,
                        throughput_mbps=ul_mbps,
                    )
                    await asyncio.sleep(cooldown_sec)

                # Phase 4: Optional Combined bidirectional load
                comb_phase: Optional[BufferbloatPhaseResult] = None
                if include_combined and not token.is_cancelled:
                    self._coordinator.update_progress(85.0, "combined_load")
                    c_t0 = utc_now()
                    dl_f = loop.run_in_executor(
                        None, self._download_worker, self._download_url, phase_duration_sec, token
                    )
                    ul_f = loop.run_in_executor(
                        None, self._upload_worker, self._upload_url, 4_000_000, phase_duration_sec, token
                    )
                    c_ping = self._probe_pings_during_window(
                        target_ip, phase_duration_sec, ping_interval_sec, token
                    )
                    for fut in (dl_f, ul_f):
                        try:
                            await fut
                        except Exception:
                            pass
                    c_sent, c_rtts = await c_ping
                    comb_phase = self._build_phase(
                        phase="combined_load",
                        target_ip=target_ip,
                        started_at=c_t0,
                        completed_at=utc_now(),
                        sent=c_sent,
                        rtts=c_rtts,
                        idle_baseline_ms=idle_ref_ms,
                    )

                # Worst grade across tested download & upload phases
                grade_rank = {"A+": 0, "A": 1, "B": 2, "C": 3, "D": 4, "F": 5}
                grades = [
                    g
                    for g in (
                        dl_phase.grade if dl_phase else None,
                        ul_phase.grade if ul_phase else None,
                        comb_phase.grade if comb_phase else None,
                    )
                    if g
                ]
                overall_grade = (
                    max(grades, key=lambda g: grade_rank.get(g, 2)) if grades else None
                )

                notes = [
                    f"Download & Upload phases ran sequentially with {cooldown_sec}s queue drain pause.",
                    f"NetGuard QoS status during test: {qos_info['summary'].rstrip('.')}.",
                ]

                idle_comp_run = False
                idle_comp_verified: Optional[bool] = None
                idle_comp_summary: Optional[str] = None
                if compare_idle_without_qos and explicit_qos_suspend_approval and not token.is_cancelled:
                    async def _no_qos_idle() -> float:
                        _, rtts_no_qos = await self._probe_pings_during_window(
                            target_ip, min(2.0, phase_duration_sec), ping_interval_sec, token
                        )
                        return round(statistics.median(rtts_no_qos), 2) if rtts_no_qos else 0.0

                    no_qos_med, audit = await self._coordinator.run_with_optional_idle_qos_suspension(
                        explicit_user_approval=True, callback=_no_qos_idle
                    )
                    idle_comp_run = True
                    idle_comp_verified = audit.post_restore_verified
                    idle_comp_summary = (
                        f"Idle median with QoS suspended={no_qos_med} ms vs baseline={idle_phase.avg_ms} ms; "
                        f"{audit.summary}"
                    )
                    notes.append(idle_comp_summary)

                dl_delta_txt = (
                    f"+{dl_phase.delta_over_idle_ms} ms"
                    if dl_phase.delta_over_idle_ms is not None
                    else "N/A"
                )
                dl_grade_txt = dl_phase.grade or "N/A"
                ul_part = ""
                if ul_phase:
                    ul_delta_txt = (
                        f"+{ul_phase.delta_over_idle_ms} ms"
                        if ul_phase.delta_over_idle_ms is not None
                        else "N/A"
                    )
                    ul_part = f", UL {ul_delta_txt} [{ul_phase.grade or 'N/A'}]"
                summary = (
                    f"Bufferbloat overall grade {overall_grade or 'N/A'} "
                    f"(DL {dl_delta_txt} [{dl_grade_txt}]{ul_part})."
                )

                return BufferbloatDiagnosticsReport(
                    run_id=run_id,
                    started_at=started,
                    completed_at=utc_now(),
                    status="completed",
                    target_ip=target_ip,
                    idle_phase=idle_phase,
                    download_phase=dl_phase,
                    upload_phase=ul_phase,
                    combined_phase=comb_phase,
                    download_bloat_grade=dl_phase.grade,
                    upload_bloat_grade=ul_phase.grade if ul_phase else None,
                    overall_grade=overall_grade,
                    qos_was_active=bool(qos_info["master_enabled"]),
                    qos_policies_count=int(qos_info["active_policies_count"]),
                    idle_qos_comparison_run=idle_comp_run,
                    idle_qos_pre_post_verified=idle_comp_verified,
                    idle_qos_comparison_summary=idle_comp_summary,
                    summary=summary,
                    notes=notes,
                )

        except (MeetingSafetyFreezeError, DiagnosticBusyError, ApprovalRequiredError) as exc:
            status = "blocked_meeting" if isinstance(exc, MeetingSafetyFreezeError) else "blocked_busy"
            return BufferbloatDiagnosticsReport(
                run_id=run_id,
                started_at=started,
                completed_at=utc_now(),
                status=status,  # type: ignore[arg-type]
                target_ip=target_ip,
                qos_was_active=bool(qos_info["master_enabled"]),
                qos_policies_count=int(qos_info["active_policies_count"]),
                summary=str(exc),
                notes=[str(exc)],
            )


BufferbloatAnalyzer = BufferbloatDiagnosticsService
