import logging
from sqlalchemy import and_, or_, func, case
from sqlalchemy.orm import Query
from typing import List

from dataall.base.db import exceptions, paginate
from dataall.base.db.paginator import Page
from dataall.core.organizations.db.organization_models import Organization
from dataall.core.environment.db.environment_models import Environment, EnvironmentGroup
from dataall.modules.datasets_base.db.dataset_models import DatasetBase
from dataall.modules.datasets_base.db.dataset_repositories import DatasetBaseRepository
from dataall.modules.notifications.db.notification_models import Notification
from dataall.modules.shares_base.db.share_object_models import ShareObjectItem, ShareObject
from dataall.modules.shares_base.services.shares_enums import (
    ShareItemHealthStatus,
    PrincipalType,
)

logger = logging.getLogger(__name__)


class ShareObjectRepository:
    @staticmethod
    def save_and_commit(session, share):
        session.add(share)
        session.commit()

    @staticmethod
    def find_share(session, dataset: DatasetBase, env, principal_id, principal_role_name, group_uri) -> ShareObject:
        return (
            session.query(ShareObject)
            .filter(
                and_(
                    ShareObject.datasetUri == dataset.datasetUri,
                    ShareObject.principalId == principal_id,
                    ShareObject.principalRoleName == principal_role_name,
                    ShareObject.environmentUri == env.environmentUri,
                    ShareObject.groupUri == group_uri,
                )
            )
            .first()
        )

    @staticmethod
    def find_dataset_shares(session, dataset_uri: str, share_statues: List[str] = None):
        query = session.query(ShareObject).filter(ShareObject.datasetUri == dataset_uri)

        if share_statues:
            query = query.filter(ShareObject.status.in_(share_statues))

        return query.all()

    @staticmethod
    def find_share_by_dataset_attributes(session, dataset_uri, dataset_owner, groups=None):
        if groups is None:
            groups = []
        share: ShareObject = (
            session.query(ShareObject)
            .filter(ShareObject.datasetUri == dataset_uri)
            .filter(or_(ShareObject.owner == dataset_owner, ShareObject.groupUri.in_(groups)))
            .first()
        )
        return share

    @staticmethod
    def list_dataset_shares_with_existing_shared_items(
        session, dataset_uri, share_item_shared_states, environment_uri=None, item_type=None
    ) -> [ShareObject]:
        query = (
            session.query(ShareObject)
            .outerjoin(ShareObjectItem, ShareObjectItem.shareUri == ShareObject.shareUri)
            .filter(
                and_(
                    ShareObject.datasetUri == dataset_uri,
                    ShareObject.deleted.is_(None),
                    ShareObjectItem.status.in_(share_item_shared_states),
                )
            )
        )
        if environment_uri:
            query = query.filter(ShareObject.environmentUri == environment_uri)
        if item_type:
            query = query.filter(ShareObjectItem.itemType == item_type)
        return query.all()

    @staticmethod
    def find_sharable_item(session, share_uri, item_uri) -> ShareObjectItem:
        return (
            session.query(ShareObjectItem)
            .filter(
                and_(
                    ShareObjectItem.itemUri == item_uri,
                    ShareObjectItem.shareUri == share_uri,
                )
            )
            .first()
        )

    @staticmethod
    def get_share_by_uri(session, uri):
        share = session.query(ShareObject).get(uri)
        if not share:
            raise exceptions.ObjectNotFound('Share', uri)
        return share

    @staticmethod
    def get_share_item_by_uri(session, uri):
        share_item: ShareObjectItem = session.query(ShareObjectItem).get(uri)
        if not share_item:
            raise exceptions.ObjectNotFound('ShareObjectItem', uri)

        return share_item

    @staticmethod
    def get_share_item_details(session, share_type_model, item_uri):
        return session.query(share_type_model).get(item_uri)

    @staticmethod
    def remove_share_object_item(session, share_item):
        session.delete(share_item)
        return True

    @staticmethod
    def get_share_data(session, share_uri):
        share: ShareObject = ShareObjectRepository.get_share_by_uri(session, share_uri)
        dataset: DatasetBase = DatasetBaseRepository.get_dataset_by_uri(session, share.datasetUri)

        source_environment: Environment = session.query(Environment).get(dataset.environmentUri)
        if not source_environment:
            raise exceptions.ObjectNotFound('SourceEnvironment', dataset.environmentUri)

        target_environment: Environment = session.query(Environment).get(share.environmentUri)
        if not target_environment:
            raise exceptions.ObjectNotFound('TargetEnvironment', share.environmentUri)

        env_group: EnvironmentGroup = (
            session.query(EnvironmentGroup)
            .filter(
                and_(
                    EnvironmentGroup.environmentUri == share.environmentUri,
                    EnvironmentGroup.groupUri == share.groupUri,
                )
            )
            .first()
        )
        if not env_group:
            raise Exception(
                f'Share object Team {share.groupUri} is not a member of the '
                f'environment {target_environment.name}/{target_environment.AwsAccountId}'
            )

        source_env_group: EnvironmentGroup = (
            session.query(EnvironmentGroup)
            .filter(
                and_(
                    EnvironmentGroup.environmentUri == dataset.environmentUri,
                    EnvironmentGroup.groupUri == dataset.SamlAdminGroupName,
                )
            )
            .first()
        )
        if not source_env_group:
            raise Exception(
                f'Share object Team {dataset.SamlAdminGroupName} is not a member of the '
                f'environment {dataset.environmentUri}'
            )

        return (
            share,
            dataset,
            source_environment,
            target_environment,
            source_env_group,
            env_group,
        )

    @staticmethod
    def get_share_data_items_by_type(session, share, share_type_model, share_type_uri, status=None, healthStatus=None):
        logger.info(f'Getting share items {status=}, {healthStatus=} for {share_type_model=} with {share_type_uri=}')
        query = (
            session.query(share_type_model)
            .join(
                ShareObjectItem,
                ShareObjectItem.itemUri == share_type_uri,
            )
            .join(
                ShareObject,
                ShareObject.shareUri == ShareObjectItem.shareUri,
            )
            .filter(
                and_(
                    ShareObject.datasetUri == share.datasetUri,
                    ShareObject.environmentUri == share.environmentUri,
                    ShareObject.shareUri == share.shareUri,
                )
            )
        )
        if status:
            query = query.filter(ShareObjectItem.status == status)
        if healthStatus:
            query = query.filter(ShareObjectItem.healthStatus == healthStatus)
        return query.all()

    @staticmethod
    def get_share_object_with_health_status(session, health_status_list: List[str] = None):
        query = (
            session.query(ShareObject)
            .join(ShareObjectItem, ShareObjectItem.shareUri == ShareObject.shareUri)
            .filter(ShareObjectItem.healthStatus.in_(health_status_list))
        )

        return query.all()

    @staticmethod
    def get_all_share_items_in_share(session, share_uri, status=None, healthStatus=None):
        query = (
            session.query(ShareObjectItem)
            .join(
                ShareObject,
                ShareObject.shareUri == ShareObjectItem.shareUri,
            )
            .filter(
                and_(
                    ShareObject.shareUri == share_uri,
                )
            )
        )
        if status:
            query = query.filter(ShareObjectItem.status.in_(status))
        if healthStatus:
            query = query.filter(ShareObjectItem.healthStatus.in_(healthStatus))
        return query.all()

    @staticmethod
    def list_all_active_share_objects(session) -> [ShareObject]:
        return session.query(ShareObject).filter(ShareObject.deleted.is_(None)).all()

    @staticmethod
    def list_user_received_share_requests(session, username, groups, data=None):
        query = (
            session.query(ShareObject)
            .join(
                DatasetBase,
                DatasetBase.datasetUri == ShareObject.datasetUri,
            )
            .filter(
                or_(
                    DatasetBase.businessOwnerEmail == username,
                    DatasetBase.businessOwnerDelegationEmails.contains(f'{{{username}}}'),
                    DatasetBase.stewards.in_(groups),
                    DatasetBase.SamlAdminGroupName.in_(groups),
                )
            )
        )

        if data and data.get('status'):
            if len(data.get('status')) > 0:
                query = query.filter(ShareObject.status.in_(data.get('status')))
        if data and data.get('dataset_owners'):
            if len(data.get('dataset_owners')) > 0:
                query = query.filter(DatasetBase.SamlAdminGroupName.in_(data.get('dataset_owners')))
        if data and data.get('datasets_uris'):
            if len(data.get('datasets_uris')) > 0:
                query = query.filter(ShareObject.datasetUri.in_(data.get('datasets_uris')))
        if data and data.get('share_requesters'):
            if len(data.get('share_requesters')) > 0:
                query = query.filter(ShareObject.groupUri.in_(data.get('share_requesters')))
        if data and data.get('share_iam_roles'):
            if len(data.get('share_iam_roles')) > 0:
                query = query.filter(ShareObject.principalRoleName.in_(data.get('share_iam_roles')))
        return paginate(query.order_by(ShareObject.shareUri), data.get('page', 1), data.get('pageSize', 10)).to_dict()

    @staticmethod
    def list_user_sent_share_requests(session, username, groups, data=None):
        query = (
            session.query(ShareObject)
            .join(
                Environment,
                Environment.environmentUri == ShareObject.environmentUri,
            )
            .join(
                DatasetBase,
                DatasetBase.datasetUri == ShareObject.datasetUri,
            )
            .filter(
                or_(
                    ShareObject.owner == username,
                    and_(
                        ShareObject.groupUri.in_(groups),
                        ShareObject.principalType.in_([PrincipalType.Group.value, PrincipalType.ConsumptionRole.value]),
                    ),
                )
            )
        )
        if data and data.get('status'):
            if len(data.get('status')) > 0:
                query = query.filter(ShareObject.status.in_(data.get('status')))
        if data and data.get('dataset_owners'):
            if len(data.get('dataset_owners')) > 0:
                query = query.filter(DatasetBase.SamlAdminGroupName.in_(data.get('dataset_owners')))
        if data and data.get('datasets_uris'):
            if len(data.get('datasets_uris')) > 0:
                query = query.filter(ShareObject.datasetUri.in_(data.get('datasets_uris')))
        if data and data.get('share_requesters'):
            if len(data.get('share_requesters')) > 0:
                query = query.filter(ShareObject.groupUri.in_(data.get('share_requesters')))
        if data and data.get('share_iam_roles'):
            if len(data.get('share_iam_roles')) > 0:
                query = query.filter(ShareObject.principalRoleName.in_(data.get('share_iam_roles')))
        return paginate(query.order_by(ShareObject.shareUri), data.get('page', 1), data.get('pageSize', 10)).to_dict()

    @staticmethod
    def paginate_shared_datasets(session, env_uri, data, share_item_shared_states):
        q = (
            session.query(
                ShareObjectItem.shareUri.label('shareUri'),
                DatasetBase.datasetUri.label('datasetUri'),
                DatasetBase.name.label('datasetName'),
                DatasetBase.description.label('datasetDescription'),
                Environment.environmentUri.label('environmentUri'),
                Environment.name.label('environmentName'),
                ShareObject.created.label('created'),
                ShareObject.principalId.label('principalId'),
                ShareObject.principalType.label('principalType'),
                ShareObject.environmentUri.label('targetEnvironmentUri'),
                ShareObjectItem.itemType.label('itemType'),
                ShareObjectItem.itemName.label('itemName'),
                Organization.organizationUri.label('organizationUri'),
                Organization.name.label('organizationName'),
            )
            .join(
                ShareObject,
                ShareObject.shareUri == ShareObjectItem.shareUri,
            )
            .join(
                DatasetBase,
                ShareObject.datasetUri == DatasetBase.datasetUri,
            )
            .join(
                Environment,
                Environment.environmentUri == DatasetBase.environmentUri,
            )
            .join(
                Organization,
                Organization.organizationUri == Environment.organizationUri,
            )
            .filter(
                and_(
                    ShareObjectItem.status.in_(share_item_shared_states),
                    ShareObject.environmentUri == env_uri,
                )
            )
        )

        if data.get('datasetUri'):
            dataset_uri = data.get('datasetUri')
            q = q.filter(ShareObject.datasetUri == dataset_uri)

        if data.get('itemTypes', None):
            item_types = data.get('itemTypes')
            q = q.filter(or_(*[ShareObjectItem.itemType == t for t in item_types]))

        if data.get('uniqueShares', False):
            q = q.filter(ShareObject.principalType != PrincipalType.ConsumptionRole.value)
            q = q.order_by(ShareObject.shareUri).distinct(ShareObject.shareUri)
        else:
            q = q.order_by(ShareObjectItem.itemName).distinct()

        if data.get('term'):
            term = data.get('term')
            q = q.filter(ShareObjectItem.itemName.ilike('%' + term + '%'))

        return paginate(query=q, page=data.get('page', 1), page_size=data.get('pageSize', 10)).to_dict()

    @staticmethod
    def list_user_shared_datasets(session, username, groups, share_item_shared_states, dataset_type) -> Query:
        query = (
            session.query(DatasetBase)
            .outerjoin(
                ShareObject,
                ShareObject.datasetUri == DatasetBase.datasetUri,
            )
            .outerjoin(ShareObjectItem, ShareObjectItem.shareUri == ShareObject.shareUri)
            .filter(
                and_(
                    or_(
                        ShareObject.principalId.in_(groups),
                        ShareObject.owner == username,
                    ),
                    ShareObjectItem.status.in_(share_item_shared_states),
                    DatasetBase.datasetType == dataset_type,
                )
            )
        )
        return query.distinct(DatasetBase.datasetUri)

    @staticmethod
    def list_shareable_items_of_type(session, share, type, share_type_model, share_type_uri, status=None):
        """
        type: ShareableType e.g. ShareableType.StorageLocation
        share_type_model: ShareProcessorDefinition.shareable_type e.g. DatasetStorageLocation
        share_type_uri: ShareProcessorDefinition.shareable_uri e.g DatasetStorageLocation.locationUri
        """
        logger.info(f'Getting all shareable items {status=}, for {share_type_model=}')
        query = (
            session.query(
                share_type_uri.label('itemUri'),
                share_type_model.datasetUri.label('datasetUri'),
                func.coalesce(type.value).label('itemType'),
                share_type_model.description.label('description'),
                share_type_model.name.label('itemName'),
                ShareObjectItem.shareItemUri.label('shareItemUri'),
                ShareObjectItem.status.label('status'),
                ShareObjectItem.healthStatus.label('healthStatus'),
                ShareObjectItem.healthMessage.label('healthMessage'),
                ShareObjectItem.lastVerificationTime.label('lastVerificationTime'),
                ShareObjectItem.attachedDataFilterUri.label('attachedDataFilterUri'),
                case(
                    [(ShareObjectItem.shareItemUri.isnot(None), True)],
                    else_=False,
                ).label('isShared'),
            )
            .outerjoin(
                ShareObjectItem,
                (ShareObjectItem.itemUri == share_type_uri) & (ShareObjectItem.shareUri == share.shareUri),
            )
            .filter(and_(share_type_model.datasetUri == share.datasetUri))
        )
        if status:
            query = query.filter(ShareObjectItem.status.in_(status))
        return query

    @staticmethod
    def paginated_list_shareable_items(session, subqueries: List[Query], data: dict = None):
        if len(subqueries) == 0:
            return Page([], 1, 1, 0)  # empty page. All modules are turned off
        elif len(subqueries) == 1:
            shareable_objects = subqueries[0].subquery('shareable_objects')
        else:
            shareable_objects = subqueries[0].union(*subqueries[1:]).subquery('shareable_objects')
        query = session.query(shareable_objects)
        if data:
            if data.get('term'):
                term = data.get('term')
                query = query.filter(
                    or_(
                        shareable_objects.c.itemName.ilike(term + '%'),
                        shareable_objects.c.description.ilike(term + '%'),
                    )
                )
            if 'isShared' in data:
                is_shared = data.get('isShared')
                query = query.filter(shareable_objects.c.isShared == is_shared)

            if 'isHealthy' in data:
                query = (
                    query.filter(shareable_objects.c.healthStatus == ShareItemHealthStatus.Healthy.value)
                    if data.get('isHealthy')
                    else query.filter(shareable_objects.c.healthStatus != ShareItemHealthStatus.Healthy.value)
                )

        return paginate(
            query.order_by(shareable_objects.c.itemName).distinct(), data.get('page', 1), data.get('pageSize', 10)
        ).to_dict()

    @staticmethod
    def list_active_share_object_for_dataset(session, dataset_uri):
        share_objects = (
            session.query(ShareObject)
            .filter(and_(ShareObject.datasetUri == dataset_uri, ShareObject.deleted.is_(None)))
            .all()
        )
        return share_objects

    @staticmethod
    def fetch_submitted_shares_with_notifications(session):
        """
        A method used by the scheduled ECS Task to run fetch_submitted_shares_with_notifications() process against ALL shared objects in ALL
        active share objects within dataall
        """
        pending_shares = (
            session.query(ShareObject)
            .join(
                Notification,
                and_(
                    ShareObject.shareUri == func.split_part(Notification.target_uri, '|', 1),
                    ShareObject.datasetUri == func.split_part(Notification.target_uri, '|', 2),
                ),
            )
            .filter(and_(Notification.type == 'SHARE_OBJECT_SUBMITTED', ShareObject.status == 'Submitted'))
            .all()
        )
        return pending_shares

    @staticmethod
    def get_shares_with_statuses(session, status_list: List[str]):
        query = session.query(ShareObject).filter(ShareObject.status.in_(status_list))
        return query.all()

    @staticmethod
    def get_all_active_shares_with_expiration(session):
        return (
            session.query(ShareObject)
            .filter(and_(ShareObject.expiryDate.isnot(None), ShareObject.deleted.is_(None)))
            .all()
        )

    @staticmethod
    def update_dataset_shares_expiration(session, enabledExpiration, datasetUri, expirationDate):
        """
        When share expiration is enabled on the dataset while editing a dataset
        update all the shares on that dataset and set minimum expiration on them
        """
        if enabledExpiration:
            shares = session.query(ShareObject).filter(ShareObject.datasetUri == datasetUri).all()
            for share in shares:
                if share.expiryDate is None:
                    share.expiryDate = expirationDate
        else:
            shares = (
                session.query(ShareObject)
                .filter(and_(ShareObject.datasetUri == datasetUri, ShareObject.expiryDate.isnot(None)))
                .all()
            )
            for share in shares:
                share.expiryDate = None
        session.commit()
        return True

    @staticmethod
    def delete_dataset_shares_with_no_shared_items(session, dataset_uri, share_item_shared_states):
        shares = (
            session.query(ShareObject)
            .outerjoin(ShareObjectItem, ShareObjectItem.shareUri == ShareObject.shareUri)
            .filter(
                and_(
                    ShareObject.datasetUri == dataset_uri,
                    ShareObjectItem.status.notin_(share_item_shared_states),
                )
            )
            .all()
        )
        for share in shares:
            share_items = session.query(ShareObjectItem).filter(ShareObjectItem.shareUri == share.shareUri).all()
            for item in share_items:
                session.delete(item)

            share_obj = session.query(ShareObject).filter(ShareObject.shareUri == share.shareUri).first()
            session.delete(share_obj)
