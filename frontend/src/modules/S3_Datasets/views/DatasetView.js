import {
  ForumOutlined,
  Info,
  LocalOffer,
  LockOpen,
  ShareOutlined,
  Upload,
  ViewArrayOutlined
} from '@mui/icons-material';
import AutoModeIcon from '@mui/icons-material/AutoMode';
import {
  Box,
  Breadcrumbs,
  Button,
  CircularProgress,
  Container,
  Divider,
  Grid,
  Link,
  Tab,
  Tabs,
  Typography
} from '@mui/material';
import { useSnackbar } from 'notistack';
import React, { useCallback, useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { FaAws, FaTrash } from 'react-icons/fa';
import { useNavigate } from 'react-router';
import { Link as RouterLink, useParams } from 'react-router-dom';
import {
  ChevronRightIcon,
  DeleteObjectWithFrictionModal,
  PencilAltIcon,
  UpVoteButton,
  useSettings
} from 'design';
import { SET_ERROR, useDispatch } from 'globalErrors';
import { getDataset, countUpVotes, getVote, upVote, useClient } from 'services';
import { deleteDataset } from '../services';
import { ShareBoxList } from 'modules/Shares';
import { FeedComments, KeyValueTagList, Stack } from 'modules/Shared';
import {
  DatasetAWSActions,
  DatasetData,
  DatasetOverview,
  DatasetUpload,
  MetadataMainModal
} from '../components';
import { isFeatureEnabled, isModuleEnabled, ModuleNames } from 'utils';
import { RequestAccessModal } from 'modules/Catalog/components';
import { MetadataAttachment } from '../../Metadata_Forms/components';

const DatasetView = () => {
  const dispatch = useDispatch();
  const { settings } = useSettings();
  const { enqueueSnackbar } = useSnackbar();
  const params = useParams();
  const client = useClient();
  const navigate = useNavigate();
  const [currentTab, setCurrentTab] = useState('data');
  const [loading, setLoading] = useState(true);
  const [dataset, setDataset] = useState(null);
  const [isDeleteObjectModalOpen, setIsDeleteObjectModalOpen] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);
  const [isUpVoted, setIsUpVoted] = useState(false);
  const [upVotes, setUpvotes] = useState(null);
  const [openFeed, setOpenFeed] = useState(false);
  const getTabs = () => {
    const tabs = [
      {
        label: 'Data',
        value: 'data',
        icon: <ViewArrayOutlined fontSize="small" />
      },
      { label: 'Overview', value: 'overview', icon: <Info fontSize="small" /> },
      {
        label: 'Metadata',
        value: 'metadata',
        icon: <ForumOutlined fontSize="small" />,
        active: isModuleEnabled(ModuleNames.METADATA_FORMS)
      }
    ];
    if (isAdmin) {
      tabs.push({
        label: 'Shares',
        value: 'shares',
        icon: <ShareOutlined fontSize="small" />
      });
      if (isFeatureEnabled('s3_datasets', 'file_uploads')) {
        tabs.push({
          label: 'Upload',
          value: 'upload',
          icon: <Upload fontSize="small" />
        });
      }
      if (settings.isAdvancedMode) {
        tabs.push({
          label: 'Tags',
          value: 'tags',
          icon: <LocalOffer fontSize="small" />
        });
        tabs.push({
          label: 'Stack',
          value: 'stack',
          icon: <FaAws size={20} />
        });
      }
    }
    return tabs.filter((tab) => tab.active !== false);
  };

  const handleDeleteObjectModalOpen = () => {
    setIsDeleteObjectModalOpen(true);
  };

  const handleDeleteObjectModalClose = () => {
    setIsDeleteObjectModalOpen(false);
  };

  const getUserDatasetVote = useCallback(
    async (datasetUri) => {
      const response = await client.query(getVote(datasetUri, 'dataset'));
      if (!response.errors && response.data.getVote !== null) {
        setIsUpVoted(response.data.getVote.upvote);
      }
    },
    [client]
  );

  const [isRequestAccessOpen, setIsRequestAccessOpen] = useState(false);
  const [isOpeningModal, setIsOpeningModal] = useState(false);
  const [isMetadataModalOpen, setIsMetadataModalOpen] = useState(false);
  const handleRequestAccessModalOpen = () => {
    setIsOpeningModal(true);
    setIsRequestAccessOpen(true);
  };

  const handleRequestAccessModalClose = () => {
    setIsRequestAccessOpen(false);
  };

  const handleMetadataModalOpen = () => {
    setIsMetadataModalOpen(true);
  };

  const handleMetadataModalClose = () => {
    setIsMetadataModalOpen(false);
  };

  const reloadVotes = async () => {
    const response = await client.query(countUpVotes(params.uri, 'dataset'));
    if (!response.errors && response.data.countUpVotes !== null) {
      setUpvotes(response.data.countUpVotes);
    } else {
      setUpvotes(0);
    }
  };

  const upVoteDataset = async (datasetUri) => {
    const response = await client.mutate(
      upVote({
        targetUri: datasetUri,
        targetType: 'dataset',
        upvote: !isUpVoted
      })
    );
    if (!response.errors && response.data.upVote !== null) {
      setIsUpVoted(response.data.upVote.upvote);
    }
    reloadVotes().catch((e) => dispatch({ type: SET_ERROR, error: e.message }));
  };

  const fetchItem = useCallback(async () => {
    setLoading(true);
    const response = await client.query(getDataset(params.uri));
    if (!response.errors && response.data.getDataset !== null) {
      setDataset(response.data.getDataset);
      setIsAdmin(
        ['BusinessOwner', 'Admin', 'DataSteward', 'Creator'].indexOf(
          response.data.getDataset.userRoleForDataset
        ) !== -1
      );
      setUpvotes(response.data.getDataset.statistics.upvotes);
    } else {
      const error = response.errors
        ? response.errors[0].message
        : 'Dataset not found';
      dispatch({ type: SET_ERROR, error });
    }
    setLoading(false);
  }, [client, dispatch, params.uri]);

  useEffect(() => {
    if (client) {
      getUserDatasetVote(params.uri).catch((e) =>
        dispatch({ type: SET_ERROR, error: e.message })
      );
      fetchItem().catch((e) => dispatch({ type: SET_ERROR, error: e.message }));
    }
  }, [client, fetchItem, getUserDatasetVote, dispatch, params.uri]);

  const handleTabsChange = (event, value) => {
    setCurrentTab(value);
  };

  const removeDataset = async (deleteFromAWS = false) => {
    const response = await client.mutate(
      deleteDataset(dataset.datasetUri, deleteFromAWS)
    );
    if (!response.errors) {
      handleDeleteObjectModalClose();
      enqueueSnackbar('Dataset deleted', {
        anchorOrigin: {
          horizontal: 'right',
          vertical: 'top'
        },
        variant: 'success'
      });
      navigate('/console/datasets');
    } else {
      dispatch({ type: SET_ERROR, error: response.errors[0].message });
    }
  };

  if (loading) {
    return <CircularProgress />;
  }
  if (!dataset) {
    return null;
  }

  return (
    <>
      <Helmet>
        <title>Datasets: Dataset Details | data.all</title>
      </Helmet>
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
                Dataset {dataset.label}
              </Typography>
              <Breadcrumbs
                aria-label="breadcrumb"
                separator={<ChevronRightIcon fontSize="small" />}
                sx={{ mt: 1 }}
              >
                <Typography color="textPrimary" variant="subtitle2">
                  Contribute
                </Typography>
                <Link
                  underline="hover"
                  color="textPrimary"
                  component={RouterLink}
                  to="/console/datasets"
                  variant="subtitle2"
                >
                  Datasets
                </Link>
                <Link
                  underline="hover"
                  color="textPrimary"
                  component={RouterLink}
                  to={`/console/s3-datasets/${dataset.datasetUri}`}
                  variant="subtitle2"
                >
                  {dataset.label}
                </Link>
              </Breadcrumbs>
            </Grid>

            <Grid item>
              <Box sx={{ m: -1 }}>
                {isFeatureEnabled('s3_datasets', 'generate_metadata_ai') && (
                  <Button
                    color="primary"
                    startIcon={<AutoModeIcon size={15} />}
                    sx={{ mt: 1, mr: 1 }}
                    onClick={handleMetadataModalOpen}
                    type="button"
                    variant="outlined"
                  >
                    Generate Metadata with AI
                  </Button>
                )}

                {isFeatureEnabled('s3_datasets', 'generate_metadata_ai') && (
                  <MetadataMainModal
                    onApply={handleMetadataModalClose}
                    onClose={handleMetadataModalClose}
                    open={isMetadataModalOpen}
                    dataset={dataset}
                  />
                )}

                {isAdmin && (
                  <span>
                    <UpVoteButton
                      upVoted={isUpVoted}
                      onClick={() => upVoteDataset(dataset.datasetUri)}
                      upVotes={upVotes}
                    />
                    <Button
                      color="primary"
                      startIcon={<ForumOutlined fontSize="small" />}
                      sx={{ mt: 1, mr: 1 }}
                      onClick={() => setOpenFeed(true)}
                      type="button"
                      variant="outlined"
                    >
                      Chat
                    </Button>
                    {isFeatureEnabled('s3_datasets', 'aws_actions') && (
                      <DatasetAWSActions dataset={dataset} isAdmin={isAdmin} />
                    )}
                    <Button
                      color="primary"
                      component={RouterLink}
                      startIcon={<PencilAltIcon fontSize="small" />}
                      sx={{ mt: 1, mr: 1 }}
                      to={`/console/s3-datasets/${dataset.datasetUri}/edit`}
                      variant="outlined"
                    >
                      Edit
                    </Button>
                    <Button
                      color="primary"
                      startIcon={<FaTrash size={15} />}
                      sx={{ mt: 1 }}
                      onClick={handleDeleteObjectModalOpen}
                      type="button"
                      variant="outlined"
                    >
                      Delete
                    </Button>
                  </span>
                )}
                {isOpeningModal ? (
                  <CircularProgress size={20} />
                ) : (
                  <Button
                    color="primary"
                    startIcon={<LockOpen size={15} />}
                    onClick={handleRequestAccessModalOpen}
                    type="button"
                    sx={{ mt: 1, ml: 1 }}
                    variant="outlined"
                  >
                    Request Access
                  </Button>
                )}
                <RequestAccessModal
                  onApply={handleRequestAccessModalClose}
                  onClose={handleRequestAccessModalClose}
                  open={isRequestAccessOpen}
                  stopLoader={() => setIsOpeningModal(false)}
                  hit={{
                    _id: dataset.datasetUri,
                    resourceKind: 'dataset',
                    label: dataset.label
                  }}
                />
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
            {currentTab === 'data' && (
              <DatasetData dataset={dataset} isAdmin={isAdmin} />
            )}
            {currentTab === 'metadata' && (
              <MetadataAttachment entityType="Dataset" entityUri={params.uri} />
            )}
            {currentTab === 'overview' && (
              <DatasetOverview dataset={dataset} isAdmin={isAdmin} />
            )}
            {isAdmin && currentTab === 'shares' && (
              <ShareBoxList tab={'inbox'} dataset={dataset} />
            )}
            {isAdmin && currentTab === 'upload' && (
              <DatasetUpload dataset={dataset} isAdmin={isAdmin} />
            )}
            {isAdmin && currentTab === 'tags' && (
              <KeyValueTagList
                targetUri={dataset.datasetUri}
                targetType="dataset"
              />
            )}
            {isAdmin && currentTab === 'stack' && (
              <Stack
                environmentUri={dataset.environment.environmentUri}
                stackUri={dataset.stack.stackUri}
                targetUri={dataset.datasetUri}
                targetType="dataset"
              />
            )}
          </Box>
        </Container>
      </Box>
      {isAdmin && (
        <DeleteObjectWithFrictionModal
          objectName={dataset.label}
          onApply={handleDeleteObjectModalClose}
          onClose={handleDeleteObjectModalClose}
          open={isDeleteObjectModalOpen}
          deleteFunction={removeDataset}
          isAWSResource
        />
      )}
      {openFeed && (
        <FeedComments
          objectOwner={dataset.owner}
          targetType="Dataset"
          targetUri={dataset.datasetUri}
          open={openFeed}
          onClose={() => setOpenFeed(false)}
        />
      )}
    </>
  );
};

export default DatasetView;
