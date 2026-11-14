"""Platform Adapter Factory for Operating System Auto-Detection."""

import sys
from app.platform.interfaces import IPlatformAdapter
from app.platform.windows.adapter import WindowsPlatformAdapter
from app.platform.linux.adapter import LinuxPlatformAdapter


def get_platform_adapter() -> IPlatformAdapter:
    """Returns the appropriate platform adapter for the current host OS."""
    if sys.platform.startswith("win"):
        return WindowsPlatformAdapter()
    elif sys.platform.startswith("linux"):
        return LinuxPlatformAdapter()
    else:
        # Default fallback to Windows or Linux adapter
        return WindowsPlatformAdapter()
