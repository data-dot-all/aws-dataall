import { gql } from 'apollo-boost';

export const listAllEnvironmentConsumptionRoles = ({
  filter,
  environmentUri
}) => ({
  variables: {
    environmentUri,
    filter
  },
  query: gql`
    query listAllEnvironmentConsumptionRoles(
      $filter: ConsumptionRoleFilter
      $environmentUri: String!
    ) {
      listAllEnvironmentConsumptionRoles(
        environmentUri: $environmentUri
        filter: $filter
      ) {
        count
        page
        pages
        hasNext
        hasPrevious
        nodes {
          consumptionRoleUri
          consumptionRoleName
          environmentUri
          groupUri
          IAMRoleArn
          dataallManaged
        }
      }
    }
  `
});
