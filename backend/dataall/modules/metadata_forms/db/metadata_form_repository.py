from sqlalchemy import or_, and_
from sqlalchemy.orm import with_polymorphic
from sqlalchemy import func

from dataall.modules.metadata_forms.db.enums import (
    MetadataFormVisibility,
    MetadataFormFieldType,
    MetadataFormEnforcementSeverity,
)
from dataall.modules.metadata_forms.db.metadata_form_models import (
    MetadataForm,
    MetadataFormField,
    AttachedMetadataForm,
    AttachedMetadataFormField,
    StringAttachedMetadataFormField,
    BooleanAttachedMetadataFormField,
    IntegerAttachedMetadataFormField,
    GlossaryTermAttachedMetadataFormField,
    MetadataFormVersion,
    MetadataFormEnforcementRule,
)

import json

all_fields = with_polymorphic(
    AttachedMetadataFormField,
    [
        StringAttachedMetadataFormField,
        BooleanAttachedMetadataFormField,
        IntegerAttachedMetadataFormField,
        GlossaryTermAttachedMetadataFormField,
    ],
)


class MetadataFormRepository:
    @staticmethod
    def create_metadata_form(session, data=None):
        mf: MetadataForm = MetadataForm(
            name=data.get('name'),
            description=data.get('description'),
            SamlGroupName=data.get('SamlGroupName'),
            visibility=data.get('visibility'),
            homeEntity=data.get('homeEntity'),
        )
        session.add(mf)
        session.commit()
        return mf

    @staticmethod
    def create_metadata_form_version(session, metadataFormUri, version_num):
        version = MetadataFormVersion(metadataFormUri=metadataFormUri, version=version_num)
        session.add(version)
        session.commit()
        return version

    @staticmethod
    def create_metadata_form_version_next(session, metadataFormUri):
        version_num = MetadataFormRepository.get_metadata_form_version_number_latest(session, metadataFormUri)
        version = MetadataFormVersion(metadataFormUri=metadataFormUri, version=version_num + 1)
        session.add(version)
        session.commit()
        return version

    @staticmethod
    def get_metadata_form_version_number_latest(session, metadataFormUri):
        return (
            session.query(func.max(MetadataFormVersion.version))
            .filter(MetadataFormVersion.metadataFormUri == metadataFormUri)
            .scalar()
        )

    @staticmethod
    def get_metadata_form_version_latest(session, metadataFormUri):
        version_num = MetadataFormRepository.get_metadata_form_version_number_latest(session, metadataFormUri)
        return session.query(MetadataFormVersion).get((metadataFormUri, version_num))

    @staticmethod
    def get_metadata_form_version(session, metadataFormUri, version_num):
        return session.query(MetadataFormVersion).get((metadataFormUri, version_num))

    @staticmethod
    def create_attached_metadata_form(session, uri, data=None):
        version_num = MetadataFormRepository.get_metadata_form_version_number_latest(session, uri)
        amf: AttachedMetadataForm = AttachedMetadataForm(
            metadataFormUri=uri, version=version_num, entityUri=data.get('entityUri'), entityType=data.get('entityType')
        )
        session.add(amf)
        session.commit()
        return amf

    @staticmethod
    def get_metadata_form(session, uri):
        return session.query(MetadataForm).get(uri)

    @staticmethod
    def get_attached_metadata_form(session, uri):
        return session.query(AttachedMetadataForm).get(uri)

    @staticmethod
    def query_user_metadata_forms(session, is_da_admin, groups, env_uris, org_uris, filter):
        """
        Returns a list of metadata forms based on the user's permissions and any provided filters.
        DataAll admins can see allll forms, while non-admins can only see forms they have access to based on their group memberships.
        :param session:
        :param is_da_admin: is user dataall admin
        :param groups: user's group memberships
        :param env_uris: user's environment URIs
        :param org_uris: user's organization URIs
        :param filter:
        """

        env_uris = env_uris or []
        org_uris = org_uris or []

        query = session.query(MetadataForm)

        if not is_da_admin:
            query = query.filter(
                or_(
                    MetadataForm.SamlGroupName.in_(groups),  # user is in owner-group
                    MetadataForm.visibility == MetadataFormVisibility.Global.value,  # MF is visible for everyone
                    and_(  # MF is visible for Organization, that user is in
                        MetadataForm.visibility == MetadataFormVisibility.Organization.value,
                        MetadataForm.homeEntity.in_(org_uris),
                    ),
                    and_(  # MF is visible for Environment, that user is in
                        MetadataForm.visibility == MetadataFormVisibility.Environment.value,
                        MetadataForm.homeEntity.in_(env_uris),
                    ),
                    and_(  # MF is visible for Team, that user is in
                        MetadataForm.visibility == MetadataFormVisibility.Team.value,
                        MetadataForm.homeEntity.in_(groups),
                    ),
                )
            )

        query = MetadataFormRepository.filter_query(query, filter)
        return query.order_by(MetadataForm.name)

    @staticmethod
    def exclude_attached(session, query, filter):
        if filter and filter.get('hideAttached') and filter.get('entityType') and filter.get('entityUri'):
            query = query.filter(
                ~MetadataForm.uri.in_(
                    session.query(AttachedMetadataForm.metadataFormUri)
                    .filter(
                        AttachedMetadataForm.entityUri == filter.get('entityUri'),
                        AttachedMetadataForm.entityType == filter.get('entityType'),
                    )
                    .subquery()
                )
            )
        return query

    @staticmethod
    def filter_query(query, filter):
        if filter and filter.get('search_input'):
            query = query.filter(
                or_(
                    MetadataForm.name.ilike('%' + filter.get('search_input') + '%'),
                    MetadataForm.description.ilike('%' + filter.get('search_input') + '%'),
                )
            )
        return query

    @staticmethod
    def query_entity_metadata_forms(
        session, is_da_admin, groups, user_org_uris, user_env_uris, entity_orgs_uris, entity_envs_uris, filter
    ):
        """
        Returns a list of metadata forms that user can attach to entity based on the user's permissions and any provided filters.
        DataAll admins can see allll forms, while non-admins can only see forms they have access to based on their group memberships.
        :param session:
        :param is_da_admin: is user dataall admin
        :param groups: user's group memberships
        :param user_env_uris: user's environment URIs
        :param user_org_uris: user's organization URIs
        :param entity_orgs_uris: organizations, related to entity
        :param entity_envs_uris: environments, related to entity
        :param filter:
        """

        entity_orgs_uris = entity_orgs_uris or []
        entity_envs_uris = entity_envs_uris or []

        query = MetadataFormRepository.query_user_metadata_forms(
            session, is_da_admin, groups, user_env_uris, user_org_uris, filter
        )

        query = query.filter(
            and_(
                or_(
                    MetadataForm.visibility != MetadataFormVisibility.Organization.value,
                    MetadataForm.homeEntity.in_(entity_orgs_uris),
                ),
                or_(
                    MetadataForm.visibility != MetadataFormVisibility.Environment.value,
                    MetadataForm.homeEntity.in_(entity_envs_uris),
                ),
            )
        )

        query = MetadataFormRepository.exclude_attached(session, query, filter)
        return query.order_by(MetadataForm.name)

    @staticmethod
    def get_metadata_form_fields(session, form_uri, version=None):
        version = version or MetadataFormRepository.get_metadata_form_version_number_latest(session, form_uri)
        return (
            session.query(MetadataFormField)
            .filter(MetadataFormField.metadataFormUri == form_uri)
            .filter(MetadataFormField.version == version)
            .order_by(MetadataFormField.displayNumber)
            .all()
        )

    @staticmethod
    def create_metadata_form_field(session, uri, data, version_num=None):
        version_num = version_num or MetadataFormRepository.get_metadata_form_version_number_latest(session, uri)
        field: MetadataFormField = MetadataFormField(
            metadataFormUri=uri,
            version=version_num,
            name=data.get('name'),
            description=data.get('description'),
            type=data.get('type'),
            required=data.get('required', False),
            glossaryNodeUri=data.get('glossaryNodeUri', None),
            possibleValues=data.get('possibleValues', None),
            displayNumber=data.get('displayNumber'),
        )
        session.add(field)
        session.commit()
        return field

    @staticmethod
    def get_metadata_form_field_by_uri(session, uri):
        return session.query(MetadataFormField).get(uri)

    @staticmethod
    def update_metadata_form_field(session, fieldUri, data):
        mf = MetadataFormRepository.get_metadata_form_field_by_uri(session, fieldUri)
        mf.name = data.get('name', mf.name)
        mf.description = data.get('description', mf.description)
        mf.type = data.get('type', mf.type)
        mf.glossaryNodeUri = data.get('glossaryNodeUri', mf.glossaryNodeUri)
        mf.required = data.get('required', mf.required)
        mf.possibleValues = data.get('possibleValues', mf.possibleValues)
        mf.displayNumber = data.get('displayNumber', mf.displayNumber)
        session.commit()
        return mf

    @staticmethod
    def get_metadata_form_owner(session, uri):
        return session.query(MetadataForm).get(uri).SamlGroupName

    @staticmethod
    def create_attached_metadata_form_field(session, attachedFormUri, field: MetadataFormField, value):
        amff = None
        value = json.loads(value)
        if field.type == MetadataFormFieldType.String.value:
            amff = StringAttachedMetadataFormField(attachedFormUri=attachedFormUri, fieldUri=field.uri, value=value)
        elif field.type == MetadataFormFieldType.Boolean.value:
            amff = BooleanAttachedMetadataFormField(attachedFormUri=attachedFormUri, fieldUri=field.uri, value=value)

        elif field.type == MetadataFormFieldType.Integer.value:
            value = int(value) if value else None
            amff = IntegerAttachedMetadataFormField(attachedFormUri=attachedFormUri, fieldUri=field.uri, value=value)
        elif field.type == MetadataFormFieldType.GlossaryTerm.value:
            amff = GlossaryTermAttachedMetadataFormField(
                attachedFormUri=attachedFormUri, fieldUri=field.uri, value=value
            )
        else:
            raise Exception('Unsupported field type')

        if amff is not None:
            session.add(amff)
            session.commit()

    @staticmethod
    def get_attached_metadata_form_field(session, field_uri):
        return session.query(all_fields).get(field_uri)

    @staticmethod
    def get_all_attached_metadata_form_fields(session, uri):
        return session.query(all_fields).filter(AttachedMetadataFormField.attachedFormUri == uri).all()

    @staticmethod
    def query_attached_metadata_forms(session, is_da_admin, groups, user_envs_uris, user_orgs_uris, filter):
        all_mfs = MetadataFormRepository.query_user_metadata_forms(
            session, is_da_admin, groups, user_envs_uris, user_orgs_uris, filter
        ).subquery()
        # The c confuses a lot of people, SQLAlchemy uses this unfortunately odd name
        # as a container for columns in table objects.
        query = session.query(AttachedMetadataForm).join(all_mfs, AttachedMetadataForm.metadataFormUri == all_mfs.c.uri)
        if filter:
            if filter.get('entityType'):
                query = query.filter(AttachedMetadataForm.entityType == filter.get('entityType'))
            if filter.get('entityUri'):
                query = query.filter(AttachedMetadataForm.entityUri == filter.get('entityUri'))
            if filter.get('metadataFormUri'):
                query = query.filter(AttachedMetadataForm.metadataFormUri == filter.get('metadataFormUri'))
            if filter.get('version'):
                query = query.filter(AttachedMetadataForm.version == filter.get('version'))
        return query.order_by(all_mfs.c.name)

    @staticmethod
    def query_all_attached_metadata_forms_for_entity(
        session, entityUri, entityType=None, metadataFormUri=None, version=None
    ):
        amfs = session.query(AttachedMetadataForm).filter(AttachedMetadataForm.entityUri == entityUri)
        if entityType:
            amfs = amfs.filter(AttachedMetadataForm.entityType == entityType)
        if metadataFormUri:
            amfs = amfs.filter(AttachedMetadataForm.metadataFormUri == metadataFormUri)
        if version:
            amfs = amfs.filter(AttachedMetadataForm.version == version)
        return amfs

    @staticmethod
    def get_metadata_form_versions_numbers(session, uri):
        versions = (
            session.query(MetadataFormVersion)
            .filter(MetadataFormVersion.metadataFormUri == uri)
            .order_by(MetadataFormVersion.version.desc())
            .all()
        )
        return [v.version for v in versions]

    @staticmethod
    def get_metadata_form_versions(session, uri):
        versions = (
            session.query(MetadataFormVersion)
            .filter(MetadataFormVersion.metadataFormUri == uri)
            .order_by(MetadataFormVersion.version.desc())
            .all()
        )
        return versions

    @staticmethod
    def get_all_attached_metadata_forms(session, mf_uri, version=None):
        all_attached = session.query(AttachedMetadataForm).filter(AttachedMetadataForm.metadataFormUri == mf_uri)
        if version:
            all_attached = all_attached.filter(AttachedMetadataForm.version == version)
        return all_attached.all()

    @staticmethod
    def create_mf_enforcement_rule(session, uri, data, version):
        rule = MetadataFormEnforcementRule(
            metadataFormUri=uri,
            version=version,
            level=data.get('level'),
            homeEntity=data.get('homeEntity'),
            entityTypes=data.get('entityTypes'),
            severity=data.get('severity', MetadataFormEnforcementSeverity.Recommended.value),
        )
        session.add(rule)
        session.commit()
        return rule

    @staticmethod
    def get_mf_enforcement_rule_by_uri(session, uri):
        return session.query(MetadataFormEnforcementRule).get(uri)

    @staticmethod
    def list_mf_enforcement_rules(session, uri):
        return (
            session.query(MetadataFormEnforcementRule).filter(MetadataFormEnforcementRule.metadataFormUri == uri).all()
        )

    @staticmethod
    def query_all_enforcement_rules(session, filter):
        all_rules = session.query(MetadataFormEnforcementRule)
        if filter:
            if filter.get('entity_types'):
                for etype in filter.get('entity_types'):
                    all_rules = all_rules.filter(MetadataFormEnforcementRule.entityTypes.any(etype))
            if filter.get('level'):
                all_rules = all_rules.filter(MetadataFormEnforcementRule.level == filter.get('level'))
            if filter.get('home_entity'):
                all_rules = all_rules.filter(MetadataFormEnforcementRule.homeEntity == filter.get('home_entity'))

        return all_rules.all()

    @staticmethod
    def update_version_in_rules(session, uri, version):
        all_rules = (
            session.query(MetadataFormEnforcementRule).filter(MetadataFormEnforcementRule.metadataFormUri == uri).all()
        )
        for r in all_rules:
            r.version = version
        session.commit()
