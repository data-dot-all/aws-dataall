from dataall.base.context import get_context
from dataall.base.db import exceptions
from dataall.base.db.paginator import paginate_list
from dataall.core.environment.db.environment_repositories import EnvironmentRepository
from dataall.core.organizations.db.organization_repositories import OrganizationRepository
from dataall.core.permissions.services.tenant_policy_service import TenantPolicyService
from dataall.modules.datasets_base.db.dataset_repositories import DatasetBaseRepository, DatasetListRepository
from dataall.modules.metadata_forms.db.enums import (
    MetadataFormEnforcementScope,
    MetadataFormEnforcementSeverity,
    ENTITY_SCOPE_BY_TYPE,
)
from dataall.core.metadata_manager.metadata_form_entity_manager import (
    MetadataFormEntityTypes,
    MetadataFormEntityManager,
    MetadataFormEntity,
)

from dataall.modules.metadata_forms.db.metadata_form_repository import MetadataFormRepository
from dataall.modules.metadata_forms.services.metadata_form_access_service import MetadataFormAccessService
from dataall.modules.metadata_forms.services.metadata_form_permissions import (
    MANAGE_METADATA_FORMS,
    ENFORCE_METADATA_FORM,
)
from dataall.modules.notifications.db.notification_repositories import NotificationRepository


class MetadataFormEnforcementRequestValidationService:
    @staticmethod
    def validate_create_request(data):
        if 'metadataFormUri' not in data:
            raise exceptions.RequiredParameter('metadataFormUri')

        if 'level' not in data:
            raise exceptions.RequiredParameter('level')

        if 'severity' not in data:
            raise exceptions.RequiredParameter('severity')

        if data.get('level') != MetadataFormEnforcementScope.Global.value:
            if 'homeEntity' not in data:
                raise exceptions.RequiredParameter('homeEntity')

        if 'entityTypes' not in data:
            raise exceptions.RequiredParameter('entityTypes')

        else:
            for entity_type in data.get('entityTypes'):
                if not MetadataFormEntityManager.is_registered(entity_type):
                    raise exceptions.InvalidInput(
                        param_name='entityType',
                        param_value=entity_type,
                        constraint='must be registered in MetadataFormEntityManager',
                    )

        # check that values are valid for the enums
        MetadataFormEnforcementScope(data.get('level'))
        MetadataFormEnforcementSeverity(data.get('severity'))


class MetadataFormEnforcementService:
    @staticmethod
    def _get_entity_uri(session, data):
        return data.get('homeEntity')

    @staticmethod
    @TenantPolicyService.has_tenant_permission(MANAGE_METADATA_FORMS)
    @MetadataFormAccessService.can_perform(ENFORCE_METADATA_FORM)
    def create_mf_enforcement_rule(uri, data):
        MetadataFormEnforcementRequestValidationService.validate_create_request(data)
        MetadataFormAccessService.check_enforcement_access(data.get('homeEntity'), data.get('level'))
        with get_context().db_engine.scoped_session() as session:
            mf = MetadataFormRepository.get_metadata_form(session, uri)
            version = MetadataFormRepository.get_metadata_form_version_number_latest(session, uri)
            rule = MetadataFormRepository.create_mf_enforcement_rule(session, uri, data, version)

            affected_entities = MetadataFormEnforcementService.get_affected_entities(rule.uri, rule=rule)
            for entity in affected_entities:
                if entity['owner']:
                    NotificationRepository.create_notification(
                        session,
                        recipient=entity['owner'],
                        target_uri=f'{entity["uri"]}|{entity["type"]}',
                        message=f'Usage of metadata form "{mf.name}" was enforced for {entity["uri"]} {entity["type"]}',
                        notification_type='METADATA_FORM_ENFORCED',
                    )

        return rule

    @staticmethod
    def get_affected_organizations(uri, rule=None):
        with get_context().db_engine.scoped_session() as session:
            if not rule:
                rule = MetadataFormRepository.get_mf_enforcement_rule_by_uri(session, uri)
            if rule.level == MetadataFormEnforcementScope.Global.value:
                return OrganizationRepository.query_all_active_organizations(session).all()
            if rule.level == MetadataFormEnforcementScope.Organization.value:
                return [OrganizationRepository.get_organization_by_uri(session, rule.homeEntity)]
            return []

    @staticmethod
    def get_affected_environments(uri, rule=None):
        with get_context().db_engine.scoped_session() as session:
            if not rule:
                rule = MetadataFormRepository.get_mf_enforcement_rule_by_uri(session, uri)
            if rule.level == MetadataFormEnforcementScope.Global.value:
                return EnvironmentRepository.query_all_active_environments(session)
            if rule.level == MetadataFormEnforcementScope.Organization.value:
                return EnvironmentRepository.get_all_envs_by_organization(session, rule.homeEntity)
            if rule.level == MetadataFormEnforcementScope.Environment.value:
                return [EnvironmentRepository.get_environment_by_uri(session, rule.homeEntity)]
            return []

    @staticmethod
    def get_affected_datasets(uri, rule=None):
        with get_context().db_engine.scoped_session() as session:
            if not rule:
                rule = MetadataFormRepository.get_mf_enforcement_rule_by_uri(session, uri)
            if rule.level == MetadataFormEnforcementScope.Global.value:
                return DatasetListRepository.query_datasets(session).all()
            if rule.level == MetadataFormEnforcementScope.Organization.value:
                return DatasetListRepository.query_datasets(session, organizationUri=rule.homeEntity).all()
            if rule.level == MetadataFormEnforcementScope.Environment.value:
                return DatasetListRepository.query_datasets(session, environmentUri=rule.homeEntity).all()
            if rule.level == MetadataFormEnforcementScope.Dataset.value:
                return [DatasetBaseRepository.get_dataset_by_uri(session, rule.homeEntity)]
            return []

    @staticmethod
    def get_attachement_for_rule(rule, entityUri):
        with get_context().db_engine.scoped_session() as session:
            return MetadataFormRepository.query_all_attached_metadata_forms_for_entity(
                session,
                entityUri=entityUri,
                metadataFormUri=rule.metadataFormUri,
                version=rule.version,
            ).first()

    @staticmethod
    def form_affected_entity_object(type, entity: MetadataFormEntity, rule):
        return {
            'type': type,
            'name': entity.get_entity_name(),
            'uri': entity.get_uri(),
            'owner': entity.get_owner(),
            'attached': MetadataFormEnforcementService.get_attachement_for_rule(rule, entity.get_uri()),
        }

    @staticmethod
    def get_affected_entities(uri, rule=None):
        affected_entities = []
        with get_context().db_engine.scoped_session() as session:
            if not rule:
                rule = MetadataFormRepository.get_mf_enforcement_rule_by_uri(session, uri)

            orgs = MetadataFormEnforcementService.get_affected_organizations(uri, rule)
            if MetadataFormEntityTypes.Organizations.value in rule.entityTypes:
                affected_entities.extend(
                    [
                        MetadataFormEnforcementService.form_affected_entity_object(
                            MetadataFormEntityTypes.Organizations.value, o, rule
                        )
                        for o in orgs
                    ]
                )

            envs = MetadataFormEnforcementService.get_affected_environments(uri, rule)
            if MetadataFormEntityTypes.Environments.value in rule.entityTypes:
                affected_entities.extend(
                    [
                        MetadataFormEnforcementService.form_affected_entity_object(
                            MetadataFormEntityTypes.Environments.value, e, rule
                        )
                        for e in envs
                    ]
                )

            datasets = []
            if MetadataFormEntityManager.is_registered(
                MetadataFormEntityTypes.S3Datasets.value
            ) or MetadataFormEntityManager.is_registered(MetadataFormEntityTypes.RDDatasets.value):
                datasets = MetadataFormEnforcementService.get_affected_datasets(uri, rule)
                affected_entities.extend(
                    [
                        MetadataFormEnforcementService.form_affected_entity_object(
                            ds.datasetType.value + '-Dataset', ds, rule
                        )
                        for ds in datasets
                        if ds.datasetType.value + '-Dataset' in rule.entityTypes
                        and MetadataFormEntityManager.is_registered(ds.datasetType.value + '-Dataset')
                    ]
                )

            entity_types = set(rule.entityTypes[:]) - {
                MetadataFormEntityTypes.Organizations.value,
                MetadataFormEntityTypes.Environments.value,
                MetadataFormEntityTypes.RDDatasets.value,
                MetadataFormEntityTypes.S3Datasets.value,
            }

            for entity_type in entity_types:
                entity_class = MetadataFormEntityManager.get_resource(entity_type)
                level = ENTITY_SCOPE_BY_TYPE[entity_type]
                all_entities = session.query(entity_class)
                if level == MetadataFormEnforcementScope.Organization:
                    all_entities = all_entities.filter(
                        entity_class.organizationUri.in_([org.organizationUri for org in orgs])
                    )
                if level == MetadataFormEnforcementScope.Environment:
                    all_entities = all_entities.filter(
                        entity_class.environmentUri.in_([env.environmentUri for env in envs])
                    )
                if level == MetadataFormEnforcementScope.Dataset:
                    all_entities = all_entities.filter(entity_class.datasetUri.in_([ds.datasetUri for ds in datasets]))
                all_entities = all_entities.all()
                affected_entities.extend(
                    [
                        MetadataFormEnforcementService.form_affected_entity_object(entity_type, e, rule)
                        for e in all_entities
                    ]
                )
            return affected_entities

    @staticmethod
    def list_mf_enforcement_rules(uri):
        with get_context().db_engine.scoped_session() as session:
            return MetadataFormRepository.list_mf_enforcement_rules(session, uri)

    @staticmethod
    def paginate_mf_affected_entities(uri, data=None):
        data = data or {}
        return paginate_list(
            items=MetadataFormEnforcementService.get_affected_entities(uri),
            page=data.get('page', 1),
            page_size=data.get('pageSize', 10),
        ).to_dict()

    @staticmethod
    def resolve_home_entity(uri, rule=None):
        with get_context().db_engine.scoped_session() as session:
            if not rule:
                rule = MetadataFormRepository.get_mf_enforcement_rule_by_uri(session, uri)
            if rule.level == MetadataFormEnforcementScope.Global.value:
                return ''
            if rule.level == MetadataFormEnforcementScope.Organization.value:
                return OrganizationRepository.get_organization_by_uri(session, rule.homeEntity).label
            if rule.level == MetadataFormEnforcementScope.Environment.value:
                return EnvironmentRepository.get_environment_by_uri(session, rule.homeEntity).label
            if rule.level == MetadataFormEnforcementScope.Dataset.value:
                return DatasetBaseRepository.get_dataset_by_uri(session, rule.homeEntity).label

    @staticmethod
    @TenantPolicyService.has_tenant_permission(MANAGE_METADATA_FORMS)
    @MetadataFormAccessService.can_perform(ENFORCE_METADATA_FORM)
    def delete_mf_enforcement_rule(uri, rule_uri):
        with get_context().db_engine.scoped_session() as session:
            rule = MetadataFormRepository.get_mf_enforcement_rule_by_uri(session, rule_uri)
            session.delete(rule)
            session.commit()
        return True

    @staticmethod
    def list_supported_entity_types():
        supported_entity_types = []
        all_levels_scope = [level for level in MetadataFormEnforcementScope]
        for entity_type in MetadataFormEntityManager.all_registered_keys():
            entity_scope = ENTITY_SCOPE_BY_TYPE[entity_type]
            levels = [level.value for level in all_levels_scope if level > entity_scope or level == entity_scope]
            supported_entity_types.append({'name': entity_type, 'levels': levels})
        return supported_entity_types

    @staticmethod
    def get_rules_that_affect_entity(entity_type, entity_uri):
        if not MetadataFormEntityManager.is_registered(entity_type):
            return []
        all_rules = []
        entity_class = MetadataFormEntityManager.get_resource(entity_type)
        entity_scope = ENTITY_SCOPE_BY_TYPE[entity_type]
        with get_context().db_engine.scoped_session() as session:
            entity = session.query(entity_class).get(entity_uri)
            parent_dataset_uri, parent_env_uri, parent_org_uri = None, None, None

            if entity_scope == MetadataFormEnforcementScope.Dataset:
                parent_dataset_uri = entity.datasetUri
                ds = DatasetBaseRepository.get_dataset_by_uri(session, parent_dataset_uri)
                parent_env_uri = ds.environmentUri
                parent_org_uri = ds.organizationUri
            if entity_scope == MetadataFormEnforcementScope.Environment:
                parent_env_uri = entity.environmentUri
                env = EnvironmentRepository.get_environment_by_uri(session, parent_env_uri)
                parent_org_uri = env.organizationUri
            if entity_scope == MetadataFormEnforcementScope.Organization:
                parent_org_uri = entity.organizationUri

            all_rules.extend(
                MetadataFormRepository.query_all_enforcement_rules(
                    session=session,
                    filter={'entity_types': [entity_type], 'level': MetadataFormEnforcementScope.Global.value},
                )
            )
            if entity_scope < MetadataFormEnforcementScope.Global:
                all_rules.extend(
                    MetadataFormRepository.query_all_enforcement_rules(
                        session=session,
                        filter={
                            'entity_types': [entity_type],
                            'level': MetadataFormEnforcementScope.Organization.value,
                            'home_entity': parent_org_uri,
                        },
                    )
                )

            if entity_scope < MetadataFormEnforcementScope.Organization:
                all_rules.extend(
                    MetadataFormRepository.query_all_enforcement_rules(
                        session=session,
                        filter={
                            'entity_types': [entity_type],
                            'level': MetadataFormEnforcementScope.Environment.value,
                            'home_entity': parent_env_uri,
                        },
                    )
                )
            if entity_scope < MetadataFormEnforcementScope.Environment:
                all_rules.extend(
                    MetadataFormRepository.query_all_enforcement_rules(
                        session=session,
                        filter={
                            'entity_types': [entity_type],
                            'level': MetadataFormEnforcementScope.Dataset.value,
                            'home_entity': parent_dataset_uri,
                        },
                    )
                )

            for r in all_rules:
                attached = MetadataFormEnforcementService.get_attachement_for_rule(r, entity_uri)
                r.attached = attached.uri if attached else None
                r.metadataFormName = MetadataFormRepository.get_metadata_form(session, r.metadataFormUri).name

        return all_rules
