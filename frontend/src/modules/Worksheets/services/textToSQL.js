import { gql } from 'apollo-boost';

export const textToSQL = ({
  prompt,
  environmentUri,
  worksheetUri,
  databaseName,
  tableNames
}) => ({
  variables: {
    prompt,
    environmentUri,
    worksheetUri,
    databaseName,
    tableNames
  },
  query: gql`
    query textToSQL(
      $prompt: String!
      $environmentUri: String!
      $worksheetUri: String!
      $databaseName: String!
      $tableNames: [String]
    ) {
      textToSQL(
        prompt: $prompt
        environmentUri: $environmentUri
        worksheetUri: $worksheetUri
        databaseName: $databaseName
        tableNames: $tableNames
      )
    }
  `
});
