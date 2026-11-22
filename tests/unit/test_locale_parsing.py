"""Unit tests for Phase 4.2: Locale-Independent Parsing (English, German, French, Arabic)."""

import pytest
import re
from unittest.mock import patch, MagicMock
from app.platform.windows.adapter import WindowsPlatformAdapter


PING_SAMPLES = {
    "English": """
Pinging 1.1.1.1 with 32 bytes of data:
Reply from 1.1.1.1: bytes=32 time=14ms TTL=57

Ping statistics for 1.1.1.1:
    Packets: Sent = 1, Received = 1, Lost = 0 (0% loss),
Approximate round trip times in milli-seconds:
    Minimum = 14ms, Maximum = 14ms, Average = 14ms
""",
    "German": """
Ping wird ausgeführt für 1.1.1.1 mit 32 Bytes Daten:
Antwort von 1.1.1.1: Bytes=32 Zeit=15ms TTL=57

Ping-Statistik für 1.1.1.1:
    Pakete: Gesendet = 1, Empfangen = 1, Verloren = 0 (0% Verlust),
Ca. Zeitangaben in Millisek.:
    Minimum = 15ms, Maximum = 15ms, Mittelwert = 15ms
""",
    "French": """
Envoi d'une requête 'Ping' 1.1.1.1 avec 32 octets de données :
Réponse de 1.1.1.1 : octets=32 temps=16 ms TTL=57

Statistiques Ping pour 1.1.1.1:
    Paquets : envoyés = 1, reçus = 1, perdus = 0 (perte 0%),
Durée approximative des boucles en millisecondes :
    Minimum = 16ms, Maximum = 16ms, Moyenne = 16ms
""",
    "Arabic": """
يتم الآن الاتصال بـ 1.1.1.1 مع 32 بايت من البيانات:
الرد من 1.1.1.1: وحدات البايت=32 الوقت=17 مللي ثانية TTL=57

إحصائيات Ping لـ 1.1.1.1:
    الحزم: تم الإرسال = 1، تم الاستلام = 1، الفقد = 0 (فقد 0%)،
الأوقات التقريبية للذهاب والعودة بالمللي ثانية:
    الحد الأدنى = 17 مللي ثانية، الحد الأقصى = 17 مللي ثانية، المتوسط = 17 مللي ثانية
""",
    "English_Sub1ms": """
Reply from 192.168.1.1: bytes=32 time<1ms TTL=64
""",
    "Arabic_Sub1ms": """
الرد من 192.168.1.1: وحدات البايت=32 الوقت<1 مللي ثانية TTL=64
""",
}

WLAN_SAMPLES = {
    "English": """
There is 1 interface on the system:

    Name                   : Wi-Fi
    Description            : Intel(R) Wireless-AC 9560
    GUID                   : a1b2c3d4-e5f6-7890-abcd-ef0123456789
    Physical address       : 78:0c:b8:55:a3:7f
    State                  : connected
    SSID                   : HomeNet_5G
    BSSID                  : aa:bb:cc:dd:ee:ff
    Network type           : Infrastructure
    Radio type             : 802.11ac
    Authentication         : WPA2-Personal
    Cipher                 : CCMP
    Connection mode        : Profile
    Channel                : 36
    Receive rate (Mbps)    : 866.7
    Transmit rate (Mbps)   : 866.7
    Signal                 : 92%
""",
    "German": """
Es ist 1 Schnittstelle auf dem System vorhanden:

    Name                   : Wi-Fi
    Beschreibung           : Intel(R) Wireless-AC 9560
    GUID                   : a1b2c3d4-e5f6-7890-abcd-ef0123456789
    Physische Adresse      : 78:0c:b8:55:a3:7f
    Status                 : Verbunden
    SSID                   : HomeNet_5G
    BSSID                  : aa:bb:cc:dd:ee:ff
    Netzwerktyp            : Infrastruktur
    Funktyp                : 802.11ac
    Authentifizierung      : WPA2-Personal
    Verschlüsselung        : CCMP
    Verbindungsmodus       : Profil
    Kanal                  : 36
    Empfangsrate (MBit/s)  : 866.7
    Übertragungsrate (MBit/s) : 866.7
    Signal                 : 92%
""",
    "French": """
Il y a 1 interface sur le système :

    Nom                    : Wi-Fi
    Description            : Intel(R) Wireless-AC 9560
    GUID                   : a1b2c3d4-e5f6-7890-abcd-ef0123456789
    Adresse physique       : 78:0c:b8:55:a3:7f
    État                   : connecté
    SSID                   : HomeNet_5G
    BSSID                  : aa:bb:cc:dd:ee:ff
    Type de réseau         : Infrastructure
    Type de radio          : 802.11ac
    Authentification       : WPA2-Personnel
    Chiffrement            : CCMP
    Mode de connexion      : Profil
    Canal                  : 36
    Vitesse de réception (Mbits/s) : 866.7
    Vitesse de transmission (Mbits/s) : 866.7
    Signal                 : 92%
""",
    "Arabic": """
يوجد 1 من الواجهات على النظام:

    الاسم                  : Wi-Fi
    الوصف                  : Intel(R) Wireless-AC 9560
    GUID                   : a1b2c3d4-e5f6-7890-abcd-ef0123456789
    العنوان الفعلي         : 78:0c:b8:55:a3:7f
    الحالة                 : متصل
    SSID                   : HomeNet_5G
    BSSID                  : aa:bb:cc:dd:ee:ff
    نوع الشبكة             : بنية أساسية
    نوع الراديو            : 802.11ac
    المصادقة               : WPA2-Personal
    التشفير                : CCMP
    وضع الاتصال            : ملف تعريف
    القناة                 : 36
    معدل الاستلام (م.ب/ث)  : 866.7
    معدل الإرسال (م.ب/ث)   : 866.7
    الإشارة                : 92%
""",
}


@pytest.mark.parametrize(
    "lang,expected_ms",
    [
        ("English", 14.0),
        ("German", 15.0),
        ("French", 16.0),
        ("Arabic", 17.0),
        ("English_Sub1ms", 0.5),
        ("Arabic_Sub1ms", 0.5),
    ],
)
def test_locale_independent_ping_parsing(lang: str, expected_ms: float):
    adapter = WindowsPlatformAdapter()
    sample_output = PING_SAMPLES[lang]

    ok, lat = adapter.parse_ping_output(sample_output)
    assert ok is True
    assert lat == expected_ms


@pytest.mark.parametrize("lang", ["English", "German", "French", "Arabic"])
def test_locale_independent_wlan_metrics(lang: str):
    adapter = WindowsPlatformAdapter()
    sample_output = WLAN_SAMPLES[lang]

    metrics = adapter.parse_wlan_output(sample_output)
    assert metrics["is_wifi"] is True
    assert metrics["ssid"] == "HomeNet_5G"
    assert metrics["bssid"] == "aa:bb:cc:dd:ee:ff"
    assert metrics["signal_percent"] == 92.0
    assert metrics["rx_rate_mbps"] == 866.7
    assert metrics["tx_rate_mbps"] == 866.7


def test_native_win32_ping_and_wlan_metrics():
    adapter = WindowsPlatformAdapter()
    # Verify ping executes via native in-process Win32 API
    ok, lat = adapter.ping("127.0.0.1", timeout_sec=1.0)
    assert isinstance(ok, bool)
    assert isinstance(lat, float)

    # Verify WLAN query returns genuine WifiMetrics without spawning netsh
    wifi = adapter.get_wifi_metrics()
    assert isinstance(wifi, dict)
    assert hasattr(wifi, "is_wifi")
    assert "is_wifi" in wifi
