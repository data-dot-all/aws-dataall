from dataall.base.api import gql
from dataall.modules.dataset_sharing.api.resolvers import (
    add_shared_item,
    approve_share_object,
    create_share_object,
    delete_share_object,
    reapply_items_share_object,
    reject_share_object,
    remove_shared_item,
    revoke_items_share_object,
    submit_share_object,
    update_share_reject_purpose,
    update_share_request_purpose,
    verify_items_share_object,
    verify_dataset_share_objects,
)

createShareObject = gql.MutationField(
    name='createShareObject',
    args=[
        gql.Argument(name='datasetUri', type=gql.NonNullableType(gql.String)),
        gql.Argument(name='itemUri', type=gql.String),
        gql.Argument(name='itemType', type=gql.String),
        gql.Argument(name='input', type=gql.NonNullableType(gql.Ref('NewShareObjectInput'))),
    ],
    type=gql.Ref('ShareObject'),
    resolver=create_share_object,
)

deleteShareObject = gql.MutationField(
    name='deleteShareObject',
    args=[gql.Argument(name='shareUri', type=gql.NonNullableType(gql.String))],
    resolver=delete_share_object,
    type=gql.Boolean,
)

addSharedItem = gql.MutationField(
    name='addSharedItem',
    args=[
        gql.Argument(name='shareUri', type=gql.NonNullableType(gql.String)),
        gql.Argument(name='input', type=gql.Ref('AddSharedItemInput')),
    ],
    type=gql.Ref('ShareItem'),
    resolver=add_shared_item,
)


removeSharedItem = gql.MutationField(
    name='removeSharedItem',
    args=[gql.Argument(name='shareItemUri', type=gql.NonNullableType(gql.String))],
    resolver=remove_shared_item,
    type=gql.Boolean,
)

submitShareObject = gql.MutationField(
    name='submitShareObject',
    args=[gql.Argument(name='shareUri', type=gql.NonNullableType(gql.String))],
    type=gql.Ref('ShareObject'),
    resolver=submit_share_object,
)

approveShareObject = gql.MutationField(
    name='approveShareObject',
    args=[gql.Argument(name='shareUri', type=gql.NonNullableType(gql.String))],
    type=gql.Ref('ShareObject'),
    resolver=approve_share_object,
)


rejectShareObject = gql.MutationField(
    name='rejectShareObject',
    args=[
        gql.Argument(name='shareUri', type=gql.NonNullableType(gql.String)),
        gql.Argument(name='rejectPurpose', type=gql.String),
    ],
    type=gql.Ref('ShareObject'),
    resolver=reject_share_object,
)

revokeItemsShareObject = gql.MutationField(
    name='revokeItemsShareObject',
    args=[gql.Argument(name='input', type=gql.Ref('ShareItemSelectorInput'))],
    type=gql.Ref('ShareObject'),
    resolver=revoke_items_share_object,
)

verifyItemsShareObject = gql.MutationField(
    name='verifyItemsShareObject',
    args=[gql.Argument(name='input', type=gql.Ref('ShareItemSelectorInput'))],
    type=gql.Ref('ShareObject'),
    resolver=verify_items_share_object,
)

reApplyItemsShareObject = gql.MutationField(
    name='reApplyItemsShareObject',
    args=[gql.Argument(name='input', type=gql.Ref('ShareItemSelectorInput'))],
    type=gql.Ref('ShareObject'),
    resolver=reapply_items_share_object,
)

updateShareRejectReason = gql.MutationField(
    name='updateShareRejectReason',
    args=[
        gql.Argument(name='shareUri', type=gql.NonNullableType(gql.String)),
        gql.Argument(name='rejectPurpose', type=gql.String),
    ],
    type=gql.Boolean,
    resolver=update_share_reject_purpose,
)


updateShareRequestReason = gql.MutationField(
    name='updateShareRequestReason',
    args=[
        gql.Argument(name='shareUri', type=gql.NonNullableType(gql.String)),
        gql.Argument(name='requestPurpose', type=gql.String),
    ],
    type=gql.Boolean,
    resolver=update_share_request_purpose,
)

verifyDatasetShareObjects = gql.MutationField(
    name='verifyDatasetShareObjects',
    args=[gql.Argument(name='input', type=gql.Ref('ShareObjectSelectorInput'))],
    type=gql.Boolean,
    resolver=verify_dataset_share_objects,
)
