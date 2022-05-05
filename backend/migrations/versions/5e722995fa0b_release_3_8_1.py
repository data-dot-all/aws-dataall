"""release 3.8.1

Revision ID: 5e722995fa0b
Revises: 97050ec09354
Create Date: 2021-12-22 12:56:28.698754

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "5e722995fa0b"
down_revision = "97050ec09354"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("scheduled_query")
    op.drop_table("share_object_v2")
    op.drop_table("share_object_item_v2")
    op.drop_table("dataset_query")
    op.drop_table("key_value_pair")
    op.drop_table("environment_permission")
    op.drop_table("metadata_facet")
    op.drop_table("EnvironmentRedshiftCluster")
    op.drop_table("organization_topic")
    op.drop_table("dataset_loader")
    op.drop_table("dataset_storage_location_permission")
    op.drop_table("athena_query_execution")
    op.drop_table("airflow_project")
    op.drop_table("environment_user_permission")
    op.drop_table("data_access_request")
    op.drop_table("organization_user")
    op.drop_table("apikey")
    op.drop_table("airflow_cluster_user_permission")
    op.drop_table("dataset_user_permission")
    op.drop_table("redshift_cluster_user_permission")
    op.drop_table("airflowcluster")
    op.drop_table("document")
    op.drop_table("lineage_store")
    op.drop_table("share_object_history")
    op.drop_table("saved_query")
    op.drop_table("dataset_table_permission")
    op.drop_table("metadata_tag")
    op.drop_table("dataset_access_point")
    op.drop_table("search_index")
    op.drop_table("userprofile")
    op.drop_table("metric")
    op.drop_table("all_permissions")
    op.drop_table("dataset_topic")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "dataset_topic",
        sa.Column("datasetUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("topicUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("created", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("updated", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("deleted", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint("datasetUri", "topicUri", name="dataset_topic_pkey"),
    )
    op.create_table(
        "all_permissions",
        sa.Column("objectUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("userName", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("permission", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("scope", postgresql.ARRAY(sa.VARCHAR()), autoincrement=False, nullable=True),
        sa.Column("created", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("updated", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint("objectUri", "userName", name="all_permissions_pkey"),
    )
    op.create_table(
        "metric",
        sa.Column("metricUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("metricName", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column(
            "metricValue",
            postgresql.DOUBLE_PRECISION(precision=53),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column("tags", postgresql.ARRAY(sa.VARCHAR()), autoincrement=False, nullable=True),
        sa.Column("created", postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
        sa.Column("emitter", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("AwsAccountId", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("region", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("target", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint("metricUri", name="metric_pkey"),
    )
    op.create_table(
        "userprofile",
        sa.Column("label", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("name", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("owner", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("created", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("updated", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("deleted", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("description", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.VARCHAR()), autoincrement=False, nullable=True),
        sa.Column("username", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("bio", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("b64EncodedAvatar", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint("username", name="userprofile_pkey"),
    )
    op.create_table(
        "search_index",
        sa.Column("objectUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("objectType", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("label", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("description", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.VARCHAR()), autoincrement=False, nullable=True),
        sa.Column("searcAttribute1", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("searcAttribute2", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("searcAttribute3", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("searcAttribute4", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("owner", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("created", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("updated", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint("objectUri", name="search_index_pkey"),
    )
    op.create_table(
        "dataset_access_point",
        sa.Column("label", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("name", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("owner", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("created", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("updated", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("deleted", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("description", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.VARCHAR()), autoincrement=False, nullable=True),
        sa.Column("datasetUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("projectUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("locationUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("accessPointUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("AWSAccountId", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("S3BucketName", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("S3Prefix", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("region", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("S3AccessPointName", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("accessPointCreated", sa.BOOLEAN(), autoincrement=False, nullable=False),
        sa.PrimaryKeyConstraint("accessPointUri", name="dataset_access_point_pkey"),
    )
    op.create_table(
        "metadata_tag",
        sa.Column("tagId", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("nodeId", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("nodeKind", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("Key", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("Value", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint("tagId", name="metadata_tag_pkey"),
    )
    op.create_table(
        "dataset_table_permission",
        sa.Column("userName", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("tableUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("created", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("updated", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("deleted", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("userRoleForTable", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.PrimaryKeyConstraint("userName", "tableUri", name="dataset_table_permission_pkey"),
    )
    op.create_table(
        "saved_query",
        sa.Column("label", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("name", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("owner", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("created", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("updated", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("deleted", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("description", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.VARCHAR()), autoincrement=False, nullable=True),
        sa.Column("scheduledQueryUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("savedQueryUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("queryOrder", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column("sqlBody", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint("savedQueryUri", name="saved_query_pkey"),
    )
    op.create_table(
        "share_object_history",
        sa.Column("label", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("name", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("owner", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("created", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("updated", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("deleted", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("description", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.VARCHAR()), autoincrement=False, nullable=True),
        sa.Column("shareUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("historyUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("actionName", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column(
            "actionPayload",
            postgresql.JSON(astext_type=sa.Text()),
            autoincrement=False,
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("historyUri", name="share_object_history_pkey"),
    )
    op.create_table(
        "lineage_store",
        sa.Column("name", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("version", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("guid", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column(
            "kind",
            postgresql.ENUM(
                "dataset",
                "table",
                "folder",
                "job",
                "run",
                "datasource",
                name="datanodetype",
            ),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column("parent", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("ref", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("location", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("created", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("inputs", postgresql.ARRAY(sa.VARCHAR()), autoincrement=False, nullable=True),
        sa.Column(
            "outputs",
            postgresql.ARRAY(sa.VARCHAR()),
            autoincrement=False,
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("name", "version", "ref", name="lineage_store_pkey"),
    )
    op.create_table(
        "document",
        sa.Column("label", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("name", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("owner", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("created", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("updated", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("deleted", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("description", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.VARCHAR()), autoincrement=False, nullable=True),
        sa.Column("parentUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("md", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint("parentUri", name="document_pkey"),
    )
    op.create_table(
        "airflowcluster",
        sa.Column("label", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("name", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("owner", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("created", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("updated", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("deleted", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.VARCHAR()), autoincrement=False, nullable=True),
        sa.Column("environmentUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("organizationUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("clusterUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("clusterArn", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("clusterName", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("description", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("region", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("AwsAccountId", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("kmsAlias", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("status", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("vpc", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column(
            "subnetIds",
            postgresql.ARRAY(sa.VARCHAR()),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "securityGroupIds",
            postgresql.ARRAY(sa.VARCHAR()),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column("CFNStackName", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("CFNStackStatus", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("CFNStackArn", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("IAMRoleArn", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("presignedUrl", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("imported", sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.Column(
            "configurationOptions",
            postgresql.ARRAY(sa.VARCHAR()),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column("airflowVersion", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("dagS3Path", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("pluginsS3Path", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("requirementsS3Path", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("environmentClass", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column(
            "loggingConfiguration",
            postgresql.ARRAY(sa.VARCHAR()),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column("sourceBucketArn", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("webServerAccessMode", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("maxWorkers", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column("SamlGroupName", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("webServerUrl", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint("clusterUri", name="airflowcluster_pkey"),
    )
    op.create_table(
        "redshift_cluster_user_permission",
        sa.Column("userName", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("redshiftClusterUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("created", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("updated", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("deleted", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column(
            "userRoleForRedshiftCluster",
            sa.VARCHAR(),
            autoincrement=False,
            nullable=False,
        ),
        sa.PrimaryKeyConstraint(
            "userName",
            "redshiftClusterUri",
            name="redshift_cluster_user_permission_pkey",
        ),
    )
    op.create_table(
        "dataset_user_permission",
        sa.Column("userName", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("datasetUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("created", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("updated", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("deleted", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("userRoleForDataset", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.PrimaryKeyConstraint("userName", "datasetUri", name="dataset_user_permission_pkey"),
    )
    op.create_table(
        "airflow_cluster_user_permission",
        sa.Column("userName", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("clusterUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("created", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("updated", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("deleted", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column(
            "userRoleForAirflowCluster",
            sa.VARCHAR(),
            autoincrement=False,
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("userName", "clusterUri", name="airflow_cluster_user_permission_pkey"),
    )
    op.create_table(
        "apikey",
        sa.Column("ApiKeyId", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("ApiKeySecretHash", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("userName", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column(
            "SamlGroups",
            postgresql.ARRAY(sa.VARCHAR()),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column("expires", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint("ApiKeyId", name="apikey_pkey"),
    )
    op.create_table(
        "organization_user",
        sa.Column("userName", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("organizationUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("created", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("deleted", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("userRoleInOrganization", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.PrimaryKeyConstraint("userName", "organizationUri", name="organization_user_pkey"),
    )
    op.create_table(
        "data_access_request",
        sa.Column("requestUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("datasetUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("principalId", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("principalType", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("principalName", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("requester", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("created", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("updated", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("message", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.PrimaryKeyConstraint("requestUri", name="data_access_request_pkey"),
    )
    op.create_table(
        "environment_user_permission",
        sa.Column("userName", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("environmentUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("created", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("updated", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("deleted", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("userRoleInEnvironment", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.PrimaryKeyConstraint("userName", "environmentUri", name="environment_user_permission_pkey"),
    )
    op.create_table(
        "airflow_project",
        sa.Column("clusterUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("projectUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("AwsAccountId", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("region", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("cfnStackName", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("cfnStackArn", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("cfnStackStatus", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("codeRepositoryName", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("codeRepositoryLink", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("codeRepositoryStatus", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("codePipelineStatus", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("codePipelineName", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("codePipelineLink", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("codePipelineArn", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("packageName", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("status", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.PrimaryKeyConstraint("projectUri", name="airflow_project_pkey"),
    )
    op.create_table(
        "athena_query_execution",
        sa.Column("parentUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("QueryExecutionId", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("AwsAccountId", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("queryid", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("status", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("created", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("completed", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint("QueryExecutionId", name="athena_query_execution_pkey"),
    )
    op.create_table(
        "dataset_storage_location_permission",
        sa.Column("userName", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("locationUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("created", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("updated", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("deleted", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column(
            "userRoleForDatasetStorageLocation",
            sa.VARCHAR(),
            autoincrement=False,
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("userName", "locationUri", name="dataset_storage_location_permission_pkey"),
    )
    op.create_table(
        "dataset_loader",
        sa.Column("label", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("name", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("owner", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("created", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("updated", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("deleted", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("description", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.VARCHAR()), autoincrement=False, nullable=True),
        sa.Column("loaderUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("datasetUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("IAMPrincipalArn", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("IAMRoleId", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint("loaderUri", name="dataset_loader_pkey"),
    )
    op.create_table(
        "organization_topic",
        sa.Column("label", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("name", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("owner", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("created", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("updated", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("deleted", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("description", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.VARCHAR()), autoincrement=False, nullable=True),
        sa.Column("organizationUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("topicUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.PrimaryKeyConstraint("topicUri", name="organization_topic_pkey"),
    )
    op.create_table(
        "EnvironmentRedshiftCluster",
        sa.Column("environmentUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("clusterUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("created", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("updated", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("deleted", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint("environmentUri", "clusterUri", name="EnvironmentRedshiftCluster_pkey"),
    )
    op.create_table(
        "metadata_facet",
        sa.Column("facetId", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("guid", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column(
            "_schema",
            postgresql.JSON(astext_type=sa.Text()),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "doc",
            postgresql.JSON(astext_type=sa.Text()),
            autoincrement=False,
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("facetId", name="metadata_facet_pkey"),
    )
    op.create_table(
        "environment_permission",
        sa.Column("entityUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("environmentUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("entityType", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("created", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("updated", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("deleted", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("entityRoleInEnvironment", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.PrimaryKeyConstraint("entityUri", "environmentUri", name="environment_permission_pkey"),
    )
    op.create_table(
        "key_value_pair",
        sa.Column("kvId", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("objectUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("key", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("value", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.PrimaryKeyConstraint("kvId", name="key_value_pair_pkey"),
    )
    op.create_table(
        "dataset_query",
        sa.Column("label", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("name", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("owner", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("created", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("updated", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("deleted", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("description", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.VARCHAR()), autoincrement=False, nullable=True),
        sa.Column("datasetUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("queryUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("body", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint("queryUri", name="dataset_query_pkey"),
    )
    op.create_table(
        "share_object_item_v2",
        sa.Column("shareUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("version", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column("shareItemUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("itemType", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("itemUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("itemName", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("created", postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
        sa.Column("updated", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("owner", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("GlueDatabaseName", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("GlueTableName", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("S3AccessPointName", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint("shareItemUri", name="share_object_item_v2_pkey"),
    )
    op.create_table(
        "share_object_v2",
        sa.Column("shareUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("version", sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column("latest", sa.BOOLEAN(), autoincrement=False, nullable=False),
        sa.Column("datasetUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("datasetName", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("principalId", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("principalType", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("status", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("created", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("updated", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("deleted", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("owner", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.PrimaryKeyConstraint("shareUri", "version", name="share_object_v2_pkey"),
    )
    op.create_table(
        "scheduled_query",
        sa.Column("label", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("name", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("owner", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("created", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("updated", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("deleted", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("description", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.VARCHAR()), autoincrement=False, nullable=True),
        sa.Column("environmentUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("scheduledQueryUri", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("SamlAdminGroupName", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("cronexpr", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint("scheduledQueryUri", name="scheduled_query_pkey"),
    )
    # ### end Alembic commands ###
