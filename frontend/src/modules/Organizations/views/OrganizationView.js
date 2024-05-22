import {
  ArchiveOutlined,
  Info,
  SupervisedUserCircleRounded,
  Warning
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
import {
  archiveOrganization,
  listOrganizationGroups,
  listOrganizationReadOnlyGroups
} from '../services';
import {
  OrganizationEnvironments,
  OrganizationOverview,
  TeamsTableCard
} from '../components';

const tabs = [
  { label: 'Overview', value: 'overview', icon: <Info fontSize="small" /> },
  { label: 'Environments', value: 'environments', icon: <FaAws size={20} /> },
  {
    label: 'Teams',
    value: 'teams',
    icon: <SupervisedUserCircleRounded fontSize="small" />
  }
];

const OrganizationView = () => {
  const { settings } = useSettings();
  const { enqueueSnackbar } = useSnackbar();
  const navigate = useNavigate();
  const [org, setOrg] = useState(null);
  const dispatch = useDispatch();
  const params = useParams();
  const client = useClient();
  const [currentTab, setCurrentTab] = useState('overview');
  const [loading, setLoading] = useState(true);
  const [isArchiveObjectModalOpen, setIsArchiveObjectModalOpen] =
    useState(false);
  const handleArchiveObjectModalOpen = () => {
    setIsArchiveObjectModalOpen(true);
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
      var org = response.data.getOrganization;
      org.canEdit = org.permissions.includes('UPDATE_ORGANIZATION');
      org.canInvite = org.permissions.includes('INVITE_ORGANIZATION_GROUP');
      org.canDelete = org.permissions.includes('DELETE_ORGANIZATION');
      org.canLink = org.permissions.includes('LINK_ENVIRONMENT');
      org.canRemoveGroup = org.permissions.includes(
        'REMOVE_ORGANIZATION_GROUP'
      );
      setOrg(response.data.getOrganization);
      setLoading(false);
    }
    setLoading(false);
  }, [client, params.uri]);

  useEffect(() => {
    if (client) {
      fetchItem().catch((e) => dispatch({ type: SET_ERROR, error: e.message }));
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
                <Box sx={{ m: -1 }}>
                  {org.canEdit && (
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
                  )}
                  {org.canDelete && (
                    <Button
                      color="primary"
                      startIcon={<ArchiveOutlined />}
                      sx={{ m: 1 }}
                      variant="outlined"
                      onClick={handleArchiveObjectModalOpen}
                    >
                      Archive
                    </Button>
                  )}
                </Box>
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
                {tabs.map((tab) => (
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
                <Grid container spacing={3}>
                  <Grid item md={8} xl={8} xs={16}>
                    <TeamsTableCard
                      organization={org}
                      showActions={true}
                      showPermissions={true}
                      showInvite={true}
                      teamsName={'Administrators'}
                      queryFunction={listOrganizationGroups}
                      resultName={'listOrganizationGroups'}
                    />
                  </Grid>
                  <Grid item md={4} xl={4} xs={8}>
                    <TeamsTableCard
                      organization={org}
                      showActions={false}
                      showPermissions={false}
                      showInvite={false}
                      teamsName={'Readers'}
                      queryFunction={listOrganizationReadOnlyGroups}
                      resultName={'listOrganizationReadOnlyGroups'}
                    />
                  </Grid>
                </Grid>
              )}
              {currentTab === 'environments' && (
                <OrganizationEnvironments organization={org} />
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
