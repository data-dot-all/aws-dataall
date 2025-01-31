"""backfill_mf_enforcement_permissions

Revision ID: ba2da94739ab
Revises: b21f86882012
Create Date: 2024-10-29 12:56:06.523524

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import orm

from dataall.core.environment.db.environment_models import Environment
from dataall.core.organizations.db.organization_models import Organization
from dataall.core.permissions.api.enums import PermissionType
from dataall.core.permissions.services.permission_service import PermissionService
from dataall.core.permissions.services.resource_policy_service import ResourcePolicyService
from dataall.core.permissions.services.resources_permissions import RESOURCES_ALL_WITH_DESC
from dataall.modules.datasets_base.db.dataset_models import DatasetBase
from dataall.modules.metadata_forms.services.metadata_form_permissions import ENFORCE_METADATA_FORM

# revision identifiers, used by Alembic.
revision = 'ba2da94739ab'
down_revision = 'af2e1362d4cb'
branch_labels = None
depends_on = None


def get_session():
    bind = op.get_bind()
    session = orm.Session(bind=bind)
    return session


def upgrade():
    op.add_column('metadata_form_enforcement_rule', sa.Column('homeEntity', sa.String(), nullable=True))
    op.create_foreign_key(
        'fk_enforcement_version', 'metadata_form_version', 'metadata_form', ['metadataFormUri'], ['uri']
    )

    session = get_session()

    PermissionService.save_permission(
        session,
        name=ENFORCE_METADATA_FORM,
        description=RESOURCES_ALL_WITH_DESC.get(ENFORCE_METADATA_FORM, ENFORCE_METADATA_FORM),
        permission_type=PermissionType.RESOURCE.name,
    )
    print('Adding organization resource permissions...')
    orgs = session.query(Organization).all()
    for org in orgs:
        ResourcePolicyService.attach_resource_policy(
            session=session,
            group=org.SamlGroupName,
            resource_uri=org.organizationUri,
            permissions=[ENFORCE_METADATA_FORM],
            resource_type=Organization.__name__,
        )
    print('Adding environment resource permissions...')
    envs = session.query(Environment).all()
    for env in envs:
        ResourcePolicyService.attach_resource_policy(
            session=session,
            group=env.SamlGroupName,
            resource_uri=env.environmentUri,
            permissions=[ENFORCE_METADATA_FORM],
            resource_type=Environment.__name__,
        )
    print('Adding dataset resource permissions...')
    datasets = session.query(DatasetBase).all()
    for dataset in datasets:
        ResourcePolicyService.attach_resource_policy(
            session=session,
            group=dataset.SamlAdminGroupName,
            resource_uri=dataset.datasetUri,
            permissions=[ENFORCE_METADATA_FORM],
            resource_type=DatasetBase.__name__,
        )


def downgrade():
    op.drop_constraint('fk_enforcement_version', 'metadata_form_version', type_='foreignkey')
    op.drop_column('metadata_form_enforcement_rule', 'homeEntity')
    bind = op.get_bind()
    session = orm.Session(bind=bind)
    all_environments = session.query(Environment).all()
    for env in all_environments:
        policies = ResourcePolicyService.find_resource_policies(
            session=session,
            group=env.SamlGroupName,
            resource_uri=env.environmentUri,
            resource_type=Environment.__name__,
            permissions=[ENFORCE_METADATA_FORM],
        )
        for policy in policies:
            for resource_pol_permission in policy.permissions:
                if resource_pol_permission.permission.name in [ENFORCE_METADATA_FORM]:
                    session.delete(resource_pol_permission)
                    session.commit()

    all_organizations = session.query(Organization).all()
    for org in all_organizations:
        policies = ResourcePolicyService.find_resource_policies(
            session=session,
            group=org.SamlGroupName,
            resource_uri=org.organizationUri,
            permissions=[ENFORCE_METADATA_FORM],
            resource_type=Organization.__name__,
        )
        for policy in policies:
            for resource_pol_permission in policy.permissions:
                if resource_pol_permission.permission.name in [ENFORCE_METADATA_FORM]:
                    session.delete(resource_pol_permission)
                    session.commit()

    datasets = session.query(DatasetBase).all()
    for dataset in datasets:
        policies = ResourcePolicyService.find_resource_policies(
            session=session,
            group=dataset.SamlAdminGroupName,
            resource_uri=dataset.datasetUri,
            permissions=[ENFORCE_METADATA_FORM],
            resource_type=DatasetBase.__name__,
        )

        for policy in policies:
            for resource_pol_permission in policy.permissions:
                if resource_pol_permission.permission.name in [ENFORCE_METADATA_FORM]:
                    session.delete(resource_pol_permission)
                    session.commit()
