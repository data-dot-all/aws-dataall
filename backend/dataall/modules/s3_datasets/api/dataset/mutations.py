from dataall.base.api import gql
from dataall.modules.s3_datasets.api.dataset.input_types import (
    ModifyDatasetInput,
    NewDatasetInput,
    ImportDatasetInput,
    DatasetMetadataInput,
)
from dataall.modules.s3_datasets.api.dataset.resolvers import (
    create_dataset,
    update_dataset,
    generate_dataset_access_token,
    delete_dataset,
    import_dataset,
    start_crawler,
    generate_metadata,
    test_read,
    read_sample_data
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
    args=[gql.Argument(name='resourceUri', type=gql.NonNullableType(gql.String)),
          gql.Argument(name='targetType', type=MetadataGenerationTargets.toGraphQLEnum()),
          gql.Argument(name='version', type=gql.Integer),
          gql.Argument(name='metadataTypes', type=gql.ArrayType(gql.String)),
          gql.Argument(name='sampleData', type=gql.Ref('SampleDataInput'))],
    type=gql.Ref('GeneratedMetadata'),
    resolver=generate_metadata,
)



test = gql.MutationField(
    name='test',
    args=[gql.Argument(name='resourceUri', type=gql.NonNullableType(gql.String)),
          gql.Argument(name='targetType', type=MetadataGenerationTargets.toGraphQLEnum()),
          gql.Argument(name='version', type=gql.Integer), #add sample data, helper data, additional context
          gql.Argument(name='metadataTypes', type=gql.ArrayType(gql.String))],
    type=gql.Ref('GeneratedMetadata'),
    resolver=test_read,
)