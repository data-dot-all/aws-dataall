import { gql } from 'apollo-boost';

export const BatchUpdateDatasetTableColumn = (columns) => ({
  variables: {
    columns
  },
  mutation: gql`
    mutation BatchUpdateDatasetTableColumn(
      $columns: [SubitemDescriptionInput]
    ) {
      batchUpdateDatasetTableColumn(columns: $columns)
    }
  `
});
