from sqlalchemy import or_, and_
from sqlalchemy.orm import with_polymorphic

from dataall.modules.metadata_forms.db.enums import MetadataFormVisibility, MetadataFormFieldType
from dataall.modules.metadata_forms.db.metadata_form_models import (
    MetadataForm,
    MetadataFormField,
    AttachedMetadataForm,
    AttachedMetadataFormField,
    StringAttachedMetadataFormField,
    BooleanAttachedMetadataFormField,
    IntegerAttachedMetadataFormField,
    GlossaryTermAttachedMetadataFormField,
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
    def create_attached_metadata_form(session, uri, data=None):
        amf: AttachedMetadataForm = AttachedMetadataForm(
            metadataFormUri=uri, entityUri=data.get('entityUri'), entityType=data.get('entityType')
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
    def query_metadata_forms(session, is_da_admin, groups, env_uris, org_uris, filter):
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

        query = session.query(MetadataForm)

        if not is_da_admin:
            query = query.filter(
                or_(
                    MetadataForm.SamlGroupName.in_(groups),
                    MetadataForm.visibility == MetadataFormVisibility.Global.value,
                    and_(
                        MetadataForm.visibility == MetadataFormVisibility.Team.value,
                        MetadataForm.homeEntity.in_(groups),
                    ),
                    and_(
                        MetadataForm.visibility == MetadataFormVisibility.Organization.value,
                        MetadataForm.homeEntity.in_(org_uris),
                    ),
                    and_(
                        MetadataForm.visibility == MetadataFormVisibility.Environment.value,
                        MetadataForm.homeEntity.in_(env_uris),
                    ),
                )
            )

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

        if filter and filter.get('search_input'):
            query = query.filter(
                or_(
                    MetadataForm.name.ilike('%' + filter.get('search_input') + '%'),
                    MetadataForm.description.ilike('%' + filter.get('search_input') + '%'),
                )
            )

        return query.order_by(MetadataForm.name)

    @staticmethod
    def get_metadata_form_fields(session, form_uri):
        return (
            session.query(MetadataFormField)
            .filter(MetadataFormField.metadataFormUri == form_uri)
            .order_by(MetadataFormField.displayNumber)
            .all()
        )

    @staticmethod
    def create_metadata_form_field(session, uri, data):
        field: MetadataFormField = MetadataFormField(
            metadataFormUri=uri,
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
    def query_attached_metadata_forms(session, filter):
        query = session.query(AttachedMetadataForm)
        if filter and filter.get('entityType'):
            query = query.filter(AttachedMetadataForm.entityType == filter.get('entityType'))
        if filter and filter.get('entityUri'):
            query = query.filter(AttachedMetadataForm.entityUri == filter.get('entityUri'))
        if filter and filter.get('metadataFormUri'):
            query = query.filter(AttachedMetadataForm.metadataFormUri == filter.get('metadataFormUri'))
        return query
