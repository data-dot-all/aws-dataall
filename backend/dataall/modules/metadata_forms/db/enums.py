from dataall.base.api.constants import GraphQLEnumMapper
from dataall.core.metadata_manager.metadata_form_entity_manager import MetadataFormEntityTypes


class MetadataFormVisibility(GraphQLEnumMapper):
    Team = 'Team Only'
    Environment = 'Environment-Wide'
    Organization = 'Organization-Wide'
    Global = 'Global'


class MetadataFormFieldType(GraphQLEnumMapper):
    String = 'String'
    Integer = 'Integer'
    Boolean = 'Boolean'
    GlossaryTerm = 'Glossary Term'


class MetadataFormEnforcementSeverity(GraphQLEnumMapper):
    Mandatory = 'Mandatory'
    Recommended = 'Recommended'


class MetadataFormEnforcementScope(GraphQLEnumMapper):
    Dataset = 'Dataset Level'
    Environment = 'Environmental Level'
    Organization = 'Organizational Level'
    Global = 'Global'

    @classmethod
    def _ordering(cls):
        return ['Global', 'Organization', 'Environment', 'Dataset']

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.__class__._ordering().index(self._name_) > self.__class__._ordering().index(other._name_)
        return NotImplemented

    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self.__class__._ordering().index(self._name_) < self.__class__._ordering().index(other._name_)
        return NotImplemented


class MetadataFormUserRoles(GraphQLEnumMapper):
    Owner = 'Owner'
    User = 'User'


ENTITY_SCOPE_BY_TYPE = {
    MetadataFormEntityTypes.Organizations.value: MetadataFormEnforcementScope.Global,
    MetadataFormEntityTypes.OrganizationTeams.value: MetadataFormEnforcementScope.Organization,
    MetadataFormEntityTypes.Environments.value: MetadataFormEnforcementScope.Organization,
    MetadataFormEntityTypes.EnvironmentTeams.value: MetadataFormEnforcementScope.Environment,
    MetadataFormEntityTypes.S3Datasets.value: MetadataFormEnforcementScope.Environment,
    MetadataFormEntityTypes.RDDatasets.value: MetadataFormEnforcementScope.Environment,
    MetadataFormEntityTypes.Worksheets.value: MetadataFormEnforcementScope.Global,
    MetadataFormEntityTypes.Dashboards.value: MetadataFormEnforcementScope.Environment,
    MetadataFormEntityTypes.ConsumptionRoles.value: MetadataFormEnforcementScope.Environment,
    MetadataFormEntityTypes.Notebooks.value: MetadataFormEnforcementScope.Environment,
    MetadataFormEntityTypes.MLStudioEntities.value: MetadataFormEnforcementScope.Environment,
    MetadataFormEntityTypes.Pipelines.value: MetadataFormEnforcementScope.Environment,
    MetadataFormEntityTypes.Tables.value: MetadataFormEnforcementScope.Dataset,
    MetadataFormEntityTypes.Folder.value: MetadataFormEnforcementScope.Dataset,
    MetadataFormEntityTypes.Bucket.value: MetadataFormEnforcementScope.Dataset,
    MetadataFormEntityTypes.Share.value: MetadataFormEnforcementScope.Dataset,
}
