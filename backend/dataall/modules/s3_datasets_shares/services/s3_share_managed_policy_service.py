import json
from typing import Any, List, Dict

from dataall.base.aws.iam import IAM
from dataall.base.aws.service_quota import ServiceQuota
from dataall.base.db.exceptions import AWSServiceQuotaExceeded
from dataall.base.utils.iam_policy_utils import (
    split_policy_statements_in_chunks,
    split_policy_with_resources_in_statements,
)
from dataall.base.utils.naming_convention import NamingConventionService, NamingConventionPattern
from dataall.core.environment.services.managed_iam_policies import ManagedPolicy
import logging

log = logging.getLogger(__name__)

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(funcName)s - %(message)s  ', datefmt='%d-%b-%y %H:%M:%S', level=logging.INFO
)

OLD_IAM_ACCESS_POINT_ROLE_POLICY = 'targetDatasetAccessControlPolicy'
OLD_IAM_S3BUCKET_ROLE_POLICY = 'dataall-targetDatasetS3Bucket-AccessControlPolicy'

IAM_S3_ACCESS_POINTS_STATEMENT_SID = 'AccessPointsStatement'
IAM_S3_BUCKETS_STATEMENT_SID = 'BucketStatement'
EMPTY_STATEMENT_SID = 'EmptyStatement'

S3_ALLOWED_ACTIONS = ['s3:List*', 's3:Describe*', 's3:GetObject']
IAM_SERVICE_NAME = 'AWS Identity and Access Management (IAM)'
IAM_SERVICE_QUOTA_NAME = 'Managed policies per role'
DEFAULT_MAX_ATTACHABLE_MANAGED_POLICIES_ACCOUNT = 10


class S3SharePolicyService(ManagedPolicy):
    def __init__(self, role_name, account, region, environmentUri, resource_prefix):
        self.role_name = role_name
        self.account = account
        self.region = region
        self.environmentUri = environmentUri
        self.resource_prefix = resource_prefix
        self.policy_version_map = {}  # Policy version map helps while updating policies
        self.total_s3_stmts: List[Any] = []
        self.total_s3_kms_stmts: List[Any] = []
        self.total_s3_access_point_stmts: List[Any] = []
        self.total_s3_access_point_kms_stmts: List[Any] = []

    def initialize_statements(self):
        log.info('Extracting policy statement from all managed policies')
        share_managed_policies_name_list = self.get_managed_policies()

        for share_managed_policy in share_managed_policies_name_list:
            version_id, policy_document = IAM.get_managed_policy_default_version(
                account_id=self.account, region=self.region, policy_name=share_managed_policy
            )
            self.policy_version_map[share_managed_policy] = version_id
            s3_statements, s3_kms_statements, s3_access_point_statements, s3_kms_access_point_statements = (
                S3SharePolicyService._get_segregated_policy_statements_from_policy(policy_document)
            )
            self.total_s3_stmts.extend(s3_statements)
            self.total_s3_kms_stmts.extend(s3_kms_statements)
            self.total_s3_access_point_stmts.extend(s3_access_point_statements)
            self.total_s3_access_point_kms_stmts.extend(s3_kms_access_point_statements)

        log.debug(f'Total S3 Bucket sharing statements: {self.total_s3_stmts}')
        log.debug(f'Total KMS Bucket sharing statements : {self.total_s3_kms_stmts}')
        log.debug(f'Total S3 Access-point sharing statements : {self.total_s3_access_point_stmts}')
        log.debug(f'Total KMS Access-point sharing statements : {self.total_s3_access_point_kms_stmts}')

    @property
    def policy_type(self) -> str:
        return 'SharePolicy'

    def generate_old_policy_name(self) -> str:
        # This function should be deprecated and removed in the future
        return NamingConventionService(
            target_label=f'env-{self.environmentUri}-share-policy',
            target_uri=self.role_name,
            pattern=NamingConventionPattern.IAM_POLICY,
            resource_prefix=self.resource_prefix,
        ).build_compliant_name()

    def generate_base_policy_name(self) -> str:
        """
        Returns the base name of managed policies. This base name is without the index.
        build_compliant_name_with_index() function generated the name of the policy considering the length needed for index.
        """
        return NamingConventionService(
            target_label=f'env-{self.environmentUri}-share-policy',
            target_uri=self.role_name,
            pattern=NamingConventionPattern.IAM_POLICY,
            resource_prefix=self.resource_prefix,
        ).build_compliant_name_with_index()

    def generate_indexed_policy_name(self, index: int = 0) -> str:
        return NamingConventionService(
            target_label=f'env-{self.environmentUri}-share-policy',
            target_uri=self.role_name,
            pattern=NamingConventionPattern.IAM_POLICY,
            resource_prefix=self.resource_prefix,
        ).build_compliant_name_with_index(index)

    def generate_empty_policy(self) -> dict:
        return {
            'Version': '2012-10-17',
            'Statement': [{'Sid': EMPTY_STATEMENT_SID, 'Effect': 'Allow', 'Action': ['none:null'], 'Resource': ['*']}],
        }

    @staticmethod
    def remove_empty_statement(policy_doc: dict, statement_sid: str) -> dict:
        statement_index = S3SharePolicyService._get_statement_by_sid(policy_doc, statement_sid)
        if statement_index is not None:
            policy_doc['Statement'].pop(statement_index)
        return policy_doc

    @staticmethod
    def check_resource_in_policy_statements(target_resources: list, existing_policy_statements: List[Any]) -> bool:
        """
        Checks if the resources are in the existing policy statements
        :param target_resources: list
        :param existing_policy_statements: dict
        :return True if all target_resources in the existing policy else False
        """
        policy_resources = [
            resource for statement in existing_policy_statements for resource in statement.get('Resource')
        ]
        for target_resource in target_resources:
            if target_resource not in policy_resources:
                return False
        return True

    @staticmethod
    def check_s3_actions_in_policy_statements(existing_policy_statements: List[Any]) -> (bool, str, str):
        """
        Checks if all required s3 actions are allowed in the existing policy and there is no disallowed actions
        :param existing_policy_statements:
        :return: List[{ bool, allowed missing actions string, not allowed actions string }]
        """
        s3_actions_checker_dict = {}
        for statement in existing_policy_statements:
            statement_actions = set(statement.get('Action'))
            allowed_actions = set(S3_ALLOWED_ACTIONS)
            missing_actions = allowed_actions - statement_actions
            extra_actions = statement_actions - allowed_actions
            s3_actions_checker_dict[statement.get('Sid')] = {
                'policy_check': (missing_actions or extra_actions),
                'missing_permissions': ','.join(missing_actions),
                'extra_permissions': ','.join(extra_actions),
            }
        return s3_actions_checker_dict

    @staticmethod
    def check_if_sid_exists(sid: str, statements):
        for statement in statements:
            if sid in statement.get('Sid', ''):
                return True
        return False

    @staticmethod
    def _get_statement_by_sid(policy, sid):
        for index, statement in enumerate(policy['Statement']):
            if statement['Sid'] == sid:
                return index
        return None

    # Backwards compatibility
    def create_managed_policy_from_inline_and_delete_inline(self):
        """
        For existing consumption and team roles, the IAM managed policy won't be created.
        We need to create the policy based on the inline statements
        Finally, delete the old obsolete inline policies from the role
        """
        try:
            policy_statements = self._generate_managed_policy_statements_from_inline_policies()
            log.info(
                f'Creating policy from inline backwards compatibility. Policy Statements = {str(policy_statements)}'
            )
            policy_arns = self._create_indexed_managed_policies(policy_statements)
            # Delete obsolete inline policies
            log.info(f'Deleting {OLD_IAM_ACCESS_POINT_ROLE_POLICY} and {OLD_IAM_S3BUCKET_ROLE_POLICY}')
            self._delete_old_inline_policies()
        except Exception as e:
            raise Exception(f'Error creating policy from inline policies: {e}')
        return policy_arns

    # Backwards compatibility
    def create_managed_indexed_policy_from_managed_policy_delete_old_policy(self):
        """
        Previously, only one managed policy was created for a role.
        Convert this old managed policy into indexed policies by splitting statements into chunks
        After converting and splitting, delete the old managed policy
        """
        old_managed_policy_name = self.generate_old_policy_name()
        log.info(
            f'Converting old managed policy with name: {old_managed_policy_name} to indexed managed policy with index: 0'
        )
        policy_document = IAM.get_managed_policy_document_by_name(
            account_id=self.account, region=self.region, policy_name=old_managed_policy_name
        )

        if not policy_document:
            raise Exception('Failed to fetch policy document while converting to indexed managed policy')

        s3_statements, s3_kms_statements, s3_access_point_statements, s3_kms_access_point_statements = (
            S3SharePolicyService._get_segregated_policy_statements_from_policy(policy_document)
        )

        log.debug(f'Total S3 Bucket sharing statements: {s3_statements}')
        log.debug(f'Total KMS Bucket sharing statements : {s3_kms_statements}')
        log.debug(f'Total S3 Access-point sharing statements : {s3_access_point_statements}')
        log.debug(f'Total KMS Access-point sharing statements : {s3_kms_access_point_statements}')

        policy_statements = []
        if len(s3_statements + s3_access_point_statements) > 0:
            existing_bucket_s3_statements = self._split_and_generate_statement_chunks(
                statements_s3=s3_statements, statements_kms=s3_kms_statements, sid=IAM_S3_BUCKETS_STATEMENT_SID
            )
            existing_bucket_s3_access_point_statement = self._split_and_generate_statement_chunks(
                statements_s3=s3_access_point_statements,
                statements_kms=s3_kms_access_point_statements,
                sid=IAM_S3_ACCESS_POINTS_STATEMENT_SID,
            )
            policy_statements = existing_bucket_s3_statements + existing_bucket_s3_access_point_statement

        log.info(
            f'Found policy statements for existing managed policy. Number of policy statements after splitting: {len(policy_statements)}'
        )
        self._create_indexed_managed_policies(policy_statements)

        if self.check_if_policy_attached(policy_name=old_managed_policy_name):
            IAM.detach_policy_from_role(
                account_id=self.account,
                region=self.region,
                role_name=self.role_name,
                policy_name=old_managed_policy_name,
            )

        IAM.delete_managed_policy_non_default_versions(
            account_id=self.account, region=self.region, policy_name=old_managed_policy_name
        )
        IAM.delete_managed_policy_by_name(
            account_id=self.account, region=self.region, policy_name=old_managed_policy_name
        )

    def merge_statements_and_update_policies(
        self, target_sid: str, target_s3_statements: List[Any], target_s3_kms_statements: List[Any]
    ):
        """
        This method is responsible for merging policy statements, re-generating chunks consisting of statements.
        Creates new policies (if needed) and then updates existing policies with statement chunks.
        Based on target_sid:
        1. This method merges all the S3 statments
        2. Splits the policy into policy chunks, where each chunk is <= size of the policy ( this is approximately true )
        3. Check if there are any missing policies and create them
        4. Check if extra policies are required and also checks if those policies can be attached to the role (At the time of writing, IAM role has limit of 10 managed policies and can be increased to 20 )
        5. Once policies are created, fill/update the policies with the policy chunks
        6. Delete ( if any ) extra policies which are remaining
        """
        share_managed_policies_name_list = self.get_managed_policies()
        total_s3_iam_policy_stmts: List[Dict] = []
        total_s3_iam_policy_kms_stmts: List[Dict] = []
        total_s3_iam_policy_access_point_stmts: List[Dict] = []
        total_s3_iam_policy_access_point_kms_stmts: List[Dict] = []

        if target_sid == IAM_S3_BUCKETS_STATEMENT_SID:
            total_s3_iam_policy_stmts = target_s3_statements
            total_s3_iam_policy_kms_stmts = target_s3_kms_statements
            total_s3_iam_policy_access_point_stmts.extend(self.total_s3_access_point_stmts)
            total_s3_iam_policy_access_point_kms_stmts.extend(self.total_s3_access_point_kms_stmts)
        else:
            total_s3_iam_policy_access_point_stmts = target_s3_statements
            total_s3_iam_policy_access_point_kms_stmts = target_s3_kms_statements
            total_s3_iam_policy_stmts.extend(self.total_s3_stmts)
            total_s3_iam_policy_kms_stmts.extend(self.total_s3_kms_stmts)

        aggregated_iam_policy_statements = (
            total_s3_iam_policy_stmts
            + total_s3_iam_policy_kms_stmts
            + total_s3_iam_policy_access_point_stmts
            + total_s3_iam_policy_access_point_kms_stmts
        )
        log.info(f'Total number of policy statements after merging: {len(aggregated_iam_policy_statements)}')

        if len(aggregated_iam_policy_statements) == 0:
            log.info('Attaching empty policy statement')
            empty_policy = self.generate_empty_policy()
            log.info(empty_policy['Statement'])
            aggregated_iam_policy_statements = empty_policy['Statement']

        policy_document_chunks = split_policy_statements_in_chunks(aggregated_iam_policy_statements)
        log.info(f'Number of policy chunks created: {len(policy_document_chunks)}')
        log.debug(policy_document_chunks)

        log.info('Checking if there are any missing policies.')
        # Check if there are policies which do not exist but should have existed
        current_policy_indexes = [int(policy[-1]) for policy in share_managed_policies_name_list]
        integer_indexes = list(range(0, len(share_managed_policies_name_list)))
        missing_policies_indexes = [index for index in integer_indexes if index not in current_policy_indexes]
        if len(missing_policies_indexes) > 0:
            log.info(f'Creating missing policies for indexes: {missing_policies_indexes}')
            self._create_empty_policies_with_indexes(indexes=missing_policies_indexes)

        # Check if managed policies can be attached to target requester role and new service policies do not exceed service quota limit
        log.info('Checking service quota limit for number of managed policies which can be attached to role')
        self._check_iam_managed_policy_attachment_limit(policy_document_chunks)

        # Check if the number of policies required are greater than currently present
        if len(policy_document_chunks) > len(share_managed_policies_name_list):
            additional_policy_indexes = list(range(len(share_managed_policies_name_list), len(policy_document_chunks)))
            log.info(
                f'Number of policies needed are more than existing number of policies. Creating policies with indexes: {additional_policy_indexes}'
            )
            self._create_empty_policies_with_indexes(indexes=additional_policy_indexes)

        updated_share_managed_policies_name_list = self.get_managed_policies()

        log.info('Updating policy_version_map for any newly created policies')
        # Update the dict tracking the policy version for new policies which were created
        for managed_policy_name in updated_share_managed_policies_name_list:
            if managed_policy_name not in self.policy_version_map:
                self.policy_version_map[managed_policy_name] = 'v1'

        for index, statement_chunk in enumerate(policy_document_chunks):
            policy_document = self._generate_policy_document_from_statements(statement_chunk)
            # If statement length is greater than 1 then check if has empty statements sid and remove it
            if len(policy_document.get('Statement')) > 1:
                log.info('Removing empty policy statements')
                policy_document = S3SharePolicyService.remove_empty_statement(
                    policy_doc=policy_document, statement_sid=EMPTY_STATEMENT_SID
                )
            policy_name = self.generate_indexed_policy_name(index=index)
            log.debug(f'Policy document for policy {policy_name}: {policy_document}')
            IAM.update_managed_policy_default_version(
                self.account,
                self.region,
                policy_name,
                self.policy_version_map.get(policy_name, 'v1'),
                json.dumps(policy_document),
            )

        # Deleting excess policies
        if len(policy_document_chunks) < len(updated_share_managed_policies_name_list):
            excess_policies_indexes = list(
                range(len(policy_document_chunks), len(updated_share_managed_policies_name_list))
            )
            log.info(f'Found more policies than needed. Deleting policies with indexes: {excess_policies_indexes}')
            self._delete_policies_with_indexes(indexes=excess_policies_indexes)

    def _delete_policies_with_indexes(self, indexes):
        for index in indexes:
            policy_name = self.generate_indexed_policy_name(index=index)
            log.info(f'Deleting policy {policy_name}')
            # Checking if policy exist or not first before deleting
            if self.check_if_policy_exists(policy_name=policy_name):
                if self.check_if_policy_attached(policy_name=policy_name):
                    IAM.detach_policy_from_role(
                        account_id=self.account, region=self.region, role_name=self.role_name, policy_name=policy_name
                    )
                IAM.delete_managed_policy_non_default_versions(
                    account_id=self.account, region=self.region, policy_name=policy_name
                )
                IAM.delete_managed_policy_by_name(account_id=self.account, region=self.region, policy_name=policy_name)
            else:
                log.info(f'Policy with name {policy_name} does not exist')

    def _create_empty_policies_with_indexes(self, indexes):
        for index in indexes:
            policy_name = self.generate_indexed_policy_name(index=index)
            policy_document = self.generate_empty_policy()
            IAM.create_managed_policy(self.account, self.region, policy_name, json.dumps(policy_document))

    def _create_indexed_managed_policies(self, policy_statements: List[Dict]):
        if not policy_statements:
            log.info(
                'No policy statements supplied while creating indexed managed policies. Creating an empty policy statement.'
            )
            empty_policy = self.generate_empty_policy()
            policy_statements = empty_policy['Statement']

        policy_document_chunks = split_policy_statements_in_chunks(policy_statements)
        log.info(f'Number of Policy chunks made: {len(policy_document_chunks)}')

        log.info(
            'Checking service quota limit for number of managed policies which can be attached to role before converting'
        )
        self._check_iam_managed_policy_attachment_limit(policy_document_chunks)

        policy_arns = []
        for index, statement_chunk in enumerate(policy_document_chunks):
            policy_document = self._generate_policy_document_from_statements(statement_chunk)
            indexed_policy_name = self.generate_indexed_policy_name(index=index)
            policy_arns.append(
                IAM.create_managed_policy(self.account, self.region, indexed_policy_name, json.dumps(policy_document))
            )

        return policy_arns

    def _check_iam_managed_policy_attachment_limit(self, policy_document_chunks):
        number_of_policies_needed = len(policy_document_chunks)
        policies_present = self.get_managed_policies()
        managed_policies_attached_to_role = IAM.get_attached_managed_policies_to_role(
            account_id=self.account, region=self.region, role_name=self.role_name
        )
        number_of_non_share_managed_policies_attached_to_role = len(
            [policy for policy in managed_policies_attached_to_role if policy not in policies_present]
        )
        log.info(
            f'number_of_non_share_managed_policies_attached_to_role: {number_of_non_share_managed_policies_attached_to_role}'
        )

        managed_iam_policy_quota = self._get_managed_policy_quota()
        if number_of_policies_needed + number_of_non_share_managed_policies_attached_to_role > managed_iam_policy_quota:
            # Send an email notification to the requestors to increase the quota
            log.error(
                f'Number of policies which can be attached to the role is more than the service quota limit: {managed_iam_policy_quota}'
            )
            raise AWSServiceQuotaExceeded(
                action='_check_iam_managed_policy_attachment_limit',
                message=f'Number of policies which can be attached to the role is more than the service quota limit: {managed_iam_policy_quota}',
            )

        log.info(f'Role: {self.role_name} has capacity to attach managed policies')

    def _get_managed_policy_quota(self):
        # Get the number of managed policies which can be attached to the IAM role
        service_quota_client = ServiceQuota(account_id=self.account, region=self.region)
        service_code_list = service_quota_client.list_services()
        service_code = None
        for service in service_code_list:
            if service.get('ServiceName') == IAM_SERVICE_NAME:
                service_code = service.get('ServiceCode')
                break

        service_quota_code = None
        if service_code:
            service_quota_codes = service_quota_client.list_service_quota(service_code=service_code)
            for service_quota_cd in service_quota_codes:
                if service_quota_cd.get('QuotaName') == IAM_SERVICE_QUOTA_NAME:
                    service_quota_code = service_quota_cd.get('QuotaCode')
                    break

        managed_iam_policy_quota = None
        if service_quota_code:
            managed_iam_policy_quota = service_quota_client.get_service_quota_value(
                service_code=service_code, service_quota_code=service_quota_code
            )

        if managed_iam_policy_quota is None:
            managed_iam_policy_quota = DEFAULT_MAX_ATTACHABLE_MANAGED_POLICIES_ACCOUNT

        return managed_iam_policy_quota

    @staticmethod
    def _get_segregated_policy_statements_from_policy(policy_document):
        """Function to split the policy document and collect policy statements relating to S3 & KMS for bucket and access point shares
        policy_document: IAM policy document
        returns: s3_statements, s3_kms_statements, s3_access_point_statements, s3_kms_access_point_statements
        """
        policy_statements = policy_document.get('Statement', [])
        s3_statements = [
            policy_stmt
            for policy_stmt in policy_statements
            if f'{IAM_S3_BUCKETS_STATEMENT_SID}S3' in policy_stmt.get('Sid', '')
        ]
        s3_kms_statements = [
            policy_stmt
            for policy_stmt in policy_statements
            if f'{IAM_S3_BUCKETS_STATEMENT_SID}KMS' in policy_stmt.get('Sid', '')
        ]
        s3_access_point_statements = [
            policy_stmt
            for policy_stmt in policy_statements
            if f'{IAM_S3_ACCESS_POINTS_STATEMENT_SID}S3' in policy_stmt.get('Sid', '')
        ]
        s3_kms_access_point_statements = [
            policy_stmt
            for policy_stmt in policy_statements
            if f'{IAM_S3_ACCESS_POINTS_STATEMENT_SID}KMS' in policy_stmt.get('Sid', '')
        ]

        return s3_statements, s3_kms_statements, s3_access_point_statements, s3_kms_access_point_statements

    def add_resources_and_generate_split_statements(self, statements, target_resources, sid, resource_type):
        """
        Method which adds target resources to the statements & splits the statements in chunks
        returns : policy statements chunks
        """
        # Using _convert_to_array to convert to array if single resource is present and its not in array
        s3_statements_resources: List[str] = [
            resource
            for statement in statements
            for resource in S3SharePolicyService._convert_to_array(str, statement.get('Resource'))
        ]
        for target_resource in target_resources:
            if target_resource not in s3_statements_resources:
                s3_statements_resources.append(target_resource)

        if len(s3_statements_resources) == 0:
            return []

        statement_chunks = split_policy_with_resources_in_statements(
            base_sid=sid,
            effect='Allow',
            actions=S3_ALLOWED_ACTIONS if resource_type == 's3' else [f'{resource_type}:*'],
            resources=s3_statements_resources,
        )
        return statement_chunks

    def remove_resources_and_generate_split_statements(self, statements, target_resources, sid, resource_type):
        """
        Method which removes target resources from the statements & splits the statements in chunks
        returns : policy statements chunks
        """
        s3_statements_resources = [
            resource
            for statement in statements
            for resource in S3SharePolicyService._convert_to_array(str, statement.get('Resource'))
        ]
        s3_statements_resources = [resource for resource in s3_statements_resources if resource not in target_resources]

        if len(s3_statements_resources) == 0:
            return []

        statement_chunks = split_policy_with_resources_in_statements(
            base_sid=sid,
            effect='Allow',
            actions=S3_ALLOWED_ACTIONS if resource_type == 's3' else [f'{resource_type}:*'],
            resources=s3_statements_resources,
        )
        return statement_chunks

    # If item is of item type i.e. single instance if present, then wrap in an array.
    # This is helpful at places where array is required even if one element is present
    @staticmethod
    def _convert_to_array(item_type, item):
        if isinstance(item, item_type):
            return [item]
        return item

    def _generate_policy_document_from_statements(self, statements: List[Dict]):
        """
        Helper method to generate a policy from statements
        """
        if statements is None:
            raise Exception('Provide valid statements while generating policy document from statement')
        return {'Version': '2012-10-17', 'Statement': statements}

    def _generate_managed_policy_statements_from_inline_policies(self):
        """
        Get resources shared in previous inline policies
        If there are already shared resources, add them to the empty policy and remove the fake statement
        return: IAM policy document
        """
        existing_bucket_s3_resources, existing_bucket_kms_resources = self._get_policy_resources_from_inline_policy(
            OLD_IAM_S3BUCKET_ROLE_POLICY
        )
        existing_access_points_s3_resources, existing_access_points_kms_resources = (
            self._get_policy_resources_from_inline_policy(OLD_IAM_ACCESS_POINT_ROLE_POLICY)
        )
        log.info(
            f'Back-filling S3BUCKET sharing resources: S3={existing_bucket_s3_resources}, KMS={existing_bucket_kms_resources}'
        )
        log.info(
            f'Back-filling S3ACCESS POINTS sharing resources: S3={existing_access_points_s3_resources}, KMS={existing_access_points_kms_resources}'
        )
        bucket_s3_statement, bucket_kms_statement = self._generate_statement_from_inline_resources(
            existing_bucket_s3_resources, existing_bucket_kms_resources, IAM_S3_BUCKETS_STATEMENT_SID
        )
        access_points_s3_statement, access_points_kms_statement = self._generate_statement_from_inline_resources(
            existing_access_points_s3_resources,
            existing_access_points_kms_resources,
            IAM_S3_ACCESS_POINTS_STATEMENT_SID,
        )

        policy_statements = []
        if len(existing_bucket_s3_resources + existing_access_points_s3_resources) > 0:
            # Split the statements in chunks
            existing_bucket_s3_statements = self._split_and_generate_statement_chunks(
                statements_s3=bucket_s3_statement, statements_kms=bucket_kms_statement, sid=IAM_S3_BUCKETS_STATEMENT_SID
            )
            existing_bucket_s3_access_point_statements = self._split_and_generate_statement_chunks(
                statements_s3=access_points_s3_statement,
                statements_kms=access_points_kms_statement,
                sid=IAM_S3_ACCESS_POINTS_STATEMENT_SID,
            )
            policy_statements = existing_bucket_s3_statements + existing_bucket_s3_access_point_statements

        log.debug(f'Created policy statements with length: {len(policy_statements)}')
        return policy_statements

    def _split_and_generate_statement_chunks(self, statements_s3, statements_kms, sid):
        """
        Helper method to aggregate S3 and KMS statements for Bucket and Accesspoint shares and split into chunks
        """
        aggregate_statements = []
        if len(statements_s3) > 0:
            statement_resources = [
                resource
                for statement in statements_s3
                for resource in S3SharePolicyService._convert_to_array(str, statement.get('Resource'))
            ]
            aggregate_statements.extend(
                split_policy_with_resources_in_statements(
                    base_sid=f'{sid}S3',
                    effect='Allow',
                    actions=['s3:List*', 's3:Describe*', 's3:GetObject'],
                    resources=statement_resources,
                )
            )
        if len(statements_kms) > 0:
            statement_resources = [
                resource
                for statement in statements_kms
                for resource in S3SharePolicyService._convert_to_array(str, statement.get('Resource'))
            ]
            aggregate_statements.extend(
                split_policy_with_resources_in_statements(
                    base_sid=f'{sid}KMS', effect='Allow', actions=['kms:*'], resources=statement_resources
                )
            )
        return aggregate_statements

    def _generate_statement_from_inline_resources(self, bucket_s3_resources, bucket_kms_resources, base_sid):
        bucket_s3_statement = []
        bucket_kms_statement = []
        if len(bucket_s3_resources) > 0:
            bucket_s3_statement.append(
                {
                    'Sid': f'{base_sid}S3',
                    'Effect': 'Allow',
                    'Action': S3_ALLOWED_ACTIONS,
                    'Resource': bucket_s3_resources,
                }
            )
        if len(bucket_kms_resources) > 0:
            bucket_kms_statement.append(
                {'Sid': f'{base_sid}KMS', 'Effect': 'Allow', 'Action': ['kms:*'], 'Resource': bucket_kms_resources}
            )
        log.info(f'Generated statement from resources: S3: {bucket_s3_statement}, KMS: {bucket_kms_statement}')
        return bucket_s3_statement, bucket_kms_statement

    def _get_policy_resources_from_inline_policy(self, policy_name):
        # This function can only be used for backwards compatibility where policies had statement[0] for s3
        # and statement[1] for KMS permissions
        try:
            existing_policy = IAM.get_role_policy(self.account, self.region, self.role_name, policy_name)
            if existing_policy is not None:
                kms_resources = (
                    existing_policy['Statement'][1]['Resource'] if len(existing_policy['Statement']) > 1 else []
                )
                return existing_policy['Statement'][0]['Resource'], kms_resources
            else:
                return [], []
        except Exception as e:
            log.error(f'Failed to retrieve the existing policy {policy_name}: {e} ')
            return [], []

    def _delete_old_inline_policies(self):
        for policy_name in [OLD_IAM_S3BUCKET_ROLE_POLICY, OLD_IAM_ACCESS_POINT_ROLE_POLICY]:
            try:
                existing_policy = IAM.get_role_policy(self.account, self.region, self.role_name, policy_name)
                if existing_policy is not None:
                    log.info(f'Deleting inline policy: {policy_name}')
                    IAM.delete_role_policy(self.account, self.region, self.role_name, policy_name)
                else:
                    pass
            except Exception as e:
                log.error(f'Failed to retrieve the existing policy {policy_name}: {e} ')
        return True

    def process_backwards_compatibility_for_target_iam_roles(self):
        """
        Backwards compatibility
        we check if a managed share policy exists. If False, the role was introduced to data.all before this update
        we create the policy from the inline statements and attach it to the role
        """
        log.info('Checking if inline policies are present')
        old_managed_policy_name = self.generate_old_policy_name()
        old_managed_policy_exists = self.check_if_policy_exists(policy_name=old_managed_policy_name)
        share_managed_policies_exist = True if self.get_managed_policies() else False
        # If old managed policy doesn't exist and also new managed policies do not exist.
        # Then there might be inline policies, convert them to managed indexed policies
        if not old_managed_policy_exists and not share_managed_policies_exist:
            self.create_managed_policy_from_inline_and_delete_inline()
            managed_policies_list = self.get_managed_policies()
            self.attach_policies(managed_policies_list)
        # End of backwards compatibility

        """
        Backwards compatibility
        After 2.6, the IAM managed policies are created with indexes on them. This was made to solve this issue decribed here - https://github.com/data-dot-all/dataall/issues/884
        If an old managed policy exists then 
        """
        log.info(f'Old managed policy with name {old_managed_policy_name} exists: {old_managed_policy_exists}')
        if old_managed_policy_exists:
            self.create_managed_indexed_policy_from_managed_policy_delete_old_policy()
            managed_policies_list = self.get_managed_policies()
            self.attach_policies(managed_policies_list)
