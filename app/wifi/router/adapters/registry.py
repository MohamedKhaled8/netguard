"""Registry selecting and instantiating vendor router adapters safely."""

from __future__ import annotations

from typing import Callable, Dict, List

from app.wifi.router.adapters.asus import AsusRouterAdapter
from app.wifi.router.adapters.base import IRouterAdapter
from app.wifi.router.adapters.generic_probe import GenericProbeAdapter
from app.wifi.router.adapters.huawei import HuaweiRouterAdapter
from app.wifi.router.adapters.isp_generic_models import IspGenericRouterAdapter, VENDOR_PROFILES
from app.wifi.router.adapters.mikrotik import MikroTikRouterAdapter
from app.wifi.router.adapters.tplink import TpLinkRouterAdapter
from app.wifi.router.adapters.zte import ZteRouterAdapter


class RouterAdapterRegistry:
    """Maintains all available modular router adapters keyed by adapter_id."""

    def __init__(self, *, allow_loopback: bool = False) -> None:
        self._allow_loopback = allow_loopback
        self._factories: Dict[str, Callable[[], IRouterAdapter]] = {
            "zte": lambda: ZteRouterAdapter(allow_loopback=self._allow_loopback),
            "huawei": lambda: HuaweiRouterAdapter(allow_loopback=self._allow_loopback),
            "tplink": lambda: TpLinkRouterAdapter(allow_loopback=self._allow_loopback),
            "asus": lambda: AsusRouterAdapter(allow_loopback=self._allow_loopback),
            "mikrotik": lambda: MikroTikRouterAdapter(allow_loopback=self._allow_loopback),
            "isp_generic": lambda: IspGenericRouterAdapter(allow_loopback=self._allow_loopback),
            "generic_probe": lambda: GenericProbeAdapter(allow_loopback=self._allow_loopback),
        }
        for vk in VENDOR_PROFILES:
            self._factories[vk] = lambda key=vk: IspGenericRouterAdapter(vendor_key=key, allow_loopback=self._allow_loopback)
            self._factories[f"isp_generic:{vk}"] = lambda key=vk: IspGenericRouterAdapter(vendor_key=key, allow_loopback=self._allow_loopback)
        self._instances: Dict[str, IRouterAdapter] = {}

    def register(self, adapter_id: str, factory: Callable[[], IRouterAdapter]) -> None:
        self._factories[adapter_id] = factory
        self._instances.pop(adapter_id, None)

    def get_adapter(self, adapter_id: str) -> IRouterAdapter:
        key = adapter_id if adapter_id in self._factories else "generic_probe"
        if key not in self._instances:
            self._instances[key] = self._factories[key]()
        return self._instances[key]

    def list_adapter_ids(self) -> List[str]:
        return list(self._factories.keys())

    def list_adapters(self) -> List[IRouterAdapter]:
        return list(self._instances.values())
