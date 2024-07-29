import {
  Box,
  Breadcrumbs,
  Button,
  Container,
  Grid,
  Link,
  Typography
} from '@mui/material';
import CircularProgress from '@mui/material/CircularProgress';
import React, { useCallback, useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link as RouterLink } from 'react-router-dom';
import {
  ChevronRightIcon,
  Defaults,
  Pager,
  PlusIcon,
  SearchInput,
  useSettings
} from 'design';
import { SET_ERROR, useDispatch } from 'globalErrors';
import { useClient } from 'services';
import { listMetadataForms } from '../services';
import { MetadataFormListItem } from '../components';
import { CreateMetadataFormModal } from '../components/createMetadataFormModal';

function MetadataFormsListPageHeader() {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [isOpeningModal, setIsOpeningModal] = useState(false);

  const handleOpenModal = () => {
    setShowCreateModal(true);
    setIsOpeningModal(true);
  };
  const handleCloseModal = () => {
    setShowCreateModal(false);
  };

  return (
    <Grid
      alignItems="center"
      container
      justifyContent="space-between"
      spacing={3}
    >
      {showCreateModal && (
        <CreateMetadataFormModal
          onApply={handleCloseModal}
          onClose={handleCloseModal}
          open={showCreateModal}
          stopLoader={() => setIsOpeningModal(false)}
        ></CreateMetadataFormModal>
      )}
      <Grid item>
        <Typography color="textPrimary" variant="h5">
          Metadata Forms
        </Typography>
        <Breadcrumbs
          aria-label="breadcrumb"
          separator={<ChevronRightIcon fontSize="small" />}
          sx={{ mt: 1 }}
        >
          <Typography color="textPrimary" variant="subtitle2">
            Discover
          </Typography>
          <Link
            underline="hover"
            color="textPrimary"
            component={RouterLink}
            to="/console/metadata-forms"
            variant="subtitle2"
          >
            Metadata Forms
          </Link>
        </Breadcrumbs>
      </Grid>
      <Grid item>
        <Box sx={{ m: -1 }}>
          <Button
            color="primary"
            startIcon={
              isOpeningModal ? (
                <CircularProgress size={20} />
              ) : (
                <PlusIcon fontSize="small" />
              )
            }
            sx={{ m: 1 }}
            variant="contained"
            onClick={handleOpenModal}
          >
            New Metadata Form
          </Button>
        </Box>
      </Grid>
    </Grid>
  );
}

const MetadataFormsList = () => {
  const dispatch = useDispatch();
  const [items, setItems] = useState(Defaults.pagedResponse);
  const [filter, setFilter] = useState({ term: '', page: 1, pageSize: 10 });
  const { settings } = useSettings();
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(true);

  const client = useClient();

  const fetchItems = useCallback(async () => {
    setLoading(true);
    const response = await client.query(listMetadataForms({}));
    if (!response.errors) {
      setItems(response.data.listMetadataForms);
    } else {
      dispatch({ type: SET_ERROR, error: response.errors[0].message });
    }
    setLoading(false);
  }, [client, dispatch, filter]);

  const handleInputChange = (event) => {
    setInputValue(event.target.value);
    setFilter({ ...filter, term: event.target.value });
  };

  const handleInputKeyup = (event) => {
    if (event.code === 'Enter') {
      setFilter({ page: 1, term: event.target.value });
      fetchItems().catch((e) =>
        dispatch({ type: SET_ERROR, error: e.message })
      );
    }
  };

  const handlePageChange = async (event, value) => {
    if (value <= items.pages && value !== items.page) {
      await setFilter({ ...filter, page: value });
    }
  };

  useEffect(() => {
    if (client) {
      fetchItems().catch((e) =>
        dispatch({ type: SET_ERROR, error: e.message })
      );
    }
  }, [client, filter.page, fetchItems, dispatch]);

  return (
    <>
      <Helmet>
        <title>Datasets | data.all</title>
      </Helmet>
      <Box
        sx={{
          backgroundColor: 'background.default',
          minHeight: '100%',
          py: 5
        }}
      >
        <Container maxWidth={settings.compact ? 'xl' : false}>
          <MetadataFormsListPageHeader />
          <Box sx={{ mt: 3 }}>
            <SearchInput
              onChange={handleInputChange}
              onKeyUp={handleInputKeyup}
              value={inputValue}
            />
          </Box>

          <Box
            sx={{
              flexGrow: 1,
              mt: 3
            }}
          >
            {loading ? (
              <CircularProgress />
            ) : (
              <Box>
                <Grid container spacing={3}>
                  {items.nodes.map((node) => (
                    <MetadataFormListItem metadata_form={node} />
                  ))}
                </Grid>

                <Pager items={items} onChange={handlePageChange} />
              </Box>
            )}
          </Box>
        </Container>
      </Box>
    </>
  );
};

export default MetadataFormsList;
