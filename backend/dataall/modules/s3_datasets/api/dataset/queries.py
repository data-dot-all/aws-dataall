from dataall.base.api import gql
from dataall.modules.s3_datasets.api.dataset.resolvers import (
    get_dataset,
    get_dataset_assume_role_url,
    list_s3_object_keys,
    get_file_upload_presigned_url,
    list_datasets_owned_by_env_group,
)

getDataset = gql.QueryField(
    name='getDataset',
    args=[gql.Argument(name='datasetUri', type=gql.NonNullableType(gql.String))],
    type=gql.Ref('Dataset'),
    resolver=get_dataset,
    test_scope='Dataset',
)


getDatasetAssumeRoleUrl = gql.QueryField(
    name='getDatasetAssumeRoleUrl',
    args=[gql.Argument(name='datasetUri', type=gql.String)],
    type=gql.String,
    resolver=get_dataset_assume_role_url,
    test_scope='Dataset',
)


getDatasetPresignedUrl = gql.QueryField(
    name='getDatasetPresignedUrl',
    args=[
        gql.Argument(name='datasetUri', type=gql.NonNullableType(gql.String)),
        gql.Argument(name='input', type=gql.Ref('DatasetPresignedUrlInput')),
    ],
    type=gql.String,
    resolver=get_file_upload_presigned_url,
)

listS3DatasetsOwnedByEnvGroup = gql.QueryField(
    name='listS3DatasetsOwnedByEnvGroup',
    type=gql.Ref('DatasetSearchResult'),
    args=[
        gql.Argument(name='environmentUri', type=gql.NonNullableType(gql.String)),
        gql.Argument(name='groupUri', type=gql.NonNullableType(gql.String)),
        gql.Argument(name='filter', type=gql.Ref('DatasetFilter')),
    ],
    resolver=list_datasets_owned_by_env_group,
    test_scope='Dataset',
)

listS3ObjectKeys = gql.QueryField(
    name='listS3ObjectKeys',
    type=gql.ArrayType(gql.String),
    args=[
        gql.Argument(name='datasetUri', type=gql.NonNullableType(gql.String)),
    ],
    resolver=list_s3_object_keys,
)
