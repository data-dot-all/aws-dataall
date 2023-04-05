import { gql } from 'apollo-boost';

export const previewTable = ({ tableUri, queryExecutionId }) => ({
  variables: {
    tableUri,
    queryExecutionId
  },
  query: gql`
    query PreviewTable($tableUri: String!, $queryExecutionId: String) {
      previewTable(tableUri: $tableUri, queryExecutionId: $queryExecutionId) {
        count
        status
        queryExecutionId
        nodes {
          data
        }
      }
    }
  `
});
