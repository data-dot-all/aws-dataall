from dataall.base.api.constants import GraphQLEnumMapper


class MetadataGenerationTargets(GraphQLEnumMapper):
    """Describes the s3_datasets metadata generation targets"""

    Table = 'Table'
    Folder = 'Folder'
    S3_Dataset = 'S3_Dataset'
