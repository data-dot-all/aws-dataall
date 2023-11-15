import {
  Autocomplete,
  Box,
  Container,
  Divider,
  Grid,
  TextField,
  Typography
} from '@mui/material';
import CircularProgress from '@mui/material/CircularProgress';
import PropTypes from 'prop-types';
import { useCallback, useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Defaults, Pager, useSettings } from 'design';
import { SET_ERROR, useDispatch } from 'globalErrors';
import {
  listDatasetShareObjects,
  getShareRequestsToMe,
  useClient
} from 'services';

import { ShareInboxListItem } from './ShareInboxListItem';
import { listDatasets } from '../../Datasets/services'; //TODO MANAGE DEPENDENCY

export const ShareInboxList = (props) => {
  const { dataset } = props;
  const dispatch = useDispatch();
  const [items, setItems] = useState(Defaults.pagedResponse);
  const [filter, setFilter] = useState(Defaults.filter);
  const [groupOptions, setGroupOptions] = useState([]);
  const [myGroupOptions, setMyGroupOptions] = useState([]);
  const [myDatasets, setMyDatasets] = useState([]); //all in listDatasets, either shared with me or owned by my teams
  const statusOptions = [
    'Draft',
    'Submitted',
    'Approved',
    'Rejected',
    'Revoked',
    'Share_In_Progress',
    'Revoke_In_Progress',
    'Processed'
  ];
  // In Received, dataset_owners : All groups I belong to
  // In Received, request_owners: All groups that have a request open to one of my datasets or All groups alternatively
  // In Sent, dataset_owners : All groups that have a dataset with a request open by one of my share requests. or All groups
  // In Sent, request_owners: All groups I belong to
  const { settings } = useSettings();
  const [loading, setLoading] = useState(true);
  const client = useClient();

  const handlePageChange = async (event, value) => {
    if (value <= items.pages && value !== items.page) {
      await setFilter({ ...filter, page: value });
    }
  };

  const handleFilterChange = (filterLabel, values) => {
    if (filterLabel === 'Status') {
      setFilter({ ...filter, status: values });
    } else if (filterLabel === 'Datasets') {
      const selectedDatasetsUris = values.map((dataset) => dataset.value);
      setFilter({ ...filter, datasets_uris: selectedDatasetsUris });
    } else if (filterLabel === 'Dataset Owners') {
      setFilter({ ...filter, dataset_owners: values });
    } else if (filterLabel === 'Request Owners') {
      setFilter({ ...filter, share_requesters: values });
    }
  };

  const fetchItems = useCallback(async () => {
    /* eslint-disable no-console */
    console.log('NEW FETCH');
    console.log(filter);
    if (dataset) {
      await client
        .query(
          listDatasetShareObjects({ datasetUri: dataset.datasetUri, filter })
        )
        .then((response) => {
          setItems(response.data.getDataset.shares);
        })
        .catch((error) => {
          dispatch({ type: SET_ERROR, error: error.Error });
        })
        .finally(() => setLoading(false));
    } else {
      await client
        .query(
          getShareRequestsToMe({
            filter: {
              ...filter
            }
          })
        )
        .then((response) => {
          setItems(response.data.getShareRequestsToMe);
        })
        .catch((error) => {
          dispatch({ type: SET_ERROR, error: error.Error });
        })
        .finally(() => setLoading(false));
    }
  }, [client, dispatch, dataset, filter]);

  const fetchGroupOptions = useCallback(async () => {
    /* eslint-disable no-console */
    await client
      .query(
        getShareRequestsToMe({
          filter: {
            ...filter
          }
        })
      )
      .then((response) => {
        setItems(response.data.getShareRequestsToMe);
        setMyGroupOptions(
          Array.from(
            new Set(
              response.data.getShareRequestsToMe.nodes.map(
                (node) => node.dataset.SamlAdminGroupName
              )
            )
          )
        );
        /* eslint-disable no-console */
        setGroupOptions(
          Array.from(
            new Set(
              response.data.getShareRequestsToMe.nodes.map(
                (node) => node.principal.SamlGroupName
              )
            )
          )
        );
      })
      .catch((error) => {
        dispatch({ type: SET_ERROR, error: error.Error });
      })
      .finally(() => setLoading(false));
  }, [client, dispatch]);

  const fetchDatasetOptions = useCallback(async () => {
    setLoading(true);
    const response = await client.query(
      listDatasets(Defaults.selectListFilter)
    );
    if (!response.errors) {
      setMyDatasets(
        response.data.listDatasets.nodes.map((node) => ({
          ...node,
          label: node.label,
          value: node.datasetUri
        }))
      );
    } else {
      dispatch({ type: SET_ERROR, error: response.errors[0].message });
    }
    setLoading(false);
  }, [client, dispatch, filter]);

  useEffect(() => {
    if (client) {
      fetchItems().catch((error) => {
        dispatch({ type: SET_ERROR, error: error.message });
      });
    }
  }, [client, filter.page, dispatch, fetchItems]);

  useEffect(() => {
    if (client) {
      fetchDatasetOptions().catch((error) => {
        dispatch({ type: SET_ERROR, error: error.message });
      });
      fetchGroupOptions().catch((error) => {
        dispatch({ type: SET_ERROR, error: error.message });
      });
    }
  }, [client]);

  if (loading) {
    return <CircularProgress />;
  }

  return (
    <>
      <Helmet>
        <title>Shares Inbox | data.all</title>
      </Helmet>
      <Box
        sx={{
          backgroundColor: 'background.default',
          minHeight: '100%',
          py: 1
        }}
      >
        <Container maxWidth={settings.compact ? 'xl' : false}>
          <Box
            sx={{
              mt: 2
            }}
          >
            <Grid container spacing={2} xs={12}>
              <Grid item md={3} xs={12}>
                <Autocomplete
                  id={'Status'}
                  multiple
                  fullWidth
                  loading={loading}
                  options={statusOptions}
                  onChange={(event, value) =>
                    handleFilterChange('Status', value)
                  }
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label={'Status'}
                      fullWidth
                      variant="outlined"
                    />
                  )}
                />
              </Grid>
              <Grid item md={3} xs={12}>
                <Autocomplete
                  id={'Datasets'}
                  multiple
                  fullWidth
                  loading={loading}
                  options={myDatasets}
                  getOptionLabel={(option) => option.label}
                  onChange={(event, value) =>
                    handleFilterChange('Datasets', value)
                  }
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label={'Datasets'}
                      fullWidth
                      variant="outlined"
                    />
                  )}
                />
              </Grid>
              <Grid item md={3} xs={12}>
                <Autocomplete
                  id={'Datasets Owners'}
                  multiple
                  fullWidth
                  loading={loading}
                  options={myGroupOptions}
                  onChange={(event, value) =>
                    handleFilterChange('Datasets Owners', value)
                  }
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label={'Datasets Owners'}
                      fullWidth
                      variant="outlined"
                    />
                  )}
                />
              </Grid>
              <Grid item md={3} xs={12}>
                <Autocomplete
                  id={'Request Owners'}
                  multiple
                  fullWidth
                  loading={loading}
                  options={groupOptions}
                  onChange={(event, value) =>
                    handleFilterChange('Request Owners', value)
                  }
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label={'Request Owners'}
                      fullWidth
                      variant="outlined"
                    />
                  )}
                />
              </Grid>
            </Grid>
          </Box>
          <Divider />
          <Box
            sx={{
              mt: 3
            }}
          >
            {items.nodes.length <= 0 ? (
              <Typography color="textPrimary" variant="subtitle2">
                No share requests received.
              </Typography>
            ) : (
              <Box>
                {items.nodes.map((node) => (
                  <ShareInboxListItem share={node} reload={fetchItems} />
                ))}

                <Pager items={items} onChange={handlePageChange} />
              </Box>
            )}
          </Box>
        </Container>
      </Box>
    </>
  );
};

ShareInboxList.propTypes = {
  dataset: PropTypes.object
};
