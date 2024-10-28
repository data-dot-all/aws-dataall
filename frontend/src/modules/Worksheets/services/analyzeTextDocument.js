import { gql } from 'apollo-boost';

export const analyzeTextDocument = ({
  prompt,
  environmentUri,
  worksheetUri,
  datasetUri,
  key
}) => ({
  variables: {
    prompt,
    environmentUri,
    worksheetUri,
    datasetUri,
    key
  },
  query: gql`
    query analyzeTextDocument(
      $prompt: String!
      $environmentUri: String!
      $worksheetUri: String!
      $datasetUri: String!
      $key: String!
    ) {
      analyzeTextDocument(
        prompt: $prompt
        environmentUri: $environmentUri
        worksheetUri: $worksheetUri
        datasetUri: $datasetUri
        key: $key
      )
    }
  `
});
