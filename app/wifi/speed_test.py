"""Controllable Internet speed test separating Wi-Fi PHY link rate, LAN speed, and Internet WAN throughput."""

from __future__ import annotations

import asyncio
import http.client
import json
import shutil
import socket
import ssl
import subprocess
import time
import urllib.parse
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, List, Optional, Tuple

from app.wifi.coordinator import (
    CancellationToken,
    DiagnosticBusyError,
    DiagnosticCoordinator,
    MeetingSafetyFreezeError,
)
from app.wifi.models import SpeedTestReport, utc_now
from app.wifi.telemetry import WifiTelemetryService

DEFAULT_DOWNLOAD_ENDPOINT = "https://speed.cloudflare.com/__down?bytes=25000000"
DEFAULT_UPLOAD_ENDPOINT = "https://speed.cloudflare.com/__up"
FALLBACK_DOWNLOAD_ENDPOINTS: Tuple[Tuple[str, str], ...] = (
    ("Cloudflare Edge Speed Endpoint", DEFAULT_DOWNLOAD_ENDPOINT),
    ("OVH Proof Speed Endpoint", "https://proof.ovh.net/files/10Mb.dat"),
    ("CacheFly CDN Speed Endpoint", "https://cachefly.cachefly.net/10mb.test"),
)


def _stream_download_worker(
    url: str,
    max_duration_sec: float,
    token: Optional[CancellationToken],
    chunk_size: int = 65536,
) -> int:
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname or ""
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = parsed.path + (f"?{parsed.query}" if parsed.query else "")
    deadline = time.monotonic() + max_duration_sec

    if parsed.scheme == "https":
        ctx = ssl.create_default_context()
        conn: http.client.HTTPConnection = http.client.HTTPSConnection(
            host, port, timeout=5.0, context=ctx
        )
    else:
        conn = http.client.HTTPConnection(host, port, timeout=5.0)

    total_bytes = 0
    try:
        conn.request(
            "GET",
            path or "/",
            headers={"User-Agent": "NetGuardAI-Diag/1.0", "Cache-Control": "no-store"},
        )
        resp = conn.getresponse()
        if resp.status >= 400:
            raise RuntimeError(f"Speed download endpoint returned HTTP {resp.status}")
        while time.monotonic() < deadline:
            if token and token.is_cancelled:
                break
            chunk = resp.read(chunk_size)
            if not chunk:
                break
            total_bytes += len(chunk)
    finally:
        conn.close()
    return total_bytes


def _stream_upload_worker(
    url: str,
    payload_bytes: int,
    max_duration_sec: float,
    token: Optional[CancellationToken],
) -> int:
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname or ""
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = parsed.path + (f"?{parsed.query}" if parsed.query else "")

    if parsed.scheme == "https":
        ctx = ssl.create_default_context()
        conn: http.client.HTTPConnection = http.client.HTTPSConnection(
            host, port, timeout=8.0, context=ctx
        )
    else:
        conn = http.client.HTTPConnection(host, port, timeout=8.0)

    data = b"\x55" * payload_bytes
    sent = 0
    try:
        conn.putrequest("POST", path or "/")
        conn.putheader("User-Agent", "NetGuardAI-Diag/1.0")
        conn.putheader("Content-Type", "application/octet-stream")
        conn.putheader("Content-Length", str(len(data)))
        conn.endheaders()

        step = 65536
        deadline = time.monotonic() + max_duration_sec
        pos = 0
        while pos < len(data) and time.monotonic() < deadline:
            if token and token.is_cancelled:
                break
            end = min(len(data), pos + step)
            conn.send(data[pos:end])
            sent += end - pos
            pos = end

        resp = conn.getresponse()
        resp.read(1024)
        if resp.status >= 400:
            raise RuntimeError(f"Speed upload endpoint returned HTTP {resp.status}")
    finally:
        conn.close()
    return sent


def _tcp_rtt_probe(host: str, port: int = 443, count: int = 4, timeout_s: float = 1.2) -> Tuple[Optional[float], Optional[float], float]:
    """Measure real TCP connect RTT samples (avg_ms, jitter_ms, loss_pct)."""
    if not host:
        return None, None, 100.0
    samples: List[float] = []
    for _ in range(max(1, count)):
        t0 = time.perf_counter()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout_s)
        try:
            s.connect((host, port))
            samples.append((time.perf_counter() - t0) * 1000.0)
        except OSError:
            pass
        finally:
            try:
                s.close()
            except OSError:
                pass
        time.sleep(0.05)

    loss_pct = round(((count - len(samples)) / count) * 100.0, 1)
    if not samples:
        return None, None, loss_pct
    avg_ms = round(sum(samples) / len(samples), 2)
    if len(samples) >= 2:
        diffs = [abs(samples[i] - samples[i - 1]) for i in range(1, len(samples))]
        jitter_ms = round(sum(diffs) / len(diffs), 2)
    else:
        jitter_ms = 0.0
    return avg_ms, jitter_ms, loss_pct


class SpeedTestService:
    """User-controllable Internet speed test isolating Wi-Fi link rate, LAN speed, and WAN speed."""

    def __init__(
        self,
        *,
        coordinator: DiagnosticCoordinator,
        wifi_telemetry: Optional[WifiTelemetryService] = None,
        download_url: str = DEFAULT_DOWNLOAD_ENDPOINT,
        upload_url: str = DEFAULT_UPLOAD_ENDPOINT,
        server_name: str = "Cloudflare Edge Speed Endpoint",
        download_worker_fn: Optional[Callable[[str, float, Optional[CancellationToken]], int]] = None,
        upload_worker_fn: Optional[Callable[[str, int, float, Optional[CancellationToken]], int]] = None,
    ) -> None:
        self._coordinator = coordinator
        self._wifi_telemetry = wifi_telemetry
        self._download_url = download_url
        self._upload_url = upload_url
        self._server_name = server_name
        self._custom_download = download_worker_fn is not None
        self._custom_upload = upload_worker_fn is not None
        self._download_worker = download_worker_fn or _stream_download_worker
        self._upload_worker = upload_worker_fn or _stream_upload_worker

    @staticmethod
    def _try_speedtest_cli() -> Optional[Dict[str, Any]]:
        exe = shutil.which("speedtest")
        if not exe:
            return None
        try:
            proc = subprocess.run(
                [exe, "--format=json", "--accept-license", "--accept-gdpr"],
                capture_output=True,
                text=True,
                timeout=35,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if proc.returncode == 0 and proc.stdout.strip().startswith("{"):
                return json.loads(proc.stdout)
        except Exception:
            pass
        return None

    async def run_speed_test(
        self,
        *,
        run_upload: bool = False,
        streams: int = 3,
        max_download_sec: float = 8.0,
        upload_payload_mb: int = 4,
        max_upload_sec: float = 8.0,
        router_wan_down_mbps: Optional[float] = None,
        router_wan_up_mbps: Optional[float] = None,
    ) -> SpeedTestReport:
        """Measure actual Internet DL/UL, idle/loaded latency, jitter, and loss under single-flight guard."""
        started = utc_now()
        run_id = uuid.uuid4().hex[:10]

        wifi_tx: Optional[float] = None
        wifi_rx: Optional[float] = None
        iface_name: Optional[str] = None
        ssid: Optional[str] = None
        bssid: Optional[str] = None
        band: Optional[str] = None
        if self._wifi_telemetry is not None:
            try:
                tel = await self._wifi_telemetry.collect_telemetry(
                    include_events=False, include_ps_driver_stats=False
                )
                wifi_tx = tel.tx_link_rate_mbps
                wifi_rx = tel.rx_link_rate_mbps
                iface_name = tel.interface_name
                ssid = tel.ssid
                bssid = tel.bssid
                band = tel.band
            except Exception:
                pass

        qos_info = self._coordinator.get_qos_status_summary()

        try:
            async with self._coordinator.async_exclusive(
                "speed_test", "Internet download/upload throughput measurement"
            ) as token:
                loop = asyncio.get_running_loop()

                # 1) Measure genuine idle latency + jitter before loading the connection (real network only)
                idle_lat: Optional[float] = None
                jitter: Optional[float] = None
                pkt_loss: Optional[float] = None
                parsed_ep = urllib.parse.urlparse(self._download_url)
                ep_host = parsed_ep.hostname or ""
                ep_port = parsed_ep.port or (443 if parsed_ep.scheme == "https" else 80)

                if not self._custom_download and ep_host:
                    self._coordinator.update_progress(10.0, "idle_latency")
                    idle_lat, jitter, pkt_loss = await asyncio.to_thread(_tcp_rtt_probe, ep_host, ep_port, 4, 1.0)

                # 2) Download test (with endpoint fallback on real runs)
                self._coordinator.update_progress(25.0, "downloading")
                candidates: List[Tuple[str, str]] = [(self._server_name, self._download_url)]
                if not self._custom_download:
                    for sname, surl in FALLBACK_DOWNLOAD_ENDPOINTS:
                        if surl != self._download_url:
                            candidates.append((sname, surl))

                used_server_name = self._server_name
                used_server_url = self._download_url
                valid_dl: List[int] = []
                dl_errors: List[str] = []
                dl_elapsed = 0.1
                loaded_dl_lat: Optional[float] = None

                for cand_name, cand_url in candidates:
                    if token.is_cancelled:
                        break
                    c_parsed = urllib.parse.urlparse(cand_url)
                    c_host = c_parsed.hostname or ep_host
                    c_port = c_parsed.port or (443 if c_parsed.scheme == "https" else 80)

                    dl_t0 = time.monotonic()
                    with ThreadPoolExecutor(max_workers=max(1, streams) + 1) as pool:
                        tasks = [
                            loop.run_in_executor(
                                pool, self._download_worker, cand_url, max_download_sec, token
                            )
                            for _ in range(max(1, streams))
                        ]
                        probe_fut = (
                            loop.run_in_executor(pool, _tcp_rtt_probe, c_host, c_port, 4, 1.2)
                            if (not self._custom_download and c_host)
                            else None
                        )
                        dl_results = await asyncio.gather(*tasks, return_exceptions=True)
                        if probe_fut is not None:
                            try:
                                loaded_dl_lat, _, _ = await probe_fut
                            except Exception:
                                loaded_dl_lat = None

                    dl_elapsed = max(0.05, time.monotonic() - dl_t0)
                    valid_dl = [r for r in dl_results if isinstance(r, int) and r > 0]
                    errs = [str(r) for r in dl_results if isinstance(r, Exception)]
                    if valid_dl:
                        used_server_name = cand_name
                        used_server_url = cand_url
                        dl_errors = errs
                        break
                    dl_errors.extend(errs or [f"{cand_name}: 0 bytes received"])

                if token.is_cancelled:
                    return SpeedTestReport(
                        run_id=run_id,
                        started_at=started,
                        completed_at=utc_now(),
                        status="cancelled",
                        server_name=used_server_name,
                        server_url=used_server_url,
                        wifi_tx_link_rate_mbps=wifi_tx,
                        wifi_rx_link_rate_mbps=wifi_rx,
                        qos_active_during_test=bool(qos_info["master_enabled"]),
                        qos_policies_count=int(qos_info["active_policies_count"]),
                        qos_summary=str(qos_info["summary"]),
                        interface_name=iface_name,
                        ssid=ssid,
                        bssid=bssid,
                        band=band,
                        idle_latency_ms=idle_lat,
                        jitter_ms=jitter,
                        packet_loss_pct=pkt_loss,
                        method_used="https_multi_stream",
                        failure_reason="Cancelled by user.",
                        router_wan_down_mbps=router_wan_down_mbps,
                        router_wan_up_mbps=router_wan_up_mbps,
                        notes=["Speed test cancelled by user."],
                    )

                method_used = "https_multi_stream"
                dl_bytes = sum(valid_dl) if valid_dl else 0
                dl_mbps: Optional[float] = round((dl_bytes * 8.0) / (dl_elapsed * 1_000_000.0), 2) if valid_dl else None
                ul_bytes = 0
                ul_mbps: Optional[float] = None
                ul_elapsed: Optional[float] = None
                loaded_ul_lat: Optional[float] = None
                ul_notes: List[str] = []

                # Optional Speedtest CLI fallback if all HTTPS streams failed on a real run
                if not valid_dl and not self._custom_download:
                    cli_data = await asyncio.to_thread(self._try_speedtest_cli)
                    if isinstance(cli_data, dict):
                        dl_bw = cli_data.get("download", {}).get("bandwidth")
                        ul_bw = cli_data.get("upload", {}).get("bandwidth")
                        if dl_bw:
                            dl_mbps = round((float(dl_bw) * 8.0) / 1_000_000.0, 2)
                            ul_mbps = round((float(ul_bw or 0) * 8.0) / 1_000_000.0, 2) if ul_bw else None
                            idle_lat = cli_data.get("ping", {}).get("latency") or idle_lat
                            jitter = cli_data.get("ping", {}).get("jitter") or jitter
                            used_server_name = cli_data.get("server", {}).get("name", "Speedtest CLI")
                            method_used = "speedtest_cli_fallback"
                            valid_dl = [int(cli_data.get("download", {}).get("bytes") or 1)]
                            dl_bytes = valid_dl[0]

                if not valid_dl:
                    fail_msg = "; ".join(dl_errors[:3]) or "All speed endpoints failed (no bytes received)."
                    return SpeedTestReport(
                        run_id=run_id,
                        started_at=started,
                        completed_at=utc_now(),
                        status="failed",
                        server_name=used_server_name,
                        server_url=used_server_url,
                        wifi_tx_link_rate_mbps=wifi_tx,
                        wifi_rx_link_rate_mbps=wifi_rx,
                        qos_active_during_test=bool(qos_info["master_enabled"]),
                        qos_policies_count=int(qos_info["active_policies_count"]),
                        qos_summary=str(qos_info["summary"]),
                        interface_name=iface_name,
                        ssid=ssid,
                        bssid=bssid,
                        band=band,
                        idle_latency_ms=idle_lat,
                        jitter_ms=jitter,
                        packet_loss_pct=pkt_loss,
                        method_used=method_used,
                        failure_reason=fail_msg,
                        router_wan_down_mbps=router_wan_down_mbps,
                        router_wan_up_mbps=router_wan_up_mbps,
                        notes=[f"Download test failed: {fail_msg}"],
                    )

                if run_upload and method_used == "https_multi_stream" and not token.is_cancelled:
                    self._coordinator.update_progress(65.0, "uploading")
                    await asyncio.sleep(0.35)
                    payload_bytes = max(512_000, upload_payload_mb * 1_000_000)
                    ul_parsed = urllib.parse.urlparse(self._upload_url)
                    ul_host = ul_parsed.hostname or ep_host
                    ul_port = ul_parsed.port or (443 if ul_parsed.scheme == "https" else 80)
                    ul_t0 = time.monotonic()
                    try:
                        with ThreadPoolExecutor(max_workers=2) as pool:
                            ul_fut = loop.run_in_executor(
                                pool,
                                self._upload_worker,
                                self._upload_url,
                                payload_bytes,
                                max_upload_sec,
                                token,
                            )
                            probe_ul = (
                                loop.run_in_executor(pool, _tcp_rtt_probe, ul_host, ul_port, 3, 1.2)
                                if (not self._custom_upload and ul_host)
                                else None
                            )
                            ul_bytes = await ul_fut
                            if probe_ul is not None:
                                try:
                                    loaded_ul_lat, _, _ = await probe_ul
                                except Exception:
                                    loaded_ul_lat = None
                        ul_elapsed = round(max(0.05, time.monotonic() - ul_t0), 2)
                        if ul_bytes > 0:
                            ul_mbps = round((ul_bytes * 8.0) / (ul_elapsed * 1_000_000.0), 2)
                    except Exception as exc:
                        ul_notes.append(f"Upload measurement skipped/failed: {exc}")
                elif not run_upload:
                    ul_notes.append(
                        "Upload measurement skipped per configuration to conserve metered/quota bandwidth."
                    )

                notes = ul_notes + [
                    "Wi-Fi TX/RX link rate reflects PHY modulation ceiling, NOT Internet throughput.",
                ]
                if dl_errors:
                    notes.append(f"Fallback note: {dl_errors[0]}")

                return SpeedTestReport(
                    run_id=run_id,
                    started_at=started,
                    completed_at=utc_now(),
                    status="completed",
                    server_name=used_server_name,
                    server_url=used_server_url,
                    wifi_tx_link_rate_mbps=wifi_tx,
                    wifi_rx_link_rate_mbps=wifi_rx,
                    local_lan_throughput_mbps=None,
                    download_mbps=dl_mbps,
                    download_duration_sec=round(dl_elapsed, 2),
                    download_bytes=dl_bytes,
                    upload_tested=run_upload or (ul_mbps is not None),
                    upload_mbps=ul_mbps,
                    upload_duration_sec=ul_elapsed,
                    upload_bytes=ul_bytes,
                    qos_active_during_test=bool(qos_info["master_enabled"]),
                    qos_policies_count=int(qos_info["active_policies_count"]),
                    qos_summary=str(qos_info["summary"]),
                    interface_name=iface_name,
                    ssid=ssid,
                    bssid=bssid,
                    band=band,
                    idle_latency_ms=idle_lat,
                    loaded_download_latency_ms=loaded_dl_lat,
                    loaded_upload_latency_ms=loaded_ul_lat,
                    jitter_ms=jitter,
                    packet_loss_pct=pkt_loss,
                    method_used=method_used,
                    failure_reason=None,
                    router_wan_down_mbps=router_wan_down_mbps,
                    router_wan_up_mbps=router_wan_up_mbps,
                    notes=notes,
                )

        except MeetingSafetyFreezeError as exc:
            return SpeedTestReport(
                run_id=run_id,
                started_at=started,
                completed_at=utc_now(),
                status="blocked_meeting",
                server_name=self._server_name,
                server_url=self._download_url,
                wifi_tx_link_rate_mbps=wifi_tx,
                wifi_rx_link_rate_mbps=wifi_rx,
                qos_active_during_test=bool(qos_info["master_enabled"]),
                qos_policies_count=int(qos_info["active_policies_count"]),
                qos_summary=str(qos_info["summary"]),
                failure_reason=str(exc),
                notes=[str(exc)],
            )
        except DiagnosticBusyError as exc:
            return SpeedTestReport(
                run_id=run_id,
                started_at=started,
                completed_at=utc_now(),
                status="blocked_busy",
                server_name=self._server_name,
                server_url=self._download_url,
                wifi_tx_link_rate_mbps=wifi_tx,
                wifi_rx_link_rate_mbps=wifi_rx,
                failure_reason=str(exc),
                notes=[str(exc)],
            )


InternetSpeedTestService = SpeedTestService
