from dataall.base.api import gql
from dataall.modules.s3_datasets.api.dataset.input_types import ModifyDatasetInput, NewDatasetInput, ImportDatasetInput
from dataall.modules.s3_datasets.api.dataset.resolvers import (
    create_dataset,
    update_dataset,
    generate_dataset_access_token,
    delete_dataset,
    import_dataset,
    start_crawler,
    generate_metadata,
)
from dataall.modules.s3_datasets.api.dataset.enums import MetadataGenerationTargets

createDataset = gql.MutationField(
    name='createDataset',
    args=[gql.Argument(name='input', type=gql.NonNullableType(NewDatasetInput))],
    type=gql.Ref('Dataset'),
    resolver=create_dataset,
    test_scope='Dataset',
)

updateDataset = gql.MutationField(
    name='updateDataset',
    args=[
        gql.Argument(name='datasetUri', type=gql.String),
        gql.Argument(name='input', type=ModifyDatasetInput),
    ],
    type=gql.Ref('Dataset'),
    resolver=update_dataset,
    test_scope='Dataset',
)

generateDatasetAccessToken = gql.MutationField(
    name='generateDatasetAccessToken',
    args=[gql.Argument(name='datasetUri', type=gql.NonNullableType(gql.String))],
    type=gql.String,
    resolver=generate_dataset_access_token,
)


deleteDataset = gql.MutationField(
    name='deleteDataset',
    args=[
        gql.Argument(name='datasetUri', type=gql.NonNullableType(gql.String)),
        gql.Argument(name='deleteFromAWS', type=gql.Boolean),
    ],
    resolver=delete_dataset,
    type=gql.Boolean,
)


importDataset = gql.MutationField(
    name='importDataset',
    args=[gql.Argument(name='input', type=ImportDatasetInput)],
    type=gql.Ref('Dataset'),
    resolver=import_dataset,
    test_scope='Dataset',
)

StartGlueCrawler = gql.MutationField(
    name='startGlueCrawler',
    args=[
        gql.Argument(name='datasetUri', type=gql.String),
        gql.Argument(name='input', type=gql.Ref('CrawlerInput')),
    ],
    resolver=start_crawler,
    type=gql.Ref('GlueCrawler'),
)
generateMetadata = gql.MutationField(
    name='generateMetadata',
    args=[
        gql.Argument(name='resourceUri', type=gql.NonNullableType(gql.String)),
        gql.Argument(name='targetType', type=gql.NonNullableType(MetadataGenerationTargets.toGraphQLEnum())),
        gql.Argument(name='metadataTypes', type=gql.NonNullableType(gql.ArrayType(gql.String))),
        gql.Argument(name='tableSampleData', type=gql.Ref('TableSampleData')),
    ],
    type=gql.ArrayType(gql.Ref('DatasetMetadata')),
    resolver=generate_metadata,
)
