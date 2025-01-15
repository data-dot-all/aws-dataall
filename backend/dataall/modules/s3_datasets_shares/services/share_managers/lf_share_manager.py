import logging
import time
from datetime import datetime
from enum import Enum, auto
from typing import List

from dataall.base.aws.iam import IAM
from dataall.base.aws.quicksight import QuicksightClient
from dataall.base.aws.sts import SessionHelper
from dataall.base.db import exceptions
from dataall.core.environment.services.environment_service import EnvironmentService
from dataall.modules.notifications.services.admin_notifications import AdminNotificationService
from dataall.modules.s3_datasets.db.dataset_models import DatasetTable
from dataall.modules.s3_datasets_shares.aws.glue_client import GlueClient
from dataall.modules.s3_datasets_shares.aws.lakeformation_client import LakeFormationClient
from dataall.modules.s3_datasets_shares.services.s3_share_alarm_service import S3ShareAlarmService
from dataall.modules.shares_base.db.share_object_models import ShareObjectItem, ShareObjectItemDataFilter
from dataall.modules.shares_base.db.share_object_repositories import ShareObjectRepository
from dataall.modules.shares_base.db.share_object_state_machines import ShareItemSM
from dataall.modules.shares_base.db.share_state_machines_repositories import ShareStatusRepository
from dataall.modules.shares_base.services.share_manager_utils import ShareErrorFormatter
from dataall.modules.shares_base.services.shares_enums import (
    ShareItemStatus,
    ShareObjectActions,
    ShareItemActions,
    ShareItemHealthStatus,
    ShareObjectDataPermission,
)
from dataall.modules.shares_base.services.sharing_service import ShareData

logger = logging.getLogger(__name__)


class LfPermType(Enum):
    Table = auto()
    Database = auto()
    ResourceLink = auto()
    Filters = auto()


PERM_TO_LF_PERMS = {
    ShareObjectDataPermission.Read.value: {
        LfPermType.Table: ['DESCRIBE', 'SELECT'],
        LfPermType.Database: ['DESCRIBE'],
        LfPermType.ResourceLink: ['DESCRIBE'],
        LfPermType.Filters: ['SELECT'],
    },
    ShareObjectDataPermission.Write.value: {
        LfPermType.Table: ['INSERT'],
        LfPermType.Database: ['CREATE_TABLE'],
        LfPermType.ResourceLink: ['DESCRIBE'],
        LfPermType.Filters: ['SELECT'],
    },
    ShareObjectDataPermission.Modify.value: {
        LfPermType.Table: ['ALTER', 'DROP', 'DELETE'],
        LfPermType.Database: ['ALTER', 'DROP'],
        LfPermType.ResourceLink: ['DESCRIBE'],
        LfPermType.Filters: ['SELECT'],
    },
}


def perms_to_lfperms(permissions: List[str], lf_perm_type: LfPermType) -> List[str]:
    lfperms = list()
    for p in permissions:
        lfperms.extend(PERM_TO_LF_PERMS[p][lf_perm_type])
    return list(dict.fromkeys(lfperms))


class LFShareManager:
    def __init__(
        self,
        session,
        share_data: ShareData,
        tables: [DatasetTable],
    ):
        self.session = session
        self.tables = tables
        self.env_group = share_data.env_group
        self.dataset = share_data.dataset
        self.share = share_data.share
        self.source_environment = share_data.source_environment
        self.target_environment = share_data.target_environment
        # Set the source account details by checking if a catalog account exists
        self.source_account_id, self.source_account_region, self.source_database_name = (
            self.init_source_account_details()
        )
        self.shared_db_name = self.build_shared_db_name()
        self.principals = self.get_share_principals()
        self.cross_account = self.target_environment.AwsAccountId != self.source_account_id
        self.tbl_level_errors = []
        self.db_level_errors = []
        # Below Clients initialized by the initialize_clients()
        self.glue_client_in_source = None
        self.glue_client_in_target = None
        self.lf_client_in_source = None
        self.lf_client_in_target = None

    def init_source_account_details(self):
        """
        Check if the catalog account is present and update the source account, source database and source region accordingly
        """
        catalog_account_present = self.check_catalog_account_exists_and_verify()
        if catalog_account_present is not False:
            if catalog_account_present is not None:
                return self.get_catalog_account_details()
            else:
                return None, None, None
        else:
            return self.source_environment.AwsAccountId, self.source_environment.region, self.dataset.GlueDatabaseName

    def get_share_principals(self) -> [str]:
        """
        Builds list of principals of the share request
        :return: List of principals' arns
        """
        principal_iam_role_arn = IAM.get_role_arn_by_name(
            account_id=self.target_environment.AwsAccountId,
            region=self.target_environment.region,
            role_name=self.share.principalRoleName,
        )
        if principal_iam_role_arn is None:
            logger.info(
                f'Principal IAM Role {self.share.principalRoleName} not found in {self.target_environment.AwsAccountId}'
            )
            logger.info('Try to build arn')
            principal_iam_role_arn = (
                f'arn:aws:iam::{self.target_environment.AwsAccountId}:role/{self.share.principalRoleName}'
            )

        return [principal_iam_role_arn]

    def build_shared_db_name(self) -> tuple:
        """
        It checks if a share is prior to 2.3.0 and builds its suffix as "_shared_" + shareUri
        For shares after 2.3.0 the suffix returned is "_shared"
        :return: Shared database name, boolean indicating if it is a new share
        """
        if self.source_database_name is None:
            return ''
        return self.source_database_name + '_shared'

    def verify_table_exists_in_source_database(self, share_item: ShareObjectItem, table: DatasetTable) -> None:
        """
        Checks if the table to be shared exists on the Glue catalog in the source account
        and add to tbl level errors if check fails
        :return: None
        """
        try:
            self.check_table_exists_in_source_database(share_item, table)
        except Exception:
            self.tbl_level_errors.append(
                ShareErrorFormatter.dne_error_msg('Glue Table', f'{table.GlueDatabaseName}.{table.GlueTableName}')
            )

    def check_table_exists_in_source_database(self, share_item: ShareObjectItem, table: DatasetTable) -> True:
        """
        Checks if the table to be shared exists on the Glue catalog in the source account
        :param share_item: request share item
        :param table: DatasetTable
        :return: True or raise exceptions.AWSResourceNotFound
        """
        if not self.glue_client_in_source.table_exists(table.GlueTableName):
            raise exceptions.AWSResourceNotFound(
                action='ProcessShare',
                message=(
                    f'Share Item {share_item.itemUri} found on share request'
                    f' but its correspondent Glue table {table.GlueTableName} does not exist.'
                ),
            )
        return True

    def verify_resource_link_table_exists_in_target_database(self, resource_link_name: str) -> None:
        """
        Checks if the resource link table exists on the shared Glue database in the target account
        and add to tbl level errors if check fails
        :return: None
        """
        if not self.check_resource_link_table_exists_in_target_database(resource_link_name):
            self.tbl_level_errors.append(
                ShareErrorFormatter.dne_error_msg(
                    'Resource Link Table',
                    f'{self.target_environment.AwsAccountId}/{self.shared_db_name}/{resource_link_name} ',
                )
            )

    def check_resource_link_table_exists_in_target_database(self, resource_link_name: str) -> bool:
        """
        Checks if the table to be shared exists on the Glue catalog in the target account as resource link
        :param table: DatasetTable
        :return: Boolean
        """
        if self.glue_client_in_target.table_exists(resource_link_name):
            return True
        logger.info(
            f'Resource link could not be found '
            f'on {self.target_environment.AwsAccountId}/{self.shared_db_name}/{resource_link_name}'
        )
        return False

    def revoke_iam_allowed_principals_from_table(self, table: DatasetTable) -> True:
        """
        Revoke ALL permissions to IAMAllowedPrincipal to the original table in source account.
        Needed for cross-account permissions. Unless this is revoked the table cannot be shared using LakeFormation
        :param table: DatasetTable
        :return: True if it is successful
        """
        self.lf_client_in_source.revoke_permissions_from_table(
            principals=['EVERYONE'],
            database_name=self.source_database_name,
            table_name=table.GlueTableName,
            catalog_id=self.source_account_id,
            permissions=['ALL'],
        )
        return True

    def upgrade_lakeformation_settings_in_source(self) -> None:
        """
        Upgrades LakeFormation settings to enable cross-account permissions
        :return: None
        """
        self.lf_client_in_source.upgrade_lakeformation_data_catalog_settings()

    def grant_pivot_role_all_database_permissions_to_source_database(self) -> True:
        """
        Grants 'ALL' Lake Formation permissions to data.all PivotRole to the original database in source account
        :return: True if it is successful
        """
        self.lf_client_in_source.grant_permissions_to_database(
            principals=[SessionHelper.get_delegation_role_arn(self.source_account_id, self.source_account_region)],
            database_name=self.source_database_name,
            permissions=['ALL'],
        )
        return True

    def check_shared_database_in_target(self) -> None:
        """
        Checks if shared database exists in target account
        and add to db level errors if check fails
        :return: True if dataset exists
        """
        if not self.glue_client_in_target.get_glue_database():
            self.db_level_errors.append(ShareErrorFormatter.dne_error_msg('Glue DB', self.shared_db_name))
            return False
        return True

    def check_if_exists_and_create_shared_database_in_target(self) -> dict:
        """
        Checks if shared database exists in target account
        Creates the shared database if it does not exist
        :return: boto3 glue create_database
        """

        database = self.glue_client_in_target.create_database(location=f's3://{self.dataset.S3BucketName}')
        return database

    def grant_pivot_role_all_database_permissions_to_shared_database(self) -> True:
        """
        Grants 'ALL' Lake Formation permissions to data.all PivotRole to the shared database in target account
        :return: True if it is successful
        """
        self.lf_client_in_target.grant_permissions_to_database(
            principals=[
                SessionHelper.get_delegation_role_arn(
                    self.target_environment.AwsAccountId, self.target_environment.region
                )
            ],
            database_name=self.shared_db_name,
            permissions=['ALL'],
        )
        return True

    def check_pivot_role_permissions_to_source_database(self) -> None:
        """
        Checks 'ALL' Lake Formation permissions to data.all PivotRole to the source database in source account
        :return: True if the permissions exists and are applied
        """
        principal = SessionHelper.get_delegation_role_arn(self.source_account_id, self.source_account_region)
        return self.lf_client_in_source.check_permissions_to_database(
            principals=[principal],
            database_name=self.source_database_name,
            permissions=['ALL'],
        )

    def check_pivot_role_permissions_to_shared_database(self) -> None:
        """
        Checks 'ALL' Lake Formation permissions to data.all PivotRole to the shared database in target account
        :return: True if the permissions exists and are applied
        """
        principal = SessionHelper.get_delegation_role_arn(
            self.target_environment.AwsAccountId, self.target_environment.region
        )
        return self.lf_client_in_target.check_permissions_to_database(
            principals=[principal],
            database_name=self.shared_db_name,
            permissions=['ALL'],
        )

    def check_principals_permissions_to_shared_database(self) -> None:
        """
        Checks Lake Formation permissions to data.all PivotRole to the shared database in target account
        and add to db level errors if check fails
        :return: None
        """
        if not self.lf_client_in_target.check_permissions_to_database(
            principals=self.principals,
            database_name=self.shared_db_name,
            permissions=perms_to_lfperms(self.share.permissions, LfPermType.Database),
        ):
            self.db_level_errors.append(
                ShareErrorFormatter.missing_permission_error_msg(
                    self.principals,
                    'LF',
                    perms_to_lfperms(self.share.permissions, LfPermType.Database),
                    'Glue DB',
                    self.shared_db_name,
                )
            )

    def check_target_principals_permissions_to_source_table(
        self, table: DatasetTable, share_item: ShareObjectItem, share_item_filter: ShareObjectItemDataFilter = None
    ) -> None:
        """
        Checks Lake Formation permissions to target principals to the original table in source account
        and add to tbl level errors if check fails
        :param table: DatasetTable
        :return: None
        """
        if share_item_filter:
            if not self.lf_client_in_source.check_permissions_to_table_with_filters(
                principals=self.principals,
                database_name=self.source_database_name,
                table_name=table.GlueTableName,
                catalog_id=self.source_account_id,
                permissions=perms_to_lfperms(self.share.permissions, LfPermType.Filters),
                data_filters=share_item_filter.dataFilterNames,
            ):
                self.tbl_level_errors.append(
                    ShareErrorFormatter.missing_permission_error_msg(
                        self.principals,
                        'LF',
                        perms_to_lfperms(self.share.permissions, LfPermType.Filters),
                        'Glue Table with Filters',
                        f'{table.GlueDatabaseName}.{table.GlueTableName}, Filters:{share_item_filter.dataFilterNames}',
                    )
                )
        else:
            if not self.lf_client_in_source.check_permissions_to_table_with_columns(
                principals=self.principals,
                database_name=self.source_database_name,
                table_name=table.GlueTableName,
                catalog_id=self.source_account_id,
                permissions=perms_to_lfperms(self.share.permissions, LfPermType.Table),
            ):
                self.tbl_level_errors.append(
                    ShareErrorFormatter.missing_permission_error_msg(
                        self.principals,
                        'LF',
                        perms_to_lfperms(self.share.permissions, LfPermType.Table),
                        'Glue Table',
                        f'{table.GlueDatabaseName}.{table.GlueTableName}',
                    )
                )
        return True

    def grant_pivot_role_drop_permissions_to_resource_link_table(self, resource_link_name: str) -> True:
        """
        Grants 'DROP' Lake Formation permissions to pivot role to the resource link table in target account
        :param table: DatasetTable
        :return: True if it is successful
        """
        self.lf_client_in_target.grant_permissions_to_table(
            principals=[
                SessionHelper.get_delegation_role_arn(
                    self.target_environment.AwsAccountId, self.target_environment.region
                )
            ],
            database_name=self.shared_db_name,
            table_name=resource_link_name,
            catalog_id=self.target_environment.AwsAccountId,
            permissions=['DROP'],
        )
        return True

    def grant_principals_database_permissions_to_shared_database(self) -> True:
        """
        Grants Lake Formation permissions to share principals to the shared database in target account
        :return: True if it is successful
        """
        self.lf_client_in_target.grant_permissions_to_database(
            principals=self.principals,
            database_name=self.shared_db_name,
            permissions=perms_to_lfperms(self.share.permissions, LfPermType.Database),
        )
        return True

    def grant_principals_permissions_to_source_table(
        self, table: DatasetTable, share_item: ShareObjectItem, share_item_filter: ShareObjectItemDataFilter = None
    ) -> True:
        """
        Grants Lake Formation permissions to target principals to the original table in source account
        :param table: DatasetTable
        :return: True if it is successful
        """
        if share_item_filter:
            self.lf_client_in_source.grant_permissions_to_table_with_filters(
                principals=self.principals,
                database_name=self.source_database_name,
                table_name=table.GlueTableName,
                catalog_id=self.source_account_id,
                permissions=perms_to_lfperms(self.share.permissions, LfPermType.Filters),
                data_filters=share_item_filter.dataFilterNames,
            )
        else:
            self.lf_client_in_source.grant_permissions_to_table_with_columns(
                principals=self.principals,
                database_name=self.source_database_name,
                table_name=table.GlueTableName,
                catalog_id=self.source_account_id,
                permissions=perms_to_lfperms(self.share.permissions, LfPermType.Table),
            )
            time.sleep(2)
        return True

    def check_if_exists_and_create_resource_link_table_in_shared_database(
        self, table: DatasetTable, resource_link_name: str
    ) -> True:
        """
        Checks if resource link to the source shared Glue table exists in target account
        Creates a resource link if it does not exist
        :param table: DatasetTable
        :return: True if it is successful
        """
        if not self.check_resource_link_table_exists_in_target_database(resource_link_name):
            self.glue_client_in_target.create_resource_link(
                resource_link_name=resource_link_name,
                table=table,
                catalog_id=self.source_account_id,
                database=self.source_database_name,
            )
        return True

    def grant_principals_permissions_to_resource_link_table(self, resource_link_name: str) -> True:
        """
        Grants Lake Formation permissions to share principals to the resource link table in target account
        :param table: DatasetTable
        :return: True if it is successful
        """
        self.lf_client_in_target.grant_permissions_to_table(
            principals=self.principals,
            database_name=self.shared_db_name,
            table_name=resource_link_name,
            catalog_id=self.target_environment.AwsAccountId,
            permissions=perms_to_lfperms(self.share.permissions, LfPermType.ResourceLink),
        )
        return True

    def check_principals_permissions_to_resource_link_table(self, resource_link_name: str) -> None:
        """
        Checks Lake Formation permissions to share principals to the resource link table in target account
        and add to tbl level errors if check fails
        :param table: DatasetTable
        :return: None
        """

        if not self.lf_client_in_target.check_permissions_to_table(
            principals=self.principals,
            database_name=self.shared_db_name,
            table_name=resource_link_name,
            catalog_id=self.target_environment.AwsAccountId,
            permissions=perms_to_lfperms(self.share.permissions, LfPermType.ResourceLink),
        ):
            self.tbl_level_errors.append(
                ShareErrorFormatter.missing_permission_error_msg(
                    self.principals,
                    'LF',
                    perms_to_lfperms(self.share.permissions, LfPermType.ResourceLink),
                    'Glue Table',
                    f'{self.shared_db_name}.{resource_link_name}',
                )
            )

    def revoke_principals_permissions_to_resource_link_table(self, resource_link_name) -> True:
        """
        Revokes Lake Formation permissions to share principals to the resource link table in target account
        :param table: DatasetTable
        :return: True if it is successful
        """

        self.lf_client_in_target.revoke_permissions_from_table(
            principals=self.principals,
            database_name=self.shared_db_name,
            table_name=resource_link_name,
            catalog_id=self.target_environment.AwsAccountId,
            permissions=perms_to_lfperms(self.share.permissions, LfPermType.ResourceLink),
        )
        return True

    def _clean_up_lf_permissions_account_delegation_pattern(self, table: DatasetTable) -> True:
        """
        THIS FUNCTION IS TO CLEAN UP THE SHARING MECHANISM OF DATA.ALL PRIOR TO v2.7 AND MIGRATE EXISTING
        TABLES SHARES TO DIRECT IAM PRINCIPAL SHARES MOVING FORWARD

        NOTE: THIS FUNCTION TO BE DEPRECATED IN A FUTURE RELEASE
        """

        # Get QS Principal (if applicable)
        principals = self.principals
        group_arn = None
        dashboard_enabled = EnvironmentService.get_boolean_env_param(
            self.session, self.target_environment, 'dashboardsEnabled'
        )
        if EnvironmentService.get_boolean_env_param(self.session, self.target_environment, 'dashboardsEnabled'):
            if (
                group_arn := QuicksightClient.create_quicksight_group(
                    AwsAccountId=self.target_environment.AwsAccountId, region=self.target_environment.region
                )
                .get('Group', {})
                .get('Arn')
            ):
                principals.append(group_arn)

        if group_arn:
            logger.info('Revoking QS Group Permissions to Resource Link...')
            self.lf_client_in_target.revoke_permissions_from_table(
                principals=[group_arn],
                database_name=self.shared_db_name,
                table_name=table.GlueTableName,
                catalog_id=self.target_environment.AwsAccountId,
                permissions=['DESCRIBE'],
            )

        logger.info('Revoking principal permissions from table in target...')
        self.lf_client_in_target.revoke_permissions_from_table_with_columns(
            principals=principals,
            database_name=self.source_database_name,
            table_name=table.GlueTableName,
            catalog_id=self.source_account_id,
            permissions=['DESCRIBE', 'SELECT'],
        )

        logger.info('Revoking target account permissions from source table')
        self.lf_client_in_source.revoke_permissions_from_table_with_columns(
            principals=[self.target_environment.AwsAccountId],
            database_name=self.source_database_name,
            table_name=table.GlueTableName,
            catalog_id=self.source_account_id,
            permissions=['DESCRIBE', 'SELECT'],
            permissions_with_grant_options=['DESCRIBE', 'SELECT'],
        )
        return True

    def revoke_principals_database_permissions_to_shared_database(self) -> True:
        """
        Revokes Lake Formation permissions to share principals to the shared database in target account
        :return: True if it is successful
        """
        self.lf_client_in_target.revoke_permissions_to_database(
            principals=self.principals,
            database_name=self.shared_db_name,
            permissions=perms_to_lfperms(self.share.permissions, LfPermType.Database),
        )
        return True

    def delete_resource_link_table_in_shared_database(self, resource_link_name: str) -> True:
        """
        Checks if resource link table from shared database in target account exists
        Deletes it if it exists
        :param table: DatasetTable
        :return: True if it is successful
        """
        glue_client = self.glue_client_in_target
        if not glue_client.table_exists(resource_link_name):
            return True

        glue_client.delete_table(resource_link_name)
        return True

    def delete_shared_database_in_target(self) -> True:
        """
        Checks if shared database in target account exists
        Deletes it if it exists
        :return: True if it is successful
        """
        logger.info(f'Deleting shared database {self.shared_db_name}')
        self.glue_client_in_target.delete_database()
        return True

    def revoke_principals_permissions_to_table_in_source(
        self, table: DatasetTable, share_item: ShareObjectItem, share_item_filter: ShareObjectItemDataFilter = None
    ) -> True:
        """
        Revokes Lake Formation permissions to target principals to the original table in source account
        If the table is not shared with any other team in the environment,
        it deletes resource_shares on RAM associated to revoked table
        :param table: DatasetTable
        :return: True if it is successful
        """

        if share_item_filter:
            self.lf_client_in_source.revoke_permissions_to_table_with_filters(
                principals=self.principals,
                database_name=self.source_database_name,
                table_name=table.GlueTableName,
                catalog_id=self.source_account_id,
                permissions=perms_to_lfperms(self.share.permissions, LfPermType.Filters),
                data_filters=share_item_filter.dataFilterNames,
            )
        else:
            self.lf_client_in_source.revoke_permissions_from_table_with_columns(
                principals=self.principals,
                database_name=self.source_database_name,
                table_name=table.GlueTableName,
                catalog_id=self.source_account_id,
                permissions=perms_to_lfperms(self.share.permissions, LfPermType.Table),
            )
        return True

    def handle_share_failure(
        self,
        table: DatasetTable,
        error: Exception,
    ) -> True:
        """
        Handles share failure by raising an alarm to alarmsTopic
        :param table: DatasetTable
        :param error: share error
        :return: True if alarm published successfully
        """
        logging.error(
            f'Failed to share table {table.GlueTableName} '
            f'from source account {self.source_environment.AwsAccountId}//{self.source_environment.region} '
            f'with target account {self.target_environment.AwsAccountId}/{self.target_environment.region}'
            f'due to: {error}'
        )

        S3ShareAlarmService().trigger_table_sharing_failure_alarm(table, self.share, self.target_environment)
        AdminNotificationService().notify_admins_with_error_log(
            process_error=f'Error occurred while processing glue tables share request for share with uri: {self.share.shareUri}',
            process_name='Glue tables share processor',
            error_logs=[str(error)],
        )
        return True

    def handle_revoke_failure(
        self,
        table: DatasetTable,
        error: Exception,
    ) -> True:
        """
        Handles share failure by raising an alarm to alarmsTopic
        :param table: DatasetTable
        :param error: share error
        :return: True if alarm published successfully
        """
        logger.error(
            f'Failed to revoke Lake Formation permissions to table {table.GlueTableName} '
            f'from source account {self.source_environment.AwsAccountId}//{self.source_environment.region} '
            f'with target account {self.target_environment.AwsAccountId}/{self.target_environment.region} '
            f'due to: {error}'
        )
        S3ShareAlarmService().trigger_revoke_table_sharing_failure_alarm(table, self.share, self.target_environment)
        AdminNotificationService().notify_admins_with_error_log(
            process_error=f'Error occurred while revoking glue tables share request for share with uri: {self.share.shareUri}',
            process_name='Glue tables share processor',
            error_logs=[str(error)],
        )
        return True

    def handle_revoke_clean_up_failure(
        self,
        error: Exception,
    ) -> True:
        """
        Handles share failure by raising an alarm to alarmsTopic
        :param table: DatasetTable
        :param error: share error
        :return: True if alarm published successfully
        """
        logger.error(
            f'Failed to clean up database permission or delete database '
            f'from source account {self.source_environment.AwsAccountId}//{self.source_environment.region} '
            f'with target account {self.target_environment.AwsAccountId}/{self.target_environment.region} '
            f'due to: {error}'
        )
        AdminNotificationService().notify_admins_with_error_log(
            process_error=f'Error occurred while revoking glue tables share request for share with uri: {self.share.shareUri} when cleaning database permissions',
            process_name='Glue tables share processor',
            error_logs=[str(error)],
        )
        return True

    def handle_share_failure_for_all_tables(self, tables, error, share_item_status, reapply=False):
        """
        Handle table share failure for all tables
        :param tables - List[DatasetTable]
        :param error - share error
        :param share_item_status : Status of approved/ revoked share
        returns : Returns True is handling is successful
        """
        for table in tables:
            share_item = ShareObjectRepository.find_sharable_item(self.session, self.share.shareUri, table.tableUri)
            if not reapply:
                share_item_sm = ShareItemSM(share_item_status)
                new_state = share_item_sm.run_transition(ShareObjectActions.Start.value)
                share_item_sm.update_state_single_item(self.session, share_item, new_state)
                new_state = share_item_sm.run_transition(ShareItemActions.Failure.value)
                share_item_sm.update_state_single_item(self.session, share_item, new_state)
            else:
                ShareStatusRepository.update_share_item_health_status(
                    self.session, share_item, ShareItemHealthStatus.Unhealthy.value, str(error), datetime.now()
                )

            if share_item_status == ShareItemStatus.Share_Approved.value:
                self.handle_share_failure(table=table, error=error)
            if share_item_status == ShareItemStatus.Revoke_Approved.value:
                self.handle_revoke_failure(table=table, error=error)

        return True

    def _verify_catalog_ownership(self, catalog_account_id, catalog_region, catalog_database):
        """
        Verifies the catalog ownership by checking
        1. if the pivot role is assumable in the catalog account
        2. if "owner_account_id" tag is present in the catalog account, which contains AWS account of source account / producer account -  where the data is present in S3 bucket
        Returns : Raises exception only in case there is an issue with any of above or returns True
        """
        logger.info(
            f'Database {self.dataset.GlueDatabaseName} is a resource link and '
            f'the source database {catalog_database} belongs to a catalog account {catalog_account_id}'
        )
        if SessionHelper.is_assumable_pivot_role(catalog_account_id, catalog_region):
            self._validate_catalog_ownership_tag(catalog_account_id, catalog_region, catalog_database)
        else:
            raise Exception(f'Pivot role is not assumable, catalog account {catalog_account_id} is not onboarded')

        return True

    def _validate_catalog_ownership_tag(self, catalog_account_id, catalog_region, catalog_database):
        glue_client = GlueClient(account_id=catalog_account_id, database=catalog_database, region=catalog_region)

        tags = glue_client.get_database_tags()
        if tags.get('owner_account_id', '') == self.source_environment.AwsAccountId:
            logger.info(
                f'owner_account_id tag exists and matches the source account id {self.source_environment.AwsAccountId}'
            )
        else:
            raise Exception(
                f'owner_account_id tag does not exist or does not matches the source account id {self.source_environment.AwsAccountId}'
            )

    def check_catalog_account_exists_and_verify(self):
        """
        Checks if the source account has a catalog associated with it. This is checked by getting source catalog information and checking if there exists a target database for the source db
        Return -
        True - if a catalog account is present and it is verified
        False - if no source catalog account is present
        None - if catalog account exists but there is an issue with verifing the conditions needed for source account. Check _verify_catalog_ownership for more details
        """
        try:
            catalog_dict = GlueClient(
                account_id=self.source_environment.AwsAccountId,
                region=self.source_environment.region,
                database=self.dataset.GlueDatabaseName,
            ).get_source_catalog()
            if catalog_dict is not None and catalog_dict.get('account_id') != self.source_environment.AwsAccountId:
                # Verify the ownership of dataset by checking if pivot role is assumable and ownership tag is present
                self._verify_catalog_ownership(
                    catalog_dict.get('account_id'), catalog_dict.get('region'), catalog_dict.get('database_name')
                )
            else:
                logger.info(
                    f'No Catalog information found for dataset - {self.dataset.name} containing database - {self.dataset.GlueDatabaseName}'
                )
                return False
        except Exception as e:
            logger.error(
                f'Failed to initialise catalog account details for share - {self.share.shareUri} ' f'due to: {e}'
            )
            return None
        return True

    def get_catalog_account_details(self):
        """
        Fetched the catalog details and returns a dict containing information about the catalog account
        Returns :
        'account_id' - AWS account id of catalog account
        'region' - AWS region in which the catalog account is present
        'database_name' - DB present in the catalog account
        """
        try:
            catalog_dict = GlueClient(
                account_id=self.source_environment.AwsAccountId,
                region=self.source_environment.region,
                database=self.dataset.GlueDatabaseName,
            ).get_source_catalog()
            return catalog_dict.get('account_id'), catalog_dict.get('region'), catalog_dict.get('database_name')
        except Exception as e:
            logger.error(f'Failed to fetch catalog account details for share - {self.share.shareUri} ' f'due to: {e}')
            return None, None, None

    def initialize_clients(self):
        self.lf_client_in_target = LakeFormationClient(
            account_id=self.target_environment.AwsAccountId, region=self.target_environment.region
        )
        self.lf_client_in_source = LakeFormationClient(
            account_id=self.source_account_id, region=self.source_account_region
        )
        self.glue_client_in_target = GlueClient(
            account_id=self.target_environment.AwsAccountId,
            region=self.target_environment.region,
            database=self.shared_db_name,
        )
        self.glue_client_in_source = GlueClient(
            account_id=self.source_account_id,
            region=self.source_account_region,
            database=self.source_database_name,
        )
