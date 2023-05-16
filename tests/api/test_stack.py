def test_update_stack(
    client,
    tenant,
    group,
    pipeline,
    env_fixture,
    sgm_studio,
    cluster,
):
    response = update_stack_query(
        client, env_fixture.environmentUri, 'environment', group.name
    )
    assert response.data.updateStack.targetUri == env_fixture.environmentUri

    response = update_stack_query(
        client, sgm_studio.sagemakerStudioUserProfileUri, 'mlstudio', group.name
    )
    assert (
        response.data.updateStack.targetUri == sgm_studio.sagemakerStudioUserProfileUri
    )

    response = update_stack_query(client, cluster.clusterUri, 'redshift', group.name)
    assert response.data.updateStack.targetUri == cluster.clusterUri

    response = update_stack_query(
        client, pipeline.DataPipelineUri, 'pipeline', group.name
    )
    assert response.data.updateStack.targetUri == pipeline.DataPipelineUri


def update_stack_query(client, target_uri, target_type, group):
    response = client.query(
        """
        mutation updateStack($targetUri:String!, $targetType:String!){
            updateStack(targetUri:$targetUri, targetType:$targetType){
                stackUri
                targetUri
                name
            }
        }
        """,
        targetUri=target_uri,
        targetType=target_type,
        username='alice',
        groups=[group],
    )
    return response
