import pytest
from aws_cdk import App
from aws_cdk.assertions import Template, Match
import os
import json

from dataall.core.environment.cdk.environment_stack import EnvironmentSetup
from dataall.core.environment.db.environment_models import EnvironmentGroup
from dataall.modules.s3_datasets.db.dataset_models import S3Dataset


@pytest.fixture(scope='function', autouse=True)
def patch_extensions(mocker):
    for extension in EnvironmentSetup._EXTENSIONS:
        if extension.__name__ not in ['DatasetCustomResourcesExtension', 'DatasetGlueProfilerExtension']:
            mocker.patch(
                f'{extension.__module__}.{extension.__name__}.extent',
                return_value=True,
            )


@pytest.fixture(scope='function', autouse=True)
def another_group(db, env_fixture):
    with db.scoped_session() as session:
        env_group: EnvironmentGroup = EnvironmentGroup(
            environmentUri=env_fixture.environmentUri,
            groupUri='anothergroup',
            environmentIAMRoleArn='aontherGroupArn',
            environmentIAMRoleName='anotherGroupRole',
            environmentAthenaWorkGroup='workgroup',
        )
        session.add(env_group)
        dataset = S3Dataset(
            label='thisdataset',
            environmentUri=env_fixture.environmentUri,
            organizationUri=env_fixture.organizationUri,
            name='anotherdataset',
            description='test',
            AwsAccountId=env_fixture.AwsAccountId,
            region=env_fixture.region,
            S3BucketName='bucket',
            GlueDatabaseName='db',
            IAMDatasetAdminRoleArn='role',
            IAMDatasetAdminUserArn='xxx',
            KmsAlias='xxx',
            owner='me',
            confidentiality='C1',
            businessOwnerEmail='jeff',
            businessOwnerDelegationEmails=['andy'],
            SamlAdminGroupName=env_group.groupUri,
            GlueCrawlerName='dhCrawler',
        )
        session.add(dataset)
        yield env_group


@pytest.fixture(scope='function', autouse=True)
def patch_methods(mocker, db, env_fixture, another_group, permissions):
    mocker.patch(
        'dataall.core.environment.cdk.environment_stack.EnvironmentSetup.get_engine',
        return_value=db,
    )
    mocker.patch(
        'dataall.base.aws.sts.SessionHelper.get_delegation_role_name',
        return_value='dataall-pivot-role-name-pytest',
    )
    mocker.patch(
        'dataall.base.aws.parameter_store.ParameterStoreManager.get_parameter_value',
        return_value='False',
    )
    mocker.patch(
        'dataall.core.environment.cdk.environment_stack.EnvironmentSetup.get_target',
        return_value=env_fixture,
    )
    mocker.patch(
        'dataall.core.environment.cdk.environment_stack.EnvironmentSetup.get_environment_groups',
        return_value=[another_group],
    )
    mocker.patch(
        'dataall.base.aws.sts.SessionHelper.get_account',
        return_value='012345678901x',
    )
    mocker.patch('dataall.core.stacks.services.runtime_stacks_tagging.TagsUtil.get_engine', return_value=db)
    mocker.patch(
        'dataall.core.stacks.services.runtime_stacks_tagging.TagsUtil.get_target',
        return_value=env_fixture,
    )
    mocker.patch(
        'dataall.core.environment.cdk.environment_stack.EnvironmentSetup.get_environment_group_permissions',
        return_value=[permission.name for permission in permissions],
    )
    mocker.patch(
        'dataall.base.aws.sts.SessionHelper.get_external_id_secret',
        return_value='secretIdvalue',
    )


def test_resources_created(env_fixture, org_fixture, mocker):
    app = App()
    mocker.patch(
        'dataall.core.environment.services.managed_iam_policies.PolicyManager.get_all_policies', return_value=[]
    )

    # Create the Stack
    stack = EnvironmentSetup(app, 'Environment', target_uri=env_fixture.environmentUri)
    app.synth()
    # Prepare the stack for assertions.
    template = Template.from_stack(stack)

    # Assert that we have created:
    template.resource_properties_count_is(
        type='AWS::S3::Bucket',
        props={
            'BucketName': env_fixture.EnvironmentDefaultBucketName,
            'BucketEncryption': {
                'ServerSideEncryptionConfiguration': [{'ServerSideEncryptionByDefault': {'SSEAlgorithm': 'AES256'}}]
            },
            'PublicAccessBlockConfiguration': {
                'BlockPublicAcls': True,
                'BlockPublicPolicy': True,
                'IgnorePublicAcls': True,
                'RestrictPublicBuckets': True,
            },
        },
        count=1,
    )
    template.resource_properties_count_is(
        type='AWS::Lambda::Function',
        props={
            'FunctionName': Match.string_like_regexp('^.*lf-settings-handler.*$'),
        },
        count=1,
    )
    template.resource_properties_count_is(
        type='AWS::Lambda::Function',
        props={
            'FunctionName': Match.string_like_regexp('^.*gluedb-lf-handler.*$'),
        },
        count=1,
    )
    template.resource_count_is('AWS::Lambda::Function', 5)
    template.resource_count_is('AWS::SSM::Parameter', 5)
    template.resource_count_is('AWS::IAM::Role', 5)
    template.resource_count_is('AWS::IAM::Policy', 4)


@pytest.mark.skipif(
    not os.getenv('GITHUB_ACTIONS'), reason='Pytest used for Checkov Scan CDK Synth Output'
)
def test_checkov(env_fixture, org_fixture, mocker):
    app = App()
    mocker.patch(
        'dataall.core.environment.services.managed_iam_policies.PolicyManager.get_all_policies', return_value=[]
    )
    stack = EnvironmentSetup(app, 'Environment', target_uri=env_fixture.environmentUri)    
    template = json.dumps(app.synth().get_stack_by_name('Environment').template)
    with open('checkov_environment_synth.json', 'w') as f:
        f.write(template)
