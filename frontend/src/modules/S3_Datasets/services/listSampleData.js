import { gql } from 'apollo-boost';

export const listSampleData = ({ tableUri }) => ({
  variables: {
    tableUri
  },
  query: gql`
    query listSampleData($tableUri: String!) {
      listSampleData(tableUri: $tableUri) {
        fields
        rows
      }
    }
  `
});
