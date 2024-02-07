import { Box, Grid } from '@mui/material';
import PropTypes from 'prop-types';
import { ObjectBrief, ObjectMetadata } from 'design';
import { EnvironmentConsoleAccess } from 'modules/Environments/components/EnvironmentConsoleAccess';
import { EnvironmentFeatures } from 'modules/Environments/components/EnvironmentFeatures';

export const EnvironmentOverview = (props) => {
  const { environment, ...other } = props;

  return (
    <Grid container spacing={3} {...other}>
      <Grid item lg={8} xl={9} xs={12}>
        <Box>
          <ObjectBrief
            uri={environment.environmentUri || '-'}
            name={environment.label || '-'}
            description={environment.description || 'No description provided'}
            tags={environment.tags.length > 0 ? environment.tags : ['-']}
          />
        </Box>
        <Box sx={{ mt: 3 }}>
          <EnvironmentConsoleAccess environment={environment} />
        </Box>
      </Grid>
      <Grid item lg={4} xl={3} xs={12}>
        <ObjectMetadata
          accountId={environment.AwsAccountId}
          region={environment.region}
          organization={environment.organization}
          owner={environment.owner}
          admins={environment.SamlGroupName || '-'}
          created={environment.created}
          status={environment.stack?.status}
        />
        <Box sx={{ mt: 3 }}>
          <EnvironmentFeatures environment={environment} />
        </Box>
      </Grid>
    </Grid>
  );
};

EnvironmentOverview.propTypes = {
  environment: PropTypes.object.isRequired
};
