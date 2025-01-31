from typing import List, Type

from dataall.base.loader import ModuleInterface, ImportMode


class MetadataFormsApiModuleInterface(ModuleInterface):
    """Implements ModuleInterface for Metadata Forms GraphQl lambda"""

    @classmethod
    def is_supported(cls, modes):
        return ImportMode.API in modes

    def __init__(self):
        import dataall.modules.metadata_forms.api
        import dataall.modules.metadata_forms.db.enums

    @staticmethod
    def depends_on() -> List[Type['ModuleInterface']]:
        from dataall.modules.datasets_base import DatasetBaseApiModuleInterface

        return [DatasetBaseApiModuleInterface]
