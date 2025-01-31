import json

from aws_cdk import Stack, aws_dms as dms, aws_iam as iam
from constructs import Construct
from .pyNestedStack import pyNestedClass


task_settings = {
    'TargetMetadata': {
        'SupportLobs': True,
        'FullLobMode': True,
        'LimitedSizeLobMode': False,
    },
}


class DMSTaskStack(pyNestedClass):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        region: str,
        secret_id_aurora_v1: str,
        secret_id_aurora_v2: str,
        kms_key_for_secret_arn: str,
        database_name: str,
        vpc_security_group: str,
        replication_subnet_group_identifier: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        replication_role = iam.Role(
            self,
            'DMSReplicationRole',
            role_name='dataall-dms-replication-role',
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal('dms-data-migrations.amazonaws.com'),
                iam.ServicePrincipal('dms.amazonaws.com'),
                iam.ServicePrincipal(f'dms.{region}.amazonaws.com'),
            ),
        )
        replication_role.add_to_policy(
            iam.PolicyStatement(
                actions=['secretsmanager:DescribeSecret', 'secretsmanager:GetSecretValue'],
                effect=iam.Effect.ALLOW,
                resources=[secret_id_aurora_v1, secret_id_aurora_v2],
            )
        )

        replication_role.add_to_policy(
            iam.PolicyStatement(
                actions=['kms:Decrypt', 'kms:DescribeKey'],
                effect=iam.Effect.ALLOW,
                resources=[kms_key_for_secret_arn],
            )
        )

        cfn_replication_instance = dms.CfnReplicationInstance(
            self,
            'MyCfnReplicationInstance',
            replication_instance_class='dms.t3.medium',
            vpc_security_group_ids=[vpc_security_group],
            replication_subnet_group_identifier=replication_subnet_group_identifier,
            replication_instance_identifier='DataAllReplicationInstance',
        )
        cfn_endpoint_source = dms.CfnEndpoint(
            self,
            'DataAllSourceEndpoint',
            endpoint_type='source',
            engine_name='aurora-postgresql',
            database_name=database_name,
            postgre_sql_settings=dms.CfnEndpoint.PostgreSqlSettingsProperty(
                secrets_manager_access_role_arn=replication_role.role_arn,
                secrets_manager_secret_id=secret_id_aurora_v1,
            ),
        )

        cfn_endpoint_target = dms.CfnEndpoint(
            self,
            'DataAllTargetEndpoint',
            endpoint_type='target',
            engine_name='aurora-postgresql',
            database_name=database_name,
            postgre_sql_settings=dms.CfnEndpoint.PostgreSqlSettingsProperty(
                secrets_manager_access_role_arn=replication_role.role_arn,
                secrets_manager_secret_id=secret_id_aurora_v2,
            ),
        )

        cfn_replication_task = dms.CfnReplicationTask(
            self,
            'DataAllReplicationTask',
            migration_type='full-load',
            replication_instance_arn=cfn_replication_instance.ref,
            replication_task_settings=json.dumps(task_settings),
            source_endpoint_arn=cfn_endpoint_source.ref,
            table_mappings='{ "rules": [ { "rule-type": "selection", "rule-id": "1", "rule-name": "1", "object-locator": { "schema-name": "%", "table-name": "%" }, "rule-action": "include" } ] }',
            target_endpoint_arn=cfn_endpoint_target.ref,
        )
