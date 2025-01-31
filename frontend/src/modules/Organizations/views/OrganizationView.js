import {
  ArchiveOutlined,
  BallotOutlined,
  Info,
  SupervisedUserCircleRounded,
  Warning,
  WarningAmber
} from '@mui/icons-material';
import {
  Box,
  Breadcrumbs,
  Button,
  Card,
  CardContent,
  Container,
  Divider,
  Grid,
  Link,
  Tab,
  Tabs,
  Typography
} from '@mui/material';
import CircularProgress from '@mui/material/CircularProgress';
import { useSnackbar } from 'notistack';
import React, { useCallback, useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { FaAws } from 'react-icons/fa';
import { Link as RouterLink, useNavigate, useParams } from 'react-router-dom';
import {
  ArchiveObjectWithFrictionModal,
  ChevronRightIcon,
  PencilAltIcon,
  useSettings
} from 'design';
import { SET_ERROR, useDispatch } from 'globalErrors';
import { getOrganization, useClient } from 'services';
import { archiveOrganization } from '../services';
import {
  OrganizationEnvironments,
  OrganizationOverview,
  OrganizationTeams
} from '../components';
import { MetadataAttachment } from '../../Metadata_Forms/components';
import { isModuleEnabled, ModuleNames } from '../../../utils';
import { listRulesThatAffectEntity } from '../../Metadata_Forms/services';

const OrganizationView = () => {
  const { settings } = useSettings();
  const { enqueueSnackbar } = useSnackbar();
  const navigate = useNavigate();
  const [org, setOrg] = useState(null);
  const dispatch = useDispatch();
  const params = useParams();
  const client = useClient();
  const [isAdmin, setIsAdmin] = useState(false);
  const [currentTab, setCurrentTab] = useState('overview');
  const [loading, setLoading] = useState(true);
  const [isArchiveObjectModalOpen, setIsArchiveObjectModalOpen] =
    useState(false);

  const [affectingMFRules, setAffectingMFRules] = useState([]);

  const getTabs = () => {
    const tabs = [
      { label: 'Overview', value: 'overview', icon: <Info fontSize="small" /> },
      {
        label: 'Environments',
        value: 'environments',
        icon: <FaAws size={20} />
      },
      {
        label: (
          <>
            Metadata{' '}
            {affectingMFRules.filter(
              (r) => r.severity === 'Mandatory' && !r.attached
            ).length > 0 ? (
              <WarningAmber sx={{ color: 'red', ml: 1 }} />
            ) : null}
            {affectingMFRules.filter(
              (r) => r.severity === 'Mandatory' && !r.attached
            ).length === 0 &&
            affectingMFRules.filter(
              (r) => r.severity === 'Recommended' && !r.attached
            ).length > 0 ? (
              <WarningAmber sx={{ color: 'orange', ml: 1 }} />
            ) : null}
          </>
        ),
        value: 'metadata',
        icon: <BallotOutlined fontSize="small" />,
        active: isModuleEnabled(ModuleNames.METADATA_FORMS)
      },
      {
        label: 'Teams',
        value: 'teams',
        icon: <SupervisedUserCircleRounded fontSize="small" />
      }
    ];

    return tabs.filter((tab) => tab.active !== false);
  };
  const handleArchiveObjectModalOpen = () => {
    setIsArchiveObjectModalOpen(true);
  };

  const fetchAffectingMFRules = async () => {
    if (isModuleEnabled(ModuleNames.METADATA_FORMS)) {
      const response = await client.query(
        listRulesThatAffectEntity(params.uri, 'Environment')
      );
      if (
        !response.errors &&
        response.data.listRulesThatAffectEntity !== null
      ) {
        setAffectingMFRules(response.data.listRulesThatAffectEntity);
      }
    }
  };
  const handleArchiveObjectModalClose = () => {
    setIsArchiveObjectModalOpen(false);
  };

  const handleTabsChange = (event, value) => {
    setCurrentTab(value);
  };

  const archiveOrg = async () => {
    const response = await client.mutate(
      archiveOrganization(org.organizationUri)
    );
    if (!response.errors) {
      enqueueSnackbar('Organization archived', {
        anchorOrigin: {
          horizontal: 'right',
          vertical: 'top'
        },
        variant: 'success'
      });
      navigate('/console/organizations');
      setLoading(false);
    } else {
      dispatch({ type: SET_ERROR, error: response.errors[0].message });
    }
  };

  const fetchItem = useCallback(async () => {
    const response = await client.query(getOrganization(params.uri));
    if (!response.errors) {
      setOrg(response.data.getOrganization);
      setIsAdmin(
        ['Admin', 'Owner'].indexOf(
          response.data.getOrganization.userRoleInOrganization
        ) !== -1
      );
      setLoading(false);
    }
    setLoading(false);
  }, [client, params.uri]);

  useEffect(() => {
    if (client) {
      fetchItem().catch((e) => dispatch({ type: SET_ERROR, error: e.message }));
      fetchAffectingMFRules().catch((e) =>
        dispatch({ type: SET_ERROR, error: e.message })
      );
    }
  }, [client, dispatch, fetchItem]);

  if (!org) {
    return null;
  }

  return (
    <>
      <Helmet>
        <title>Organizations: Organization Details | data.all</title>
      </Helmet>
      {loading ? (
        <CircularProgress />
      ) : (
        <Box
          sx={{
            backgroundColor: 'background.default',
            minHeight: '100%',
            py: 8
          }}
        >
          <Container maxWidth={settings.compact ? 'xl' : false}>
            <Grid container justifyContent="space-between" spacing={3}>
              <Grid item>
                <Typography color="textPrimary" variant="h5">
                  Organization {org.label}
                </Typography>
                <Breadcrumbs
                  aria-label="breadcrumb"
                  separator={<ChevronRightIcon fontSize="small" />}
                  sx={{ mt: 1 }}
                >
                  <Link
                    underline="hover"
                    color="textPrimary"
                    component={RouterLink}
                    to="/console/organizations"
                    variant="subtitle2"
                  >
                    Admin
                  </Link>
                  <Link
                    underline="hover"
                    color="textPrimary"
                    component={RouterLink}
                    to="/console/organizations"
                    variant="subtitle2"
                  >
                    Organizations
                  </Link>
                  <Typography color="textSecondary" variant="subtitle2">
                    {org.label}
                  </Typography>
                </Breadcrumbs>
              </Grid>
              <Grid item>
                {isAdmin && (
                  <Box sx={{ m: -1 }}>
                    <Button
                      color="primary"
                      component={RouterLink}
                      startIcon={<PencilAltIcon fontSize="small" />}
                      sx={{ m: 1 }}
                      variant="outlined"
                      to={`/console/organizations/${org.organizationUri}/edit`}
                    >
                      Edit
                    </Button>
                    <Button
                      color="primary"
                      startIcon={<ArchiveOutlined />}
                      sx={{ m: 1 }}
                      variant="outlined"
                      onClick={handleArchiveObjectModalOpen}
                    >
                      Archive
                    </Button>
                  </Box>
                )}
              </Grid>
            </Grid>
            <Box sx={{ mt: 3 }}>
              <Tabs
                indicatorColor="primary"
                onChange={handleTabsChange}
                scrollButtons="auto"
                textColor="primary"
                value={currentTab}
                variant="fullWidth"
              >
                {getTabs().map((tab) => (
                  <Tab
                    key={tab.value}
                    label={tab.label}
                    value={tab.value}
                    icon={settings.tabIcons ? tab.icon : null}
                    iconPosition="start"
                  />
                ))}
              </Tabs>
            </Box>
            <Divider />
            <Box sx={{ mt: 3 }}>
              {currentTab === 'overview' && (
                <OrganizationOverview organization={org} />
              )}
              {currentTab === 'teams' && (
                <OrganizationTeams organization={org} />
              )}
              {currentTab === 'environments' && (
                <OrganizationEnvironments organization={org} />
              )}
              {currentTab === 'metadata' && (
                <MetadataAttachment
                  entityType="Organization"
                  entityUri={org.organizationUri}
                  affectingRules={affectingMFRules}
                />
              )}
            </Box>
          </Container>
        </Box>
      )}
      {isArchiveObjectModalOpen && (
        <ArchiveObjectWithFrictionModal
          objectName={org.label}
          onApply={handleArchiveObjectModalClose}
          onClose={handleArchiveObjectModalClose}
          open={isArchiveObjectModalOpen}
          archiveFunction={archiveOrg}
          archiveMessage={
            <Card variant="outlined" color="error" sx={{ mb: 2 }}>
              <CardContent>
                <Typography variant="subtitle2" color="error">
                  <Warning sx={{ mr: 1 }} /> Remove all environments linked to
                  the organization before archiving !
                </Typography>
              </CardContent>
            </Card>
          }
        />
      )}
    </>
  );
};

export default OrganizationView;
