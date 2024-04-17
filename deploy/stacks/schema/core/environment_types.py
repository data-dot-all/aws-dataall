from awscdk.appsync_utils import GraphqlType, EnumType, ObjectType

from stacks.appsync import AppSyncStack
from stacks.schema.commons import CommonTypes


class EnvironmentTypes:
    def __init__(
        self,
        app_sync_stack: AppSyncStack,
        common_types: CommonTypes,
    ):
        self.environment_permission = EnumType(
            'EnvironmentPermission',
            definition=[
                'Owner',
                'Admin',
                'DatasetCreator',
                'Invited',
                'ProjectAccess',
                'NotInvited',
            ],
        )
        app_sync_stack.schema.add_type(self.environment_permission)

        self.environment_sort_field = EnumType(
            'EnvironmentSortField',
            definition=[
                'created',
                'updated',
                'label',
            ],
        )
        app_sync_stack.schema.add_type(self.environment_sort_field)

        self.vpc = ObjectType(
            'Vpc',
            definition={
                'VpcId': GraphqlType.string(is_required=True),
                'vpcUri': GraphqlType.id(is_required=True),
                # environment: Environment
                'label': GraphqlType.string(),
                'owner': GraphqlType.string(),
                'name': GraphqlType.string(),
                'description': GraphqlType.string(),
                'tags': GraphqlType.string(is_list=True),
                'AwsAccountId': GraphqlType.string(is_required=True),
                'region': GraphqlType.string(is_required=True),
                'privateSubnetIds': GraphqlType.string(is_list=True),
                'publicSubnetIds': GraphqlType.string(is_list=True),
                'SamlGroupName': GraphqlType.string(),
                'default': GraphqlType.boolean(),
            },
        )
        app_sync_stack.schema.add_type(self.vpc)

        self.environment_parameter = ObjectType(
            'EnvironmentParameter',
            definition={
                'key': GraphqlType.string(),
                'value': GraphqlType.string(),
            },
        )
        app_sync_stack.schema.add_type(self.environment_parameter)

        self.vpc_search_result = ObjectType(
            'VpcSearchResult',
            interface_types=[common_types.paged_result],
            definition={
                'nodes': self.vpc.attribute(is_list=True),
            },
        )
        app_sync_stack.schema.add_type(self.vpc_search_result)

        self.environment = ObjectType(
            'Environment',
            definition={
                'environmentUri': GraphqlType.id(),
                'label': GraphqlType.string(),
                'name': GraphqlType.string(),
                'description': GraphqlType.string(),
                'owner': GraphqlType.string(),
                'created': GraphqlType.string(),
                'updated': GraphqlType.string(),
                'deleted': GraphqlType.string(),
                'tags': GraphqlType.string(is_list=True),
                'admins': GraphqlType.string(is_list=True),
                'environmentType': GraphqlType.string(),
                'AwsAccountId': GraphqlType.string(),
                'region': GraphqlType.string(),
                'SamlGroupName': GraphqlType.string(),
                'resourcePrefix': GraphqlType.string(),
                'EnvironmentDefaultIAMRoleArn': GraphqlType.string(),
                'EnvironmentDefaultIAMRoleName': GraphqlType.string(),
                'EnvironmentDefaultIAMRoleImported': GraphqlType.boolean(),
                'datasets': GraphqlType.string(),
                # organization: Organization
                # userRoleInEnvironment: EnvironmentPermission,
                'validated': GraphqlType.string(),
                'roleCreated': GraphqlType.boolean(),
                'isOrganizationDefaultEnvironment': GraphqlType.boolean(),
                # stack: Stack
                'subscriptionsEnabled': GraphqlType.boolean(),
                'subscriptionsProducersTopicImported': GraphqlType.boolean(),
                'subscriptionsConsumersTopicImported': GraphqlType.boolean(),
                'subscriptionsConsumersTopicName': GraphqlType.string(),
                'subscriptionsProducersTopicName': GraphqlType.string(),
                'EnvironmentDefaultBucketName': GraphqlType.string(),
                'EnvironmentDefaultAthenaWorkGroup': GraphqlType.string(),
                # networks: [Vpc]
                # parameters: [EnvironmentParameter]
            },
        )
        app_sync_stack.schema.add_type(self.environment)

        self.environment_search_result = ObjectType(
            'EnvironmentSearchResult',
            interface_types=[common_types.paged_result],
            definition={
                'nodes': self.environment.attribute(is_list=True),
            },
        )
        app_sync_stack.schema.add_type(self.environment_search_result)
