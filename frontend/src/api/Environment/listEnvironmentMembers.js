import { gql } from 'apollo-boost';

export const listEnvironmentMembers = ({ term, environmentUri }) => ({
  variables: {
    environmentUri,
    filter: { term: term || '' }
  },
  query: gql`
    query getEnvironment(
      $filter: OrganizationUserFilter
      $environmentUri: String
    ) {
      getEnvironment(environmentUri: $environmentUri) {
        environmentUri
        userRoleInEnvironment
        users(filter: $filter) {
          count
          nodes {
            userName
            userRoleInEnvironment
            created
          }
        }
      }
    }
  `
});
