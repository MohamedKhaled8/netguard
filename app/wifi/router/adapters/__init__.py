"""Modular router adapters package."""

from app.wifi.router.adapters.base import IRouterAdapter, RouterHttpClient, RouterHttpResponse
from app.wifi.router.adapters.generic_probe import GenericProbeAdapter
from app.wifi.router.adapters.huawei import HuaweiRouterAdapter
from app.wifi.router.adapters.registry import RouterAdapterRegistry
from app.wifi.router.adapters.tplink import TpLinkRouterAdapter
from app.wifi.router.adapters.zte import ZteRouterAdapter

__all__ = [
    "IRouterAdapter",
    "RouterHttpClient",
    "RouterHttpResponse",
    "GenericProbeAdapter",
    "HuaweiRouterAdapter",
    "TpLinkRouterAdapter",
    "ZteRouterAdapter",
    "RouterAdapterRegistry",
]
