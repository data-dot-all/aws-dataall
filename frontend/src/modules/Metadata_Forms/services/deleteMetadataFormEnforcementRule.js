import { gql } from 'apollo-boost';

export const deleteMetadataFormEnforcementRule = (uri, rule_uri) => ({
  variables: {
    uri: uri,
    rule_uri: rule_uri
  },
  mutation: gql`
    mutation deleteMetadataFormEnforcementRule(
      $uri: String!
      $rule_uri: String!
    ) {
      deleteMetadataFormEnforcementRule(uri: $uri, rule_uri: $rule_uri)
    }
  `
});
