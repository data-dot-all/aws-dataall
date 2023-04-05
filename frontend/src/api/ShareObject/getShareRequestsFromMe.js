import { gql } from 'apollo-boost';

export const getShareRequestsFromMe = ({ filter }) => ({
  variables: { filter },
  query: gql`
    query getShareRequestsFromMe($filter: ShareObjectFilter) {
      getShareRequestsFromMe(filter: $filter) {
        count
        page
        pages
        hasNext
        hasPrevious
        nodes {
          owner
          created
          deleted
          shareUri
          status
          userRoleForShareObject
          principal {
            principalId
            principalType
            principalName
            principalIAMRoleName
            SamlGroupName
            environmentUri
            environmentName
            AwsAccountId
            region
            organizationUri
            organizationName
          }
          statistics {
            sharedItems
            revokedItems
            failedItems
            pendingItems
          }
          dataset {
            datasetUri
            datasetName
            SamlAdminGroupName
            environmentName
            exists
          }
        }
      }
    }
  `
});
