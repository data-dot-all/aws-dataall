import { gql } from 'apollo-boost';

export const disableRedshiftClusterDatasetCopy = ({
  clusterUri,
  datasetUri,
  tableUri
}) => ({
  variables: { clusterUri, datasetUri, tableUri },
  mutation: gql`
    mutation disableRedshiftClusterDatasetTableCopy(
      $clusterUri: String
      $datasetUri: String
      $tableUri: String
    ) {
      disableRedshiftClusterDatasetTableCopy(
        clusterUri: $clusterUri
        datasetUri: $datasetUri
        tableUri: $tableUri
      )
    }
  `
});
