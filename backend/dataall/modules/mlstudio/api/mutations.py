"""The module defines GraphQL mutations for the SageMaker ML Studio"""
from dataall.base.api import gql
from dataall.modules.mlstudio.api.resolvers import (
    create_sagemaker_studio_user,
    delete_sagemaker_studio_user,
)

createSagemakerStudioUser = gql.MutationField(
    name='createSagemakerStudioUser',
    args=[
        gql.Argument(
            name='input',
            type=gql.NonNullableType(gql.Ref('NewSagemakerStudioUserInput')),
        )
    ],
    type=gql.Ref('SagemakerStudioUser'),
    resolver=create_sagemaker_studio_user,
)

deleteSagemakerStudioUser = gql.MutationField(
    name='deleteSagemakerStudioUser',
    args=[
        gql.Argument(
            name='sagemakerStudioUserUri',
            type=gql.NonNullableType(gql.String),
        ),
        gql.Argument(name='deleteFromAWS', type=gql.Boolean),
    ],
    type=gql.String,
    resolver=delete_sagemaker_studio_user,
)

createMLStudioDomain = gql.MutationField(
    name='createMLStudioDomain',
    args=[
        gql.Argument(
            name='input',
            type=gql.NonNullableType(gql.Ref('NewStudioDomainInput')),
        )
    ],
    type=gql.Ref('SagemakerStudioDomain'),
    resolver=create_sagemaker_studio_domain,
)

deleteMLStudioDomain = gql.MutationField(
    name='deleteMLStudioDomain',
    args=[
        gql.Argument(
            name='sagemakerStudioUri',
            type=gql.NonNullableType(gql.String),
        )
    ],
    type=gql.Boolean,
    resolver=delete_sagemaker_studio_domain,
)
