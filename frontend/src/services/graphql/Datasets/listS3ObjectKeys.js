import { gql } from 'apollo-boost';

export const listS3ObjectKeys = ({ datasetUri }) => ({
  variables: {
    datasetUri
  },
  query: gql`
    query listS3ObjectKeys($datasetUri: String!) {
      listS3ObjectKeys(datasetUri: $datasetUri)
    }
  `
});
