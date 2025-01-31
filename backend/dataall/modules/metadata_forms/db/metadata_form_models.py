from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, ForeignKeyConstraint, PrimaryKeyConstraint, Enum
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship, validates

from dataall.base.db import Base, utils

from dataall.modules.metadata_forms.db.enums import MetadataFormFieldType


class MetadataForm(Base):
    __tablename__ = 'metadata_form'
    uri = Column(String, primary_key=True, default=utils.uuid('metadata_form'))
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    SamlGroupName = Column(String, nullable=False)
    visibility = Column(String, nullable=False)  # enum MetadataFormVisibility
    homeEntity = Column(String, nullable=True)


class MetadataFormVersion(Base):
    __tablename__ = 'metadata_form_version'
    metadataFormUri = Column(String, ForeignKey('metadata_form.uri'), nullable=False)
    version = Column(Integer, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint('metadataFormUri', 'version'),
        ForeignKeyConstraint(
            ('metadataFormUri',), ('metadata_form.uri',), name='f_key_version_metadata', ondelete='CASCADE'
        ),
    )


class MetadataFormEnforcementRule(Base):
    __tablename__ = 'metadata_form_enforcement_rule'
    uri = Column(String, primary_key=True, default=utils.uuid('rule'))
    metadataFormUri = Column(String, ForeignKey('metadata_form.uri'), nullable=False)
    version = Column(Integer, nullable=False)
    level = Column(String, nullable=False)  # enum MetadataFormEnforcementScope
    homeEntity = Column(String, nullable=True)
    entityTypes = Column(ARRAY(String), nullable=False)  # enum MetadataFormEntityTypes
    severity = Column(String, nullable=False)  # enum MetadataFormEnforcementSeverity

    __table_args__ = (
        ForeignKeyConstraint(
            ['metadataFormUri', 'version'],
            ['metadata_form_version.metadataFormUri', 'metadata_form_version.version'],
            name='f_key_enforcement_version_metadata',
            ondelete='CASCADE',
        ),
    )


class MetadataFormField(Base):
    __tablename__ = 'metadata_form_field'
    metadataFormUri = Column(String)
    version = Column(Integer, nullable=False)
    uri = Column(String, primary_key=True, default=utils.uuid('field'))
    displayNumber = Column(Integer, nullable=False)
    description = Column(String, nullable=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # enum MetadataFormFieldType
    required = Column(Boolean, nullable=False)
    glossaryNodeUri = Column(String, ForeignKey('glossary_node.nodeUri'), nullable=True)
    possibleValues = Column(ARRAY(String), nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ['metadataFormUri', 'version'],
            ['metadata_form_version.metadataFormUri', 'metadata_form_version.version'],
            name='fk_version',
            ondelete='CASCADE',
        ),
    )


class AttachedMetadataForm(Base):
    __tablename__ = 'attached_metadata_form'
    metadataFormUri = Column(String, nullable=False)
    version = Column(Integer, nullable=False)
    uri = Column(String, primary_key=True, default=utils.uuid('attached_form'))
    entityUri = Column(String, nullable=False)
    entityType = Column(String, nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ['metadataFormUri', 'version'],
            ['metadata_form_version.metadataFormUri', 'metadata_form_version.version'],
            name='fk_attached_mf_version_uri',
            ondelete='CASCADE',
        ),
    )


class AttachedMetadataFormField(Base):
    __tablename__ = 'attached_metadata_form_field'
    attachedFormUri = Column(String, primary_key=True)
    fieldUri = Column(String, primary_key=True)
    type = Column(Enum(MetadataFormFieldType), nullable=False, default=MetadataFormFieldType.String)

    __table_args__ = (
        PrimaryKeyConstraint('attachedFormUri', 'fieldUri'),
        ForeignKeyConstraint(
            ('attachedFormUri',),
            ('attached_metadata_form.uri',),
            name='fk_attached_field_mf_uri',
            ondelete='CASCADE',
        ),
        ForeignKeyConstraint(
            ('fieldUri',), ('metadata_form_field.uri',), name='fk_attached_field_uri', ondelete='CASCADE'
        ),
    )
    __mapper_args__ = {'polymorphic_identity': 'attached_metadata_form_field', 'polymorphic_on': 'type'}

    @property
    def value(self):
        raise NotImplementedError('Basic AttachedMetadataFormField has no implemented property value')


class StringAttachedMetadataFormField(AttachedMetadataFormField):
    __tablename__ = 'string_attached_metadata_form_field'
    attachedFormUri = Column(String, primary_key=True)
    fieldUri = Column(String, primary_key=True)
    value = Column(String, nullable=True)
    __mapper_args__ = {'polymorphic_identity': MetadataFormFieldType.String}

    __table_args__ = (
        ForeignKeyConstraint(
            ['attachedFormUri', 'fieldUri'],
            ['attached_metadata_form_field.attachedFormUri', 'attached_metadata_form_field.fieldUri'],
            name='fk_s_field',
            ondelete='CASCADE',
        ),
    )


class BooleanAttachedMetadataFormField(AttachedMetadataFormField):
    __tablename__ = 'boolean_attached_metadata_form_field'
    attachedFormUri = Column(String, primary_key=True)
    fieldUri = Column(String, primary_key=True)
    value = Column(Boolean, nullable=True)
    __mapper_args__ = {'polymorphic_identity': MetadataFormFieldType.Boolean}

    __table_args__ = (
        ForeignKeyConstraint(
            ['attachedFormUri', 'fieldUri'],
            ['attached_metadata_form_field.attachedFormUri', 'attached_metadata_form_field.fieldUri'],
            name='fk_b_field',
            ondelete='CASCADE',
        ),
    )


class IntegerAttachedMetadataFormField(AttachedMetadataFormField):
    __tablename__ = 'integer_attached_metadata_form_field'
    attachedFormUri = Column(String, primary_key=True)
    fieldUri = Column(String, primary_key=True)
    value = Column(Integer, nullable=True)
    __mapper_args__ = {'polymorphic_identity': MetadataFormFieldType.Integer}

    __table_args__ = (
        ForeignKeyConstraint(
            ['attachedFormUri', 'fieldUri'],
            ['attached_metadata_form_field.attachedFormUri', 'attached_metadata_form_field.fieldUri'],
            name='fk_i_field',
            ondelete='CASCADE',
        ),
    )


class GlossaryTermAttachedMetadataFormField(AttachedMetadataFormField):
    __tablename__ = 'glossary_term_attached_metadata_form_field'
    attachedFormUri = Column(String, primary_key=True)
    fieldUri = Column(String, primary_key=True)
    value = Column(String, nullable=True)
    __mapper_args__ = {'polymorphic_identity': MetadataFormFieldType.GlossaryTerm}

    __table_args__ = (
        ForeignKeyConstraint(
            ['attachedFormUri', 'fieldUri'],
            ['attached_metadata_form_field.attachedFormUri', 'attached_metadata_form_field.fieldUri'],
            name='fk_gt_field',
            ondelete='CASCADE',
        ),
    )
