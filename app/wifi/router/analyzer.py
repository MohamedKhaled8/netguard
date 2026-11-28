"""Cross-layer router & network configuration analyzer producing evidence-backed change proposals."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from app.wifi.models import (
    BufferbloatDiagnosticsReport,
    ConnectedDeviceRecord,
    DnsDiagnosticsReport,
    FullChannelAnalysisReport,
    NetworkDiagnosticsReport,
    RouterCapabilities,
    RouterChangeProposal,
    RouterConfigurationSnapshot,
    WifiInterfaceTelemetry,
)
from app.wifi.router.models_config import RouterConfigurationModel


class RouterConfigAnalyzer:
    """Evaluates settings in hardware/firmware/ISP/client/RF context rather than static template matching."""

    def analyze(
        self,
        *,
        capabilities: RouterCapabilities,
        router_config: Optional[RouterConfigurationSnapshot] = None,
        config_model: Optional[RouterConfigurationModel] = None,
        telemetry: Optional[WifiInterfaceTelemetry] = None,
        channel_report: Optional[FullChannelAnalysisReport] = None,
        dns_report: Optional[DnsDiagnosticsReport] = None,
        bufferbloat_report: Optional[BufferbloatDiagnosticsReport] = None,
        network_report: Optional[NetworkDiagnosticsReport] = None,
        devices: Optional[List[ConnectedDeviceRecord]] = None,
    ) -> List[RouterChangeProposal]:
        """Generate evidence-backed router and network proposals across RF, DNS, QoS, WAN, LAN/DHCP, and security."""
        proposals: List[RouterChangeProposal] = []
        snap = router_config or (config_model.snapshot if config_model else None)
        domains: Dict[str, Dict[str, Any]] = config_model.domains if config_model else {}

        # 1. Band/Channel Optimization Proposals
        if channel_report is not None:
            for band, band_res in channel_report.bands.items():
                cur_ch = band_res.current_channel
                cur_sc = band_res.current_channel_score
                best = band_res.recommended_channels[0] if band_res.recommended_channels else None
                if best and cur_ch and cur_sc and best.channel != cur_ch:
                    improvement = round(cur_sc.total_score - best.total_score, 2)
                    if improvement >= 4.0:
                        conf_ar = {"high": "ثقة عالية", "medium": "ثقة متوسطة", "low": "ثقة محدودة"}.get(best.confidence_label, best.confidence_label)
                        lvl_cur_ar = {"low": "منخفض", "moderate": "متوسط", "high": "مرتفع", "severe": "حرج"}.get(cur_sc.interference_level, cur_sc.interference_level)
                        lvl_best_ar = {"low": "منخفض", "moderate": "متوسط", "high": "مرتفع", "severe": "حرج"}.get(best.interference_level, best.interference_level)
                        proposals.append(
                            RouterChangeProposal(
                                proposal_id=f"ch_{band.replace(' ', '_')}_{uuid.uuid4().hex[:6]}",
                                category="wifi_channel",
                                title=f"تغيير قناة {band} من القناة {cur_ch} إلى القناة {best.channel}",
                                target_field="channel",
                                band=band,
                                current_value=str(cur_ch),
                                proposed_value=str(best.channel),
                                reason=(
                                    f"درجة ازدحام القناة {cur_ch} تبلغ {cur_sc.total_score:.1f} ({lvl_cur_ar})، "
                                    f"بينما القناة {best.channel} تسجل {best.total_score:.1f} ({lvl_best_ar})."
                                ),
                                expected_impact=(
                                    f"يخفض أثر التداخل المتبادل والمجاور بمقدار {improvement:.1f} نقطة ({conf_ar})."
                                ),
                                risk_level="medium" if best.is_dfs else "low",
                                requires_reconnect_warning=True,
                                supported_by_adapter=capabilities.supports_channel_write,
                                requires_manual_apply=not capabilities.supports_channel_write,
                                evidence=[cur_sc.formula_notes, best.reason],
                            )
                        )
                # Non-orthogonal 2.4 GHz channel check (not 1/6/11 when neighbors overlap)
                if band == "2.4 GHz" and cur_ch and cur_ch not in (1, 6, 11) and not proposals:
                    best_ortho = next((r for r in band_res.recommended_channels if r.channel in (1, 6, 11)), None)
                    if best_ortho:
                        proposals.append(
                            RouterChangeProposal(
                                proposal_id=f"ch24_ortho_{uuid.uuid4().hex[:6]}",
                                category="wifi_channel",
                                title=f"نقل قناة 2.4 GHz من {cur_ch} المتداخلة إلى القناة القياسية {best_ortho.channel}",
                                target_field="channel",
                                band="2.4 GHz",
                                current_value=str(cur_ch),
                                proposed_value=str(best_ortho.channel),
                                reason=f"القناة {cur_ch} تتداخل طيفياً مع القنوات القياسية غير المتداخلة (1 و 6 و 11).",
                                expected_impact="يتجنب التداخل الجزئي وتصادم حزم CSMA/CA على 2.4 GHz.",
                                risk_level="low",
                                requires_reconnect_warning=True,
                                supported_by_adapter=capabilities.supports_channel_write,
                                requires_manual_apply=not capabilities.supports_channel_write,
                                evidence=[f"القناة الحالية على 2.4 GHz={cur_ch}؛ القناة القياسية المقترحة={best_ortho.channel}"],
                            )
                        )

        # 2. Channel Width Guardrails
        r24 = snap.radios.get("2.4 GHz") if snap else None
        r5 = snap.radios.get("5 GHz") if snap else None
        obs_w24 = telemetry.channel_width_mhz if (telemetry and telemetry.band == "2.4 GHz") else (
            int(str(r24.channel_width).replace("MHz", "").strip()) if r24 and str(r24.channel_width or "").replace("MHz", "").strip().isdigit() else None
        )
        if obs_w24 == 40:
            proposals.append(
                RouterChangeProposal(
                    proposal_id=f"w24_{uuid.uuid4().hex[:6]}",
                    category="channel_width",
                    title="تضييق عرض قناة 2.4 GHz من 40 MHz إلى 20 MHz",
                    target_field="channel_width",
                    band="2.4 GHz",
                    current_value="40 MHz",
                    proposed_value="20 MHz",
                    reason="عرض 40 MHz على نطاق 2.4 GHz يستهلك ثلثي النطاق الكامل ويزيد تداخل شبكات الجيران (OBSS).",
                    expected_impact="يرفع استقرار وقت البث ويقلل إعادة إرسال الحزم أثناء المكالمات والتصفح.",
                    risk_level="low",
                    requires_reconnect_warning=True,
                    supported_by_adapter=capabilities.supports_width_write,
                    requires_manual_apply=not capabilities.supports_width_write,
                    evidence=[f"عرض قناة 2.4 GHz المرصود: {obs_w24} MHz"],
                )
            )
        elif (
            telemetry
            and telemetry.band == "5 GHz"
            and telemetry.channel_width_mhz in (80, 160)
            and telemetry.rssi_dbm is not None
            and telemetry.rssi_dbm <= -72
        ):
            target_w = "40 MHz" if telemetry.channel_width_mhz == 80 else "80 MHz"
            proposals.append(
                RouterChangeProposal(
                    proposal_id=f"w5_{uuid.uuid4().hex[:6]}",
                    category="channel_width",
                    title=f"تضييق عرض قناة 5 GHz من {telemetry.channel_width_mhz} MHz إلى {target_w}",
                    target_field="channel_width",
                    band="5 GHz",
                    current_value=f"{telemetry.channel_width_mhz} MHz",
                    proposed_value=target_w,
                    reason=(
                        f"ضعف إشارة 5 GHz ({telemetry.rssi_dbm} dBm) مع عرض {telemetry.channel_width_mhz} MHz "
                        "يخفض هامش الإشارة للضوضاء لكل موجة فرعية ويزيد إعادة الإرسال."
                    ),
                    expected_impact="يحسن هامش الإشارة بنحو 3 dB لكل تنصيف للعرض ويخفض التذبذب.",
                    risk_level="low",
                    requires_reconnect_warning=True,
                    supported_by_adapter=capabilities.supports_width_write,
                    requires_manual_apply=not capabilities.supports_width_write,
                    evidence=[f"RSSI={telemetry.rssi_dbm} dBm | Width={telemetry.channel_width_mhz} MHz"],
                )
            )

        # 3. 5 GHz Disabled or Wrong Band Check
        if r5 and r5.enabled is False:
            proposals.append(
                RouterChangeProposal(
                    proposal_id=f"en5_{uuid.uuid4().hex[:6]}",
                    category="band_steering",
                    title="تفعيل شبكة 5 GHz على الراوتر لسرعة أعلى وتذبذب أقل",
                    target_field="radio_5ghz_enabled",
                    band="5 GHz",
                    current_value="معطّل",
                    proposed_value="مفعّل",
                    reason="راديو 5 GHz في الراوتر معطّل حالياً، مما يجبر كل الأجهزة على استخدام 2.4 GHz المزدحم.",
                    expected_impact="يتيح قنوات غير متداخلة بأداء مستقر وتنافس أقل على الهواء.",
                    risk_level="low",
                    requires_reconnect_warning=True,
                    supported_by_adapter=capabilities.supports_wifi_write,
                    requires_manual_apply=not capabilities.supports_wifi_write,
                    evidence=["أفاد الراوتر أن بث 5 GHz معطّل"],
                )
            )

        # 4. Bufferbloat / Router SQM or QoS
        if bufferbloat_report and bufferbloat_report.overall_grade in ("C", "D", "F"):
            ul_delta = bufferbloat_report.upload_phase.delta_over_idle_ms if bufferbloat_report.upload_phase else None
            dl_delta = bufferbloat_report.download_phase.delta_over_idle_ms if bufferbloat_report.download_phase else None
            if not (snap and snap.sqm_enabled):
                proposals.append(
                    RouterChangeProposal(
                        proposal_id=f"sqm_{uuid.uuid4().hex[:6]}",
                        category="qos_sqm",
                        title="تفعيل إدارة الطوابير الذكية SQM أو QoS في الراوتر",
                        target_field="qos_enabled",
                        band=None,
                        current_value=(
                            "مفعّل" if (snap and snap.qos_enabled is True) else ("معطّل" if (snap and snap.qos_enabled is False) else "غير مؤكد / معطّل")
                        ),
                        proposed_value="مفعّل",
                        reason=(
                            f"تقدير Bufferbloat الحالي هو {bufferbloat_report.overall_grade} "
                            f"(زيادة التنزيل +{dl_delta} ms والرفع +{ul_delta} ms)."
                        ),
                        expected_impact=(
                            "يضبط تأخير طوابير WAN لكل أجهزة المنزل ويكمل حماية NetGuard QoS المحلية لهذا الجهاز."
                        ),
                        risk_level="medium",
                        requires_reconnect_warning=False,
                        supported_by_adapter=capabilities.supports_sqm_or_qos_write,
                        requires_manual_apply=not capabilities.supports_sqm_or_qos_write,
                        evidence=[bufferbloat_report.summary],
                    )
                )

        # 5. WMM Check (disabling WMM cripples 802.11n/ac/ax to <=54 Mbps!)
        wmm_dom = domains.get("wmm", {})
        for k, v in wmm_dom.items():
            if "wmm" in k.lower() and str(v).strip().lower() in ("0", "false", "disabled", "off"):
                proposals.append(
                    RouterChangeProposal(
                        proposal_id=f"wmm_{uuid.uuid4().hex[:6]}",
                        category="wmm",
                        title="إعادة تفعيل WMM (جودة الوسائط اللاسلكية 802.11e)",
                        target_field="wmm_enabled",
                        band=None,
                        current_value=str(v),
                        proposed_value="مفعّل",
                        reason="تعطيل WMM يخالف مواصفات 802.11n/ac/ax ويقيد سرعة Wi-Fi قرب 54 Mbps ويلغي أولوية الصوت والفيديو.",
                        expected_impact="يستعيد سرعات HT/VHT/HE الكاملة وأولوية المكالمات لاسلكياً.",
                        risk_level="low",
                        requires_reconnect_warning=True,
                        supported_by_adapter=False,
                        requires_manual_apply=True,
                        evidence=[f"إعداد الراوتر {k}={v}"],
                    )
                )
                break

        # 6. Security check
        sec_str = telemetry.security_mode if telemetry and telemetry.security_mode else (r24.security_mode if r24 else None)
        if sec_str:
            sec_low = sec_str.lower()
            if "open" in sec_low or "wep" in sec_low or ("wpa-" in sec_low and "wpa2" not in sec_low and "wpa3" not in sec_low) or "tkip" in sec_low:
                proposals.append(
                    RouterChangeProposal(
                        proposal_id=f"sec_{uuid.uuid4().hex[:6]}",
                        category="security_mode",
                        title="ترقية أمان الواي فاي إلى WPA2-PSK (AES) أو WPA2/WPA3",
                        target_field="security_mode",
                        band=telemetry.band if telemetry else "2.4 GHz",
                        current_value=sec_str,
                        proposed_value="WPA2-PSK (AES)",
                        reason=f"التشفير الحالي ({sec_str}) يعتمد على تشفير قديم ضعيف أو TKIP الذي يقيد سرعة الربط.",
                        expected_impact="يمنع اعتراض الاتصال ويرفع قيود السرعة المفروضة بسبب TKIP.",
                        risk_level="high",
                        requires_reconnect_warning=True,
                        supported_by_adapter=False,
                        requires_manual_apply=True,
                        evidence=[f"وضع الأمان المرصود: {sec_str}"],
                    )
                )

        # 7. DNS check (even if router_config DNS list isn't populated, use OS DNS report if DNS latency problem measured)
        if dns_report and dns_report.recommended_dns:
            cur_dns = ", ".join(snap.dns_servers) if (snap and snap.dns_servers) else (dns_report.router_dns_server or ", ".join(dns_report.configured_dns_servers))
            rec_dns = dns_report.recommended_dns
            slow_or_diff = rec_dns not in cur_dns if cur_dns else False
            if cur_dns and slow_or_diff and ((snap and snap.dns_servers) or any(t.role in ("configured", "router") and (t.status in ("unreachable", "failed") or (t.median_ms or 0) >= 80.0) for t in dns_report.targets)):
                proposals.append(
                    RouterChangeProposal(
                        proposal_id=f"dns_{uuid.uuid4().hex[:6]}",
                        category="dns",
                        title=f"تعيين خادم DNS الأسرع ({rec_dns}) في الراوتر",
                        target_field="dns_servers",
                        band=None,
                        current_value=cur_dns,
                        proposed_value=rec_dns,
                        reason=dns_report.summary,
                        expected_impact="يخفض زمن ترجمة أسماء النطاقات غير المخزنة ويحسن استقرار التصفح.",
                        risk_level="low",
                        requires_reconnect_warning=False,
                        supported_by_adapter=capabilities.supports_dns_config_write,
                        requires_manual_apply=not capabilities.supports_dns_config_write,
                        evidence=[f"الخادم الأسرع المقاس: {rec_dns}", f"DNS الحالي: {cur_dns}"],
                    )
                )

        # 8. DSL / Fiber Access Line Signal Health (when router line stats are extracted)
        if snap and snap.wan_line_stats:
            snr_dn = snap.wan_line_stats.get("snr_margin_down_db")
            if isinstance(snr_dn, (int, float)) and snr_dn < 6.0:
                proposals.append(
                    RouterChangeProposal(
                        proposal_id=f"dsl_{uuid.uuid4().hex[:6]}",
                        category="wan",
                        title="فحص هامش التشويش على خط DSL (SNR Margin أقل من 6 dB)",
                        target_field="wan_line_snr",
                        band=None,
                        current_value=f"{snr_dn} dB",
                        proposed_value=">= 8.0 dB (فحص السبليتر والأسلاك وملف الخط)",
                        reason="انخفاض هامش SNR للتنزيل عن 6 dB يسبب أخطاء CRC وانقطاعات متكررة وتخفيض سرعة الخط من المزود.",
                        expected_impact="يثبت مزامنة الخط ويمنع الانقطاعات المتكررة.",
                        risk_level="high",
                        requires_reconnect_warning=False,
                        supported_by_adapter=False,
                        requires_manual_apply=True,
                        evidence=[f"SNR خط DSL للتنزيل = {snr_dn} dB"],
                    )
                )

        # 9. DHCP Lease Time sanity check
        dhcp_dom = domains.get("dhcp_server", {})
        for k, v in dhcp_dom.items():
            if "leasetime" in k.lower() and str(v).isdigit():
                sec = int(v)
                if 0 < sec < 300:
                    proposals.append(
                        RouterChangeProposal(
                            proposal_id=f"dhcp_{uuid.uuid4().hex[:6]}",
                            category="dhcp",
                            title="إطالة مدة إيجار عناوين DHCP القصيرة جداً",
                            target_field="dhcp_lease_time",
                            band=None,
                            current_value=f"{sec}s",
                            proposed_value="86400s (24 ساعة)",
                            reason="مدة إيجار DHCP القصيرة (< 5 دقائق) تولّد طلبات تجديد متكررة وتقطيعاً لحظياً على الأجهزة المتنقلة.",
                            expected_impact="يزيل التقطيع الدوري الناتج عن تجديد عناوين الشبكة.",
                            risk_level="low",
                            requires_reconnect_warning=False,
                            supported_by_adapter=False,
                            requires_manual_apply=True,
                            evidence=[f"{k}={sec} seconds"],
                        )
                    )
                    break

        # 10. UPnP exposure check
        upnp_dom = domains.get("upnp", {})
        upnp_flag = snap.upnp_enabled if snap else None
        if upnp_flag is None:
            for k, v in upnp_dom.items():
                if "upnp" in k.lower() and str(v).strip().lower() in ("1", "true", "enabled", "on"):
                    upnp_flag = True
                    break
        if upnp_flag is True:
            proposals.append(
                RouterChangeProposal(
                    proposal_id=f"upnp_{uuid.uuid4().hex[:6]}",
                    category="upnp",
                    title="مراجعة أو تعطيل فتح المنافذ التلقائي UPnP عند عدم الحاجة",
                    target_field="upnp_enabled",
                    band=None,
                    current_value="مفعّل",
                    proposed_value="معطّل (توجيه منافذ يدوي فقط)",
                    reason="تفعيل UPnP يتيح لأي جهاز أو برنامج على الشبكة المحلية فتح منافذ خارجية في الجدار الناري بصمت.",
                    expected_impact="يقلل انكشاف الشبكة على الإنترنت مع الإبقاء على التوجيهات اليدوية للألعاب والخدمات.",
                    risk_level="low",
                    requires_reconnect_warning=False,
                    supported_by_adapter=False,
                    requires_manual_apply=True,
                    evidence=["أظهر إعداد الراوتر أن UPnP مفعّل"],
                )
            )

        # 11. Firewall Level Check
        fw_level = (snap.firewall_level or "").strip().lower() if snap and snap.firewall_level else ""
        if not fw_level:
            fw_dom = domains.get("firewall", {})
            for k, v in fw_dom.items():
                if "firewall" in k.lower() or "spi" in k.lower():
                    fw_level = str(v).strip().lower()
                    break
        if fw_level in ("0", "false", "off", "disabled", "none"):
            proposals.append(
                RouterChangeProposal(
                    proposal_id=f"fw_{uuid.uuid4().hex[:6]}",
                    category="firewall",
                    title="تفعيل جدار الحماية SPI في الراوتر",
                    target_field="firewall_level",
                    band=None,
                    current_value=fw_level,
                    proposed_value="متوسط / مفعّل (SPI)",
                    reason="تعطيل جدار الحماية يعرض أجهزة الشبكة المحلية مباشرة لفحوصات ومحاولات الاتصال من الإنترنت.",
                    expected_impact="يستعيد فحص الحزم الواردة بدون أثر يُذكر على زمن الاستجابة.",
                    risk_level="medium",
                    requires_reconnect_warning=False,
                    supported_by_adapter=False,
                    requires_manual_apply=True,
                    evidence=[f"إعداد جدار الحماية={fw_level}"],
                )
            )

        # 12. High Transmit Power vs Co-Channel Interference / OBSS balance
        tx_dom = domains.get("tx_power", {})
        for k, v in tx_dom.items():
            val_low = str(v).strip().lower()
            if ("tx" in k.lower() or "power" in k.lower()) and val_low in ("100", "100%", "high", "max"):
                if channel_report and telemetry and telemetry.band == "2.4 GHz":
                    b_res = channel_report.bands.get("2.4 GHz")
                    if b_res and b_res.current_channel_score and b_res.current_channel_score.total_score >= 40.0 and (telemetry.rssi_dbm or -90) >= -58:
                        proposals.append(
                            RouterChangeProposal(
                                proposal_id=f"txp_{uuid.uuid4().hex[:6]}",
                                category="tx_power",
                                title="دراسة خفض طاقة بث 2.4 GHz من 100% إلى 75% لتقليل التداخل",
                                target_field="tx_power",
                                band="2.4 GHz",
                                current_value=str(v),
                                proposed_value="75% / متوسط (عند إشارة >= -58 dBm)",
                                reason="طاقة البث القصوى 100% على 2.4 GHz تزيد تداخل الجيران وتبقي الأجهزة القريبة معلّقة على 2.4 GHz بدلاً من 5 GHz.",
                                expected_impact="يشجع انتقال الأجهزة القريبة إلى 5 GHz ويقلل إعادة إرسال الحزم.",
                                risk_level="low",
                                requires_reconnect_warning=True,
                                supported_by_adapter=capabilities.supports_tx_power_write,
                                requires_manual_apply=not capabilities.supports_tx_power_write,
                                evidence=[f"TX Power={v}", f"2.4G congestion={b_res.current_channel_score.total_score:.1f}", f"RSSI={telemetry.rssi_dbm} dBm"],
                            )
                        )
                        break

        # 13. DHCP disabled or client density check
        if snap and snap.dhcp_enabled is False and devices and len(devices) >= 3:
            proposals.append(
                RouterChangeProposal(
                    proposal_id=f"dhcp_off_{uuid.uuid4().hex[:6]}",
                    category="dhcp",
                    title="التحقق من توزيع العناوين اليدوي (خادم DHCP بالراوتر معطّل)",
                    target_field="dhcp_enabled",
                    band=None,
                    current_value="معطّل",
                    proposed_value="مفعّل (ما لم يوجد خادم DHCP بديل)",
                    reason=f"رُصد {len(devices)} أجهزة على الشبكة بينما خادم DHCP بالراوتر معطّل، مما قد يمنع الأجهزة الجديدة من أخذ عنوان IP.",
                    expected_impact="يمنع فشل حصول الأجهزة الجديدة على IP وتعارض العناوين إلا إذا كان هناك خادم DHCP مقصود.",
                    risk_level="medium",
                    requires_reconnect_warning=False,
                    supported_by_adapter=False,
                    requires_manual_apply=True,
                    evidence=[f"dhcp_enabled=False", f"Active LAN devices={len(devices)}"],
                )
            )

        return proposals


RouterConfigurationAnalyzer = RouterConfigAnalyzer
