import { gql } from 'apollo-boost';

export const listEntityTypesWithScope = () => ({
  variables: {},
  query: gql`
    query listEntityTypesWithScope {
      listEntityTypesWithScope {
        name
        levels
      }
    }
  `
});
