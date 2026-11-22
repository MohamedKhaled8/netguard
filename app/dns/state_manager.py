"""Re-export of DnsStateManager and DnsStateData for module contract compliance."""

from app.dns.state import DnsStateManager, DnsStateData

__all__ = ["DnsStateManager", "DnsStateData"]
