// import { LoadingButton } from '@mui/lab';
import {
  // Autocomplete,
  Avatar,
  Box,
  Button,
  // CardContent,
  // CardHeader,
  Checkbox,
  Chip,
  Divider,
  FormControl,
  FormGroup,
  FormControlLabel,
  FormLabel,
  Grid,
  InputLabel,
  MenuItem,
  Select,
  Switch,
  // TextField,
  Typography
} from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
// import { Formik } from 'formik';
import { useSnackbar } from 'notistack';
import PropTypes from 'prop-types';
// import { useCallback, useEffect, useState } from 'react';
import { useState } from 'react';
import AutoModeIcon from '@mui/icons-material/AutoMode';
// import * as Yup from 'yup';
// import { ChipInput, Defaults } from 'design';
import { Defaults, Scrollbar } from 'design';
import { SET_ERROR, useDispatch } from 'globalErrors';
import { useClient } from 'services';
import { listDatasetTablesFolders, generateMetadataBedrock } from '../services';
import { useCallback } from 'react';

/* eslint-disable no-console */
export const GenerateMetadataComponent = (props) => {
  const {
    dataset,
    targetType,
    setTargetType,
    targets,
    setTargets,
    targetOptions,
    setTargetOptions,
    selectedMetadataTypes,
    setSelectedMetadataTypes,
    currentView,
    setCurrentView,
    loadingMetadata,
    setLoadingMetadata,
    version,
    setVersion,
    ...other
  } = props;
  const { enqueueSnackbar } = useSnackbar();
  const dispatch = useDispatch();

  const client = useClient();
  const [loadingTableFolder, setLoadingTableFolder] = useState(false);
  const [tableFolderFilter, setTableFolderFilter] = useState(Defaults.filter);
  const handleChange = useCallback(
    async (event) => {
      setTargetType(event.target.value);
      if (event.target.value === 'Dataset') {
        setTargets([
          {
            targetUri: dataset.datasetUri,
            targetType: 'S3_Dataset'
          }
        ]);
      } else {
        setTargets([]);
        setLoadingTableFolder(true);
        const response = await client.query(
          listDatasetTablesFolders({
            datasetUri: dataset.datasetUri,
            filter: tableFolderFilter
          })
        );
        if (!response.errors) {
          setTargetOptions(response.data.listDatasetTablesFolders);
        } else {
          dispatch({
            type: SET_ERROR,
            error: response.errors[0].message + dataset.datasetUri
          });
        }
        setLoadingTableFolder(false);
      }
    },
    [client, dispatch]
  );

  const handleMetadataChange = (event) => {
    setSelectedMetadataTypes({
      ...selectedMetadataTypes,
      [event.target.name]: event.target.checked
    });
  };

  const handlePageChange = async (page) => {
    page += 1; //expecting 1-indexing
    if (page <= targetOptions.pages && page !== targetOptions.page) {
      await setTableFolderFilter({ ...tableFolderFilter, page: page });
    }
  };

  const generateMetadata = async () => {
    setCurrentView('REVIEW_METADATA');
    console.log('generateMetadata');
    for (let target of targets) {
      let response = await client.mutate(
        generateMetadataBedrock({
          resourceUri: target.targetUri,
          targetType: target.targetType,
          metadataTypes: Object.entries(selectedMetadataTypes)
            .filter(([key, value]) => value === true)
            .map(([key]) => key),
          version: version,
          sampleData: {}
        })
      );
      console.log('target.uri', target.targetUri);
      if (!response.errors) {
        target.description = response.data.generateMetadata.description;
        target.label = response.data.generateMetadata.label;
        target.name = response.data.generateMetadata.name;
        target.tags = response.data.generateMetadata.tags;
        target.topic = response.data.generateMetadata.topic;
        console.log('target.response', target.response);
        enqueueSnackbar(`Returned response ${target.response}`, {
          anchorOrigin: {
            horizontal: 'right',
            vertical: 'top'
          },
          variant: 'success'
        });
        setVersion(version + 1);
      }
    }
  };
  return (
    <>
      <Grid
        container
        sx={{ m: 1 }}
        spacing={3}
        justifyContent="flex-start"
        {...other}
      >
        <Grid item lg={2} xl={2} md={2} sm={2} xs={2}>
          <Chip
            avatar={<Avatar>1</Avatar>}
            label="Select target type"
            color="primary"
            variant="outlined"
          />
        </Grid>
        <Grid item lg={6} xl={6} md={6} sm={6} xs={6}>
          {targetType && (
            <Chip
              avatar={<Avatar>2</Avatar>}
              label="Select target resources"
              color="primary"
              variant="outlined"
            />
          )}
        </Grid>
        <Grid item lg={3} xl={3} md={3} sm={3} xs={3}>
          {targetType && !!targets.length && (
            <Chip
              avatar={<Avatar>3</Avatar>}
              label="Select type of metadata"
              color="primary"
              variant="outlined"
            />
          )}
        </Grid>
      </Grid>
      <Divider></Divider>
      <Grid
        container
        sx={{ mt: 1 }}
        spacing={3}
        justifyContent="space-around"
        alignItems="flex-start"
        {...other}
      >
        <Grid item lg={2} xl={2} md={2} sm={2} xs={2}>
          <FormControl sx={{ minWidth: 200, mb: 1 }}>
            <InputLabel id="Target">Target Type *</InputLabel>
            <Select
              id="demo-simple-select"
              value={targetType}
              label="Target Type *"
              onChange={handleChange}
            >
              <MenuItem value={'Dataset'}>Dataset</MenuItem>
              <MenuItem value={'TablesAndFolders'}>Tables and Folders</MenuItem>
            </Select>
          </FormControl>
          {targetType === 'Dataset' && (
            <Typography
              align="left"
              color="textSecondary"
              variant="subtitle2"
              sx={{ ml: 1 }}
            >
              Data.all will use the table and folder metadata to generate
              Dataset label, description, tags and/or topics using Amazon
              Bedrock.
            </Typography>
          )}
          {targetType === 'TablesAndFolders' && (
            <Typography //TODO: better info messages
              align="left"
              color="textSecondary"
              variant="subtitle2"
              sx={{ ml: 1 }}
            >
              Data.all will use table column names and table descriptions and
              folder S3 prefix names to generate Tables and Folders label,
              description, tags and/or topics using Amazon Bedrock.
            </Typography>
          )}
        </Grid>
        <Grid item lg={6} xl={6} md={6} sm={6} xs={6}>
          {targetType === 'Dataset' && (
            <FormControlLabel
              disabled
              control={<Checkbox checked />}
              label={dataset.name}
            />
          )}
          {targetType === 'TablesAndFolders' && (
            <Scrollbar>
              <Box sx={{ minWidth: 600 }}>
                <DataGrid
                  autoHeight
                  checkboxSelection
                  getRowId={(node) => node.targetUri}
                  rows={targetOptions.nodes}
                  columns={[
                    { field: 'targetUri', hide: true },
                    {
                      field: 'name',
                      headerName: 'Name',
                      flex: 1.5,
                      editable: false
                    },
                    {
                      field: 'targetType',
                      headerName: 'Type',
                      flex: 1,
                      editable: false
                    }
                  ]}
                  rowCount={targetOptions.count}
                  page={targetOptions.page - 1}
                  pageSize={targetOptions.pageSize}
                  paginationMode="server"
                  onPageChange={handlePageChange}
                  loading={loadingTableFolder}
                  onPageSizeChange={(pageSize) => {
                    setTableFolderFilter({
                      ...tableFolderFilter,
                      pageSize: pageSize
                    });
                  }}
                  getRowHeight={() => 'auto'}
                  disableSelectionOnClick
                  onSelectionModelChange={(newSelectionModel) => {
                    console.log('selectionModel2', newSelectionModel);
                    const selectedTargets = newSelectionModel.map((id) =>
                      targetOptions.nodes.find(
                        (option) => option.targetUri === id
                      )
                    );
                    console.log('selectedTargets', selectedTargets);
                    setTargets(selectedTargets);
                    if (newSelectionModel.length === 0) {
                      setSelectedMetadataTypes({});
                    }
                  }}
                  sx={{
                    wordWrap: 'break-word',
                    '& .MuiDataGrid-row': {
                      borderBottom: '1px solid rgba(145, 158, 171, 0.24)'
                    },
                    '& .MuiDataGrid-columnHeaders': {
                      borderBottom: 0.5
                    }
                  }}
                />
              </Box>
            </Scrollbar>
          )}
        </Grid>
        <Grid item lg={3} xl={3} md={3} sm={3} xs={3}>
          {targetType && !!targets.length && (
            <FormGroup>
              <FormLabel component="legend">Metadata</FormLabel>
              <FormControlLabel
                control={
                  <Switch
                    name="label"
                    checked={selectedMetadataTypes.label}
                    onChange={handleMetadataChange}
                  />
                }
                label="Label"
              />
              <FormControlLabel
                control={
                  <Switch
                    name="description"
                    checked={selectedMetadataTypes.description}
                    onChange={handleMetadataChange}
                  />
                }
                label="Description"
              />
              <FormControlLabel
                control={
                  <Switch
                    name="tags"
                    checked={selectedMetadataTypes.tags}
                    onChange={handleMetadataChange}
                  />
                }
                label="Tags"
              />
              <FormControlLabel
                control={
                  <Switch
                    name="topic"
                    checked={selectedMetadataTypes.topics}
                    onChange={handleMetadataChange}
                  />
                }
                label="Topic"
              />
            </FormGroup>
          )}
        </Grid>
      </Grid>
      {!loadingMetadata && (
        <Button
          color="primary"
          size="small"
          startIcon={<AutoModeIcon size={15} />}
          sx={{ m: 2 }}
          onClick={generateMetadata}
          type="button"
          variant="contained"
          disabled={Object.values(selectedMetadataTypes).every(
            (value) => value === false
          )} // Note: I tested my multiple API call by setting this to {false} directly.
        >
          Generate
        </Button>
      )}
    </>
  );
};

GenerateMetadataComponent.propTypes = {
  dataset: PropTypes.object.isRequired,
  targetType: PropTypes.string.isRequired,
  setTargetType: PropTypes.func.isRequired,
  targets: PropTypes.array.isRequired,
  setTargets: PropTypes.func.isRequired,
  targetOptions: PropTypes.array.isRequired,
  setTargetOptions: PropTypes.func.isRequired,
  selectedMetadataTypes: PropTypes.object.isRequired,
  setSelectedMetadataTypes: PropTypes.func.isRequired,
  currentView: PropTypes.string.isRequired,
  setCurrentView: PropTypes.func.isRequired,
  version: PropTypes.number.isRequired,
  setVersion: PropTypes.func.isRequired
};
