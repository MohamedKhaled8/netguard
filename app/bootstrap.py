"""Application Bootstrap and Lifecycle Management."""

from __future__ import annotations
import asyncio
from pathlib import Path
from typing import Optional
from app.core.config.loader import load_config
from app.core.config.models import AppConfig
from app.core.events.bus import EventBus
from app.core.utilities.logger import setup_logger
from app.platform.factory import get_platform_adapter
from app.platform.interfaces import IPlatformAdapter
from app.storage.database import DatabaseManager
from app.storage.repositories.measurement_repo import MeasurementRepository
from app.storage.repositories.incident_repo import IncidentRepository
from app.storage.repositories.audit_repo import AuditRepository
from app.core.settings import UserSettings


class ApplicationContext:
    """Holds shared runtime services across the application."""

    def __init__(
        self,
        config: AppConfig,
        event_bus: EventBus,
        platform_adapter: IPlatformAdapter,
        db_manager: DatabaseManager,
        measurement_repo: MeasurementRepository,
        incident_repo: IncidentRepository,
        audit_repo: AuditRepository,
        settings: Optional[UserSettings] = None,
    ) -> None:
        self.config = config
        self.event_bus = event_bus
        self.platform = platform_adapter
        self.db = db_manager
        self.measurements = measurement_repo
        self.incidents = incident_repo
        self.audit = audit_repo
        self.settings = settings
        self.logger = setup_logger(
            name="netguard",
            level=config.logging.level,
            log_dir=config.logging.log_dir,
            log_to_console=config.logging.log_to_console,
            log_to_file=config.logging.log_to_file,
        )


def bootstrap_application(config_path: Optional[Path | str] = None, in_memory_db: bool = False) -> ApplicationContext:
    """Initializes all foundational dependencies and validates environment."""
    config = load_config(config_path)

    # Initialize Logger
    logger = setup_logger(
        name="netguard",
        level=config.logging.level,
        log_dir=config.logging.log_dir,
        log_to_console=config.logging.log_to_console,
        log_to_file=config.logging.log_to_file,
    )
    logger.info("Initializing NetGuard AI runtime environment...")

    # Platform Adapter
    platform_adapter = get_platform_adapter()
    primary_iface = platform_adapter.get_primary_interface()
    gateway_ip = platform_adapter.get_default_gateway()
    logger.info("Host platform adapter initialized. Active Interface: %s, Default Gateway: %s", primary_iface, gateway_ip)

    # Event Bus
    event_bus = EventBus()

    # Database & Repositories
    db_target = ":memory:" if in_memory_db else config.database.db_path
    db_manager = DatabaseManager(db_path=db_target, enable_wal=config.database.enable_wal)
    measurement_repo = MeasurementRepository(db_manager)
    incident_repo = IncidentRepository(db_manager)
    audit_repo = AuditRepository(db_manager)

    settings = UserSettings(config=config, event_bus=event_bus)

    context = ApplicationContext(
        config=config,
        event_bus=event_bus,
        platform_adapter=platform_adapter,
        db_manager=db_manager,
        measurement_repo=measurement_repo,
        incident_repo=incident_repo,
        audit_repo=audit_repo,
        settings=settings,
    )
    logger.info("NetGuard AI Bootstrap completed successfully.")
    return context

