import { gql } from 'apollo-boost';

export const generateMetadataBedrock = ({
  resourceUri,
  targetType,
  metadataTypes,
  tableSampleData
}) => ({
  variables: {
    resourceUri,
    targetType,
    metadataTypes,
    tableSampleData
  },
  mutation: gql`
    mutation generateMetadata(
      $resourceUri: String!
      $targetType: MetadataGenerationTargets!
      $metadataTypes: [String]!
      $tableSampleData: TableSampleData
    ) {
      generateMetadata(
        resourceUri: $resourceUri
        targetType: $targetType
        metadataTypes: $metadataTypes
        tableSampleData: $tableSampleData
      ) {
        targetUri
        targetType
        label
        description
        tags
        topics
      }
    }
  `
});
