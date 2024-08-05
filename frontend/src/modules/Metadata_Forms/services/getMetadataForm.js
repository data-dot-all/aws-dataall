import { gql } from 'apollo-boost';

export const getMetadataForm = (uri) => ({
  variables: {
    uri
  },
  query: gql`
    query getMetadataForm($uri: String!) {
      getMetadataForm(uri: $uri) {
        uri
        name
        description
        SamlGroupName
        visibility
        homeEntity
        homeEntityName
        fields {
          uri
          metadataFormUri
          name
          description
          required
          type
          glossaryNodeUri
          possibleValues
        }
      }
    }
  `
});
