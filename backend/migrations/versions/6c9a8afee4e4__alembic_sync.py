"""alembic_sync

Revision ID: 6c9a8afee4e4
Revises: f6cd4ba7dd8d
Create Date: 2024-02-13 11:09:39.387899

"""
import os
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from dataall.base.db import has_table, get_engine

# revision identifiers, used by Alembic.
revision = '6c9a8afee4e4'
down_revision = 'f6cd4ba7dd8d'
branch_labels = None
depends_on = None


def upgrade():
    envname = os.getenv('envname', 'local')
    engine = get_engine(envname=envname).engine
    # ### commands auto generated by Alembic - please adjust! ###
    if has_table("redshiftcluster_datasettable", engine):
        op.drop_table('redshiftcluster_datasettable')
    if has_table("dataset_quality_rule", engine):
        op.drop_table('dataset_quality_rule')
    if has_table("tag", engine):
        op.drop_table('tag')
    if has_table("redshiftcluster_dataset", engine):
        op.drop_table('redshiftcluster_dataset')
    if has_table("item_tags", engine):
        op.drop_table('item_tags')
    if has_table("dataset_table_profiling_job", engine):
        op.drop_table('dataset_table_profiling_job')
    if has_table("redshiftcluster", engine):
        op.drop_table('redshiftcluster')
    if has_table("group_member", engine):
        op.drop_table('group_member')

    op.drop_constraint('dataset_bucket_datasetUri_fkey', 'dataset_bucket', type_='foreignkey')
    op.create_foreign_key('dataset_bucket_datasetUri_fkey', 'dataset_bucket', 'dataset', ['datasetUri'], ['datasetUri'], ondelete='CASCADE')
    op.create_foreign_key('environment_parameters_environmentUri_fkey', 'environment_parameters', 'environment', ['environmentUri'], ['environmentUri'])
    # ### end Alembic commands ###


def downgrade():
    envname = os.getenv('envname', 'local')
    engine = get_engine(envname=envname).engine
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('environment_parameters_environmentUri_fkey', 'environment_parameters', type_='foreignkey')
    op.drop_constraint('dataset_bucket_datasetUri_fkey', 'dataset_bucket', type_='foreignkey')
    op.create_foreign_key('dataset_bucket_datasetUri_fkey', 'dataset_bucket', 'dataset', ['datasetUri'], ['datasetUri'])
    
    if not has_table('group_member', engine):
        op.create_table('group_member',
                        sa.Column('groupUri', sa.VARCHAR(), autoincrement=False, nullable=False),
                        sa.Column('userName', sa.VARCHAR(), autoincrement=False, nullable=False),
                        sa.Column('created', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
                        sa.Column('updated', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
                        sa.Column('deleted', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
                        sa.Column('userRoleInGroup', sa.VARCHAR(), autoincrement=False, nullable=False),
                        sa.PrimaryKeyConstraint('groupUri', 'userName', name='group_member_pkey')
                        )
    if not has_table('redshiftcluster', engine):
        op.create_table('redshiftcluster',
                        sa.Column('label', sa.VARCHAR(), autoincrement=False, nullable=False),
                        sa.Column('name', sa.VARCHAR(), autoincrement=False, nullable=False),
                        sa.Column('owner', sa.VARCHAR(), autoincrement=False, nullable=False),
                        sa.Column('created', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
                        sa.Column('updated', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
                        sa.Column('deleted', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
                        sa.Column('tags', postgresql.ARRAY(sa.VARCHAR()), autoincrement=False, nullable=True),
                        sa.Column('environmentUri', sa.VARCHAR(), autoincrement=False, nullable=False),
                        sa.Column('organizationUri', sa.VARCHAR(), autoincrement=False, nullable=False),
                        sa.Column('clusterUri', sa.VARCHAR(), autoincrement=False, nullable=False),
                        sa.Column('clusterArn', sa.VARCHAR(), autoincrement=False, nullable=True),
                        sa.Column('clusterName', sa.VARCHAR(), autoincrement=False, nullable=True),
                        sa.Column('description', sa.VARCHAR(), autoincrement=False, nullable=True),
                        sa.Column('databaseName', sa.VARCHAR(), autoincrement=False, nullable=True),
                        sa.Column('databaseUser', sa.VARCHAR(), autoincrement=False, nullable=True),
                        sa.Column('masterUsername', sa.VARCHAR(), autoincrement=False, nullable=True),
                        sa.Column('masterDatabaseName', sa.VARCHAR(), autoincrement=False, nullable=True),
                        sa.Column('nodeType', sa.VARCHAR(), autoincrement=False, nullable=True),
                        sa.Column('numberOfNodes', sa.INTEGER(), autoincrement=False, nullable=True),
                        sa.Column('region', sa.VARCHAR(), autoincrement=False, nullable=True),
                        sa.Column('AwsAccountId', sa.VARCHAR(), autoincrement=False, nullable=True),
                        sa.Column('kmsAlias', sa.VARCHAR(), autoincrement=False, nullable=True),
                        sa.Column('status', sa.VARCHAR(), autoincrement=False, nullable=True),
                        sa.Column('vpc', sa.VARCHAR(), autoincrement=False, nullable=True),
                        sa.Column('subnetGroupName', sa.VARCHAR(), autoincrement=False, nullable=True),
                        sa.Column('subnetIds', postgresql.ARRAY(sa.VARCHAR()), autoincrement=False, nullable=True),
                        sa.Column('securityGroupIds', postgresql.ARRAY(sa.VARCHAR()), autoincrement=False, nullable=True),
                        sa.Column('CFNStackName', sa.VARCHAR(), autoincrement=False, nullable=True),
                        sa.Column('CFNStackStatus', sa.VARCHAR(), autoincrement=False, nullable=True),
                        sa.Column('CFNStackArn', sa.VARCHAR(), autoincrement=False, nullable=True),
                        sa.Column('IAMRoles', postgresql.ARRAY(sa.VARCHAR()), autoincrement=False, nullable=True),
                        sa.Column('endpoint', sa.VARCHAR(), autoincrement=False, nullable=True),
                        sa.Column('port', sa.INTEGER(), autoincrement=False, nullable=True),
                        sa.Column('datahubSecret', sa.VARCHAR(), autoincrement=False, nullable=True),
                        sa.Column('masterSecret', sa.VARCHAR(), autoincrement=False, nullable=True),
                        sa.Column('external_schema_created', sa.BOOLEAN(), autoincrement=False, nullable=True),
                        sa.Column('SamlGroupName', sa.VARCHAR(), autoincrement=False, nullable=True),
                        sa.Column('imported', sa.BOOLEAN(), autoincrement=False, nullable=True),
                        sa.ForeignKeyConstraint(['environmentUri'], ['environment.environmentUri'],
                                                name='fk_redshiftcluster_env_uri'),
                        sa.PrimaryKeyConstraint('clusterUri', name='redshiftcluster_pkey')
                        )
    if not has_table('dataset_table_profiling_job', engine):
        op.create_table('dataset_table_profiling_job',
                        sa.Column('label', sa.VARCHAR(), autoincrement=False, nullable=False),
                        sa.Column('name', sa.VARCHAR(), autoincrement=False, nullable=False),
                        sa.Column('owner', sa.VARCHAR(), autoincrement=False, nullable=False),
                        sa.Column('created', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
                        sa.Column('updated', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
                        sa.Column('deleted', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
                        sa.Column('description', sa.VARCHAR(), autoincrement=False, nullable=True),
                        sa.Column('tags', postgresql.ARRAY(sa.VARCHAR()), autoincrement=False, nullable=True),
                        sa.Column('tableUri', sa.VARCHAR(), autoincrement=False, nullable=False),
                        sa.Column('jobUri', sa.VARCHAR(), autoincrement=False, nullable=False),
                        sa.Column('AWSAccountId', sa.VARCHAR(), autoincrement=False, nullable=False),
                        sa.Column('RunCommandId', sa.VARCHAR(), autoincrement=False, nullable=True),
                        sa.Column('GlueDatabaseName', sa.VARCHAR(), autoincrement=False, nullable=False),
                        sa.Column('GlueTableName', sa.VARCHAR(), autoincrement=False, nullable=False),
                        sa.Column('region', sa.VARCHAR(), autoincrement=False, nullable=True),
                        sa.Column('status', sa.VARCHAR(), autoincrement=False, nullable=True),
                        sa.PrimaryKeyConstraint('jobUri', name='dataset_table_profiling_job_pkey')
                        )
    if not has_table('item_tags', engine):
        op.create_table('item_tags',
                        sa.Column('tagid', sa.VARCHAR(), autoincrement=False, nullable=False),
                        sa.Column('itemid', sa.VARCHAR(), autoincrement=False, nullable=False),
                        sa.PrimaryKeyConstraint('tagid', 'itemid', name='item_tags_pkey')
                        )
    if not has_table('redshiftcluster_dataset', engine):
        op.create_table('redshiftcluster_dataset',
                        sa.Column('clusterUri', sa.VARCHAR(), autoincrement=False, nullable=False),
                        sa.Column('datasetUri', sa.VARCHAR(), autoincrement=False, nullable=False),
                        sa.Column('datasetCopyEnabled', sa.BOOLEAN(), autoincrement=False, nullable=True),
                        sa.Column('created', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
                        sa.Column('updated', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
                        sa.Column('deleted', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
                        sa.PrimaryKeyConstraint('clusterUri', 'datasetUri', name='redshiftcluster_dataset_pkey')
                        )
    if not has_table('tag', engine):
        op.create_table('tag',
                        sa.Column('id', sa.VARCHAR(), autoincrement=False, nullable=False),
                        sa.Column('tag', sa.VARCHAR(), autoincrement=False, nullable=False),
                        sa.Column('owner', sa.VARCHAR(), autoincrement=False, nullable=True),
                        sa.Column('created', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
                        sa.PrimaryKeyConstraint('id', name='tag_pkey')
                        )
    if not has_table('dataset_quality_rule', engine):
        op.create_table('dataset_quality_rule',
                        sa.Column('label', sa.VARCHAR(), autoincrement=False, nullable=False),
                        sa.Column('name', sa.VARCHAR(), autoincrement=False, nullable=False),
                        sa.Column('owner', sa.VARCHAR(), autoincrement=False, nullable=False),
                        sa.Column('created', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
                        sa.Column('updated', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
                        sa.Column('deleted', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
                        sa.Column('description', sa.VARCHAR(), autoincrement=False, nullable=True),
                        sa.Column('tags', postgresql.ARRAY(sa.VARCHAR()), autoincrement=False, nullable=True),
                        sa.Column('datasetUri', sa.VARCHAR(), autoincrement=False, nullable=False),
                        sa.Column('ruleUri', sa.VARCHAR(), autoincrement=False, nullable=False),
                        sa.Column('query', sa.VARCHAR(), autoincrement=False, nullable=False),
                        sa.Column('status', sa.VARCHAR(), autoincrement=False, nullable=False),
                        sa.Column('logs', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
                        sa.PrimaryKeyConstraint('ruleUri', name='dataset_quality_rule_pkey')
                        )
    if not has_table('redshiftcluster_datasettable', engine):
        op.create_table('redshiftcluster_datasettable',
                        sa.Column('clusterUri', sa.VARCHAR(), autoincrement=False, nullable=False),
                        sa.Column('datasetUri', sa.VARCHAR(), autoincrement=False, nullable=False),
                        sa.Column('tableUri', sa.VARCHAR(), autoincrement=False, nullable=False),
                        sa.Column('shareUri', sa.VARCHAR(), autoincrement=False, nullable=True),
                        sa.Column('enabled', sa.BOOLEAN(), autoincrement=False, nullable=True),
                        sa.Column('schema', sa.VARCHAR(), autoincrement=False, nullable=False),
                        sa.Column('databaseName', sa.VARCHAR(), autoincrement=False, nullable=False),
                        sa.Column('created', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
                        sa.Column('updated', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
                        sa.Column('deleted', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
                        sa.Column('dataLocation', sa.VARCHAR(), autoincrement=False, nullable=True),
                        sa.PrimaryKeyConstraint('clusterUri', 'datasetUri', 'tableUri',
                                                name='redshiftcluster_datasettable_pkey')
                        )
    # ### end Alembic commands ###
