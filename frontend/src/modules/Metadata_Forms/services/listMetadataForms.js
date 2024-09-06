import { gql } from 'apollo-boost';

export const listUserMetadataForms = (filter) => ({
  variables: {
    filter
  },
  query: gql`
    query listUserMetadataForms($filter: MetadataFormFilter) {
      listUserMetadataForms(filter: $filter) {
        hasTenantPermissions
        count
        page
        pages
        hasNext
        hasPrevious
        nodes {
          uri
          name
          description
          SamlGroupName
          userRole
          visibility
          homeEntity
          homeEntityName
        }
      }
    }
  `
});


export const listEntityMetadataForms = (filter) => ({
  variables: {
    filter
  },
  query: gql`
    query listEntityMetadataForms($filter: MetadataFormFilter) {
      listEntityMetadataForms(filter: $filter) {
        hasTenantPermissions
        count
        page
        pages
        hasNext
        hasPrevious
        nodes {
          uri
          name
          description
          SamlGroupName
          userRole
          visibility
          homeEntity
          homeEntityName
        }
      }
    }
  `
});
