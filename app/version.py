"""Application Version and Metadata definition for NetGuard AI."""

__version__ = "1.2.0"
APP_NAME = "NetGuard AI"
APP_DESCRIPTION = "Autonomous Zero-Loss Network Diagnostics & Latency Self-Healing System"
# Self-Hosted Update Configuration:
# Default fallback update source. Can be a LAN UNC path (e.g. \\\\SERVER\\NetGuardUpdates\\version.json)
# or an HTTP endpoint (e.g. http://192.168.1.100:8765/version.json).
# Configurable and persisted in application settings without rebuilding the .exe.
DEFAULT_UPDATE_SOURCE = ""
UPDATE_CHECK_URL = DEFAULT_UPDATE_SOURCE
