import { gql } from 'apollo-boost';

export const listRulesThatAffectEntity = (uri, type) => ({
  variables: {
    entityUri: uri,
    entityType: type
  },
  query: gql`
    query listRulesThatAffectEntity($entityUri: String!, $entityType: String!) {
      listRulesThatAffectEntity(
        entityUri: $entityUri
        entityType: $entityType
      ) {
        uri
        level
        homeEntity
        homeEntityName
        entityTypes
        metadataFormUri
        metadataFormName
        version
        severity
        attached
      }
    }
  `
});
