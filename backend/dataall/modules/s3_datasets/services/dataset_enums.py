from enum import Enum


class MetadataGenerationTargets(Enum):
    """Describes the s3_datasets metadata generation types"""

    Table = 'Table'
    Folder = 'Folder'
    S3_Dataset = 'S3_Dataset'


class MetadataGenerationTypes(Enum):
    """Describes the s3_datasets metadata generation types"""

    Description = 'description'
    Label = 'label'
    Tag = 'tags'
    Topic = 'topics'
