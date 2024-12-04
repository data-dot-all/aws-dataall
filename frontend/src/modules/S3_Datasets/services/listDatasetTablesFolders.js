import { gql } from 'apollo-boost';

export const listDatasetTablesFolders = ({ datasetUri, filter }) => ({
  variables: {
    datasetUri,
    filter
  },
  query: gql`
    query listDatasetTablesFolders(
      $datasetUri: String!
      $filter: DatasetFilter
    ) {
      listDatasetTablesFolders(datasetUri: $datasetUri, filter: $filter) {
        count
        page
        pages
        hasNext
        hasPrevious
        nodes {
          name
          targetType
          targetUri
        }
      }
    }
  `
});
