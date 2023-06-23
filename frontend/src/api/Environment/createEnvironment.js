import { gql } from 'apollo-boost';

const createEnvironment = (input) => ({
  variables: {
    input
  },
  mutation: gql`
    mutation CreateEnvironment($input: NewEnvironmentInput) {
      createEnvironment(input: $input) {
        environmentUri
        label
        userRoleInEnvironment
        SamlGroupName
        AwsAccountId
        created
        dashboardsEnabled
        warehousesEnabled
        parameters {
          key
          value
        }
      }
    }
  `
});

export default createEnvironment;
