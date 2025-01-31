import { gql } from 'apollo-boost';

export const createMetadataFormEnforcementRule = (input) => ({
  variables: {
    input
  },
  mutation: gql`
    mutation createMetadataFormEnforcementRule(
      $input: NewMetadataFormEnforcementInput!
    ) {
      createMetadataFormEnforcementRule(input: $input) {
        uri
        level
        homeEntity
        homeEntityName
        entityTypes
        metadataFormUri
        version
      }
    }
  `
});
