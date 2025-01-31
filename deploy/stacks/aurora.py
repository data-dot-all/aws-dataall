from aws_cdk import (
    Duration,
    RemovalPolicy,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_lambda as _lambda,
    aws_ssm as ssm,
    aws_kms,
    aws_ec2,
    aws_iam as iam,
)

from .pyNestedStack import pyNestedClass


class AuroraServerlessStack(pyNestedClass):
    def __init__(
        self,
        scope,
        id,
        envname='dev',
        resource_prefix='dataall',
        vpc: ec2.Vpc = None,
        lambdas: [_lambda.Function] = None,
        ecs_security_groups: [aws_ec2.SecurityGroup] = None,
        codebuild_dbmigration_sg: aws_ec2.SecurityGroup = None,
        prod_sizing=False,
        quicksight_monitoring_sg=None,
        **kwargs,
    ):
        super().__init__(scope, id, **kwargs)

        # if exclude_characters property is set make sure that the pwd regex in DbConfig is changed accordingly

        db_subnet_group = rds.SubnetGroup(
            self,
            'DbSubnetGroup',
            description=f'{envname}db subnet group',
            subnet_group_name=f'{resource_prefix}-{envname}-db-subnet-group',
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnets=vpc.select_subnets(subnet_type=ec2.SubnetType.PRIVATE_WITH_NAT, one_per_az=True).subnets
            ),
        )

        db_security_group = ec2.SecurityGroup(
            self,
            'AuroraSecurityGroup',
            security_group_name=f'{resource_prefix}-{envname}-aurora-sg',
            vpc=vpc,
            allow_all_outbound=False,
            disable_inline_rules=True,
        )

        key = aws_kms.Key(
            self,
            'AuroraKMSKey',
            removal_policy=RemovalPolicy.DESTROY if envname == 'dev' else RemovalPolicy.RETAIN,
            alias=f'{resource_prefix}-{envname}-aurora',
            enable_key_rotation=True,
        )

        db_credentials = rds.DatabaseSecret(
            self, f'{resource_prefix}-{envname}-aurora-v2-db', username='dtaadmin', encryption_key=key
        )

        database_name = f'{envname}db'

        monitoring_role = iam.Role(
            self,
            'RDSMonitoringRole',
            role_name='dataall-rds-monitoring-role',
            assumed_by=iam.ServicePrincipal('monitoring.rds.amazonaws.com'),
        )

        monitoring_role.add_to_policy(
            iam.PolicyStatement(
                actions=['logs:CreateLogGroup', 'logs:PutRetentionPolicy'],
                effect=iam.Effect.ALLOW,
                resources=['arn:aws:logs:*:*:log-group:RDS*'],
            )
        )

        monitoring_role.add_to_policy(
            iam.PolicyStatement(
                actions=['logs:CreateLogStream', 'logs:PutLogEvents', 'logs:DescribeLogStreams', 'logs:GetLogEvents'],
                effect=iam.Effect.ALLOW,
                resources=['arn:aws:logs:*:*:log-group:RDS*:log-stream:*'],
            )
        )

        database = rds.DatabaseCluster(
            self,
            f'AuroraDatabase{envname}',
            engine=rds.DatabaseClusterEngine.aurora_postgres(version=rds.AuroraPostgresEngineVersion.VER_15_4),
            deletion_protection=True,
            writer=rds.ClusterInstance.serverless_v2('writer'),
            readers=[
                # will be put in promotion tier 1 and will scale with the writer
                rds.ClusterInstance.serverless_v2('reader1', scale_with_writer=True),
                # will be put in promotion tier 2 and will not scale with the writer
                rds.ClusterInstance.serverless_v2('reader2'),
            ],
            cluster_identifier=f'{resource_prefix}-{envname}-db-v2',
            parameter_group=rds.ParameterGroup.from_parameter_group_name(
                self, 'ParameterGroup', 'default.aurora-postgresql15'
            ),
            backup=rds.BackupProps(
                retention=Duration.days(30),
            )
            if prod_sizing
            else None,
            default_database_name=database_name,
            subnet_group=db_subnet_group,
            vpc=vpc,
            credentials=rds.Credentials.from_secret(db_credentials),
            security_groups=[db_security_group],
            serverless_v2_min_capacity=4 if prod_sizing else 2,
            serverless_v2_max_capacity=16 if prod_sizing else 8,
            storage_encryption_key=key,
            monitoring_interval=Duration.seconds(1),
            monitoring_role=monitoring_role,
        )
        database.add_rotation_single_user(automatically_after=Duration.days(90))

        # Allow Lambda Connections
        if lambdas:
            l: _lambda.Function
            for l in lambdas:
                database.connections.allow_from(
                    l.connections,
                    ec2.Port.tcp(5432),
                    f'Allow dataall lambda {l.function_name}',
                )

        # Allow ECS Connections
        if ecs_security_groups:
            for sg in ecs_security_groups:
                database.connections.allow_from(
                    ec2.Connections(security_groups=[sg]),
                    ec2.Port.tcp(5432),
                    'Allow dataall ecs to db connection',
                )

        # Allow CodeBuild DB Migration Connections
        if codebuild_dbmigration_sg:
            database.connections.allow_from(
                ec2.Connections(security_groups=[codebuild_dbmigration_sg]),
                ec2.Port.tcp(5432),
                'Allow dataall ECS codebuild alembic migration',
            )

        if quicksight_monitoring_sg:
            database.connections.allow_from(
                ec2.Connections(security_groups=[quicksight_monitoring_sg]),
                ec2.Port.tcp(5432),
                'Allow Quicksight connection from Quicksight to RDS port',
            )
            database.connections.allow_to(
                ec2.Connections(security_groups=[quicksight_monitoring_sg]),
                ec2.Port.all_tcp(),
                'Allow Quicksight connection from RDS to Quicksight',
            )

        ssm.StringParameter(
            self,
            'DatabaseHostParameter',
            parameter_name=f'/dataall/{envname}/aurora/hostname',
            string_value=str(database.cluster_endpoint.hostname),
        )

        ssm.StringParameter(
            self,
            'DatabaseCredentialsArns',
            parameter_name=f'/dataall/{envname}/aurora/dbcreds',
            string_value=str(db_credentials.secret_arn),
        )

        ssm.StringParameter(
            self,
            'DatabaseDb',
            parameter_name=f'/dataall/{envname}/aurora/db',
            string_value=database_name,
        )

        ssm.StringParameter(
            self,
            'DatabaseDbKey',
            parameter_name=f'/dataall/{envname}/aurora/kms_key_id',
            string_value=key.key_id,
        )

        ssm.StringParameter(
            self,
            'DatabaseSecurityGroup',
            parameter_name=f'/dataall/{envname}/aurora/security_group_id',
            string_value=db_security_group.security_group_id,
        )

        ssm.StringParameter(
            self,
            'DatabaseResourceArn',
            parameter_name=f'/dataall/{envname}/aurora/resource_arn',
            string_value=database.cluster_arn,
        )

        ssm.StringParameter(
            self,
            'DatabaseSecretArn',
            parameter_name=f'/dataall/{envname}/aurora/secret_arn',
            string_value=db_credentials.secret_arn,
        )

        self.cluster = database
        self.aurora_sg = db_security_group
        self.db_credentials = db_credentials
        self.kms_key = key
        self.db_name = database_name
