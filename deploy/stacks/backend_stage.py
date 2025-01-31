from aws_cdk import Stage, Tags, Aspects
from cdk_nag import AwsSolutionsChecks, NagSuppressions, NagPackSuppression

from .backend_stack import BackendStack
from .cdk_nag_exclusions import BACKEND_STACK_CDK_NAG_EXCLUSIONS


class BackendStage(Stage):
    def __init__(
        self,
        scope,
        id: str,
        envname='dev',
        resource_prefix='dataall',
        ecr_repository=None,
        commit_id=None,
        tooling_account_id=None,
        pipeline_bucket=None,
        vpc_id=None,
        vpc_restricted_nacls=False,
        vpc_endpoints_sg=None,
        internet_facing=True,
        custom_domain=None,
        apigw_custom_domain=None,
        ip_ranges=None,
        apig_vpce=None,
        prod_sizing=False,
        enable_cw_canaries=False,
        enable_cw_rum=False,
        shared_dashboard_sessions='anonymous',
        enable_opensearch_serverless=False,
        enable_pivot_role_auto_create=False,
        codeartifact_domain_name=None,
        codeartifact_pip_repo_name=None,
        reauth_config=None,
        cognito_user_session_timeout_inmins=43200,
        custom_auth=None,
        custom_waf_rules=None,
        with_approval_tests=False,
        allowed_origins='*',
        log_retention_duration=None,
        deploy_dms_stack=False,
        old_aurora_connection_secret_arn=None,
        **kwargs,
    ):
        super().__init__(scope, id, **kwargs)

        backend_stack = BackendStack(
            self,
            'backend-stack',
            envname=envname,
            resource_prefix=resource_prefix,
            tooling_account_id=tooling_account_id,
            ecr_repository=ecr_repository,
            pipeline_bucket=pipeline_bucket,
            image_tag=commit_id,
            vpc_id=vpc_id,
            vpc_restricted_nacls=vpc_restricted_nacls,
            vpc_endpoints_sg=vpc_endpoints_sg,
            internet_facing=internet_facing,
            custom_domain=custom_domain,
            apigw_custom_domain=apigw_custom_domain,
            ip_ranges=ip_ranges,
            apig_vpce=apig_vpce,
            prod_sizing=prod_sizing,
            enable_cw_canaries=enable_cw_canaries,
            enable_cw_rum=enable_cw_rum,
            shared_dashboard_sessions=shared_dashboard_sessions,
            enable_opensearch_serverless=enable_opensearch_serverless,
            enable_pivot_role_auto_create=enable_pivot_role_auto_create,
            codeartifact_domain_name=codeartifact_domain_name,
            codeartifact_pip_repo_name=codeartifact_pip_repo_name,
            reauth_config=reauth_config,
            cognito_user_session_timeout_inmins=cognito_user_session_timeout_inmins,
            custom_auth=custom_auth,
            custom_waf_rules=custom_waf_rules,
            with_approval_tests=with_approval_tests,
            allowed_origins=allowed_origins,
            log_retention_duration=log_retention_duration,
            deploy_dms_stack=deploy_dms_stack,
            old_aurora_connection_secret_arn=old_aurora_connection_secret_arn,
            **kwargs,
        )

        Tags.of(backend_stack).add('Application', f'{resource_prefix}-{envname}')

        Aspects.of(backend_stack).add(AwsSolutionsChecks(reports=True, verbose=True))

        NagSuppressions.add_stack_suppressions(
            backend_stack,
            suppressions=[
                NagPackSuppression(id=rule_suppressed['id'], reason=rule_suppressed['reason'])
                for rule_suppressed in BACKEND_STACK_CDK_NAG_EXCLUSIONS
            ],
            apply_to_nested_stacks=True,
        )
