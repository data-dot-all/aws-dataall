"""remove_dataset_table_read_permissions_from_env_admins

Revision ID: 458572580709
Revises: c6d01930179d
Create Date: 2024-05-01 17:14:08.190904

"""

from alembic import op
from sqlalchemy import orm
from sqlalchemy import and_

from dataall.core.environment.services.environment_service import EnvironmentService
from dataall.core.permissions.services.resource_policy_service import ResourcePolicyService

from dataall.modules.s3_datasets.db.dataset_models import DatasetTable, Dataset
from dataall.modules.s3_datasets_shares.db.share_object_models import ShareObject, ShareObjectItem
from dataall.modules.shares_base.services.shares_enums import ShareItemStatus, ShareableType, PrincipalType

# revision identifiers, used by Alembic.
revision = '458572580709'
down_revision = 'a991ac7a85a2'
branch_labels = None
depends_on = None


def get_session():
    bind = op.get_bind()
    session = orm.Session(bind=bind)
    return session


def upgrade():
    session = get_session()

    datasets: [Dataset] = session.query(Dataset).all()
    for dataset in datasets:
        environment = EnvironmentService.get_environment_by_uri(session, uri=dataset.environmentUri)
        env_admin_group = environment.SamlGroupName

        # if envAdmis is also Dataset admin, no need to delete permissions
        if env_admin_group == dataset.SamlAdminGroupName or env_admin_group == dataset.stewards:
            continue

        tables: [DatasetTable] = session.query(DatasetTable).filter(DatasetTable.datasetUri == dataset.datasetUri).all()
        for table in tables:
            # check, if table was shared with  env_admin_group
            table_was_shared = session.query(
                session.query(ShareObjectItem)
                .join(
                    ShareObject,
                    ShareObject.shareUri == ShareObjectItem.shareItemUri,
                )
                .filter(
                    (
                        and_(
                            ShareObject.principalType == PrincipalType.Group.value,
                            ShareObject.principalId == env_admin_group,
                            ShareObjectItem.shareItemUri == table.tableUri,
                            ShareObjectItem.itemType == ShareableType.Table.value,
                            ShareObjectItem.status.in_(
                                [
                                    ShareItemStatus.Share_Approved.value,
                                    ShareItemStatus.Share_Succeeded.value,
                                    ShareItemStatus.Share_In_Progress.value,
                                ]
                            ),
                        )
                    )
                )
                .exists()
            ).scalar()

            if not table_was_shared:
                print(
                    f'Table with uri = {table.tableUri} was not shared with group {env_admin_group}. Remove '
                    f'resource policy.'
                )
                ResourcePolicyService.delete_resource_policy(
                    session, env_admin_group, table.tableUri, DatasetTable.__name__
                )


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    print('Skipping ... ')
    # ### end Alembic commands ###
