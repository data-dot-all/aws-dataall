import logging
from typing import Any, Dict
from dataclasses import dataclass
from abc import ABC, abstractmethod
from dataall.modules.shares_base.services.shares_enums import ShareableType

log = logging.getLogger(__name__)


class SharesProcessorInterface(ABC):
    @abstractmethod
    def process_approved_shares(self) -> bool:
        """Executes a series of actions to share items using the share manager. Returns True if the sharing was successful"""
        ...

    @abstractmethod
    def process_revoked_shares(self) -> bool:
        """Executes a series of actions to revoke share items using the share manager. Returns True if the revoking was successful"""
        ...

    @abstractmethod
    def verify_shares_health_status(self) -> bool:
        """Executes a series of actions to verify share items using the share manager. Returns True if the verifying was successful"""
        ...

    @abstractmethod
    def cleanup_shares(self) -> bool:
        """Executes a series of actions to fully cleanup a share using the share manager. Returns True"""
        ...


@dataclass
class ShareProcessorDefinition:
    type: ShareableType
    Processor: Any
    shareable_type: Any
    shareable_uri: Any


class ShareProcessorManager:
    SHARING_PROCESSORS: Dict[ShareableType, ShareProcessorDefinition] = {}

    @classmethod
    def register_processor(cls, processor: ShareProcessorDefinition) -> None:
        cls.SHARING_PROCESSORS[processor.type] = processor

    @classmethod
    def get_processor_by_item_type(cls, item_type: str) -> ShareProcessorDefinition:
        for type, processor in cls.SHARING_PROCESSORS.items():
            if type.value == item_type:
                return processor
