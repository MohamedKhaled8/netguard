from app.platform.interfaces import IPlatformAdapter
from app.platform.factory import get_platform_adapter
from app.platform.admin import require_admin, prompt_restart_as_admin

__all__ = ["IPlatformAdapter", "get_platform_adapter", "require_admin", "prompt_restart_as_admin"]
