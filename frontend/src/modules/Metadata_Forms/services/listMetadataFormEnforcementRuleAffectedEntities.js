import { gql } from 'apollo-boost';

export const listEntityAffectedByEnforcementRules = (uri, filter) => ({
  variables: {
    uri,
    filter
  },
  query: gql`
    query listEntityAffectedByEnforcementRules(
      $uri: String!
      $filter: AffectedEntityFilter
    ) {
      listEntityAffectedByEnforcementRules(uri: $uri, filter: $filter) {
        count
        page
        pages
        hasNext
        hasPrevious
        nodes {
          uri
          type
          name
          owner
          attached {
            uri
          }
        }
      }
    }
  `
});
