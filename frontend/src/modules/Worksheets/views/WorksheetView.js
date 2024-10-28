import { PlayArrowOutlined } from '@mui/icons-material';
import { LoadingButton } from '@mui/lab';
import {
  Box,
  CircularProgress,
  Divider,
  IconButton,
  Typography,
  Tabs,
  Tab,
  Alert,
  Stack
} from '@mui/material';
import { useSnackbar } from 'notistack';
import React, { useCallback, useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { FaTrash } from 'react-icons/fa';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Defaults,
  DeleteObjectWithFrictionModal,
  PencilAltIcon,
  SaveIcon,
  useSettings
} from 'design';
import { SET_ERROR, useDispatch } from 'globalErrors';
import {
  listDatasetTables,
  getSharedDatasetTables,
  listDatasetTableColumns,
  listS3DatasetsOwnedByEnvGroup,
  listValidEnvironments,
  useClient
} from 'services';
import {
  deleteWorksheet,
  getWorksheet,
  listS3DatasetsSharedWithEnvGroup,
  listSharedDatasetTableColumns,
  runAthenaSqlQuery,
  updateWorksheet
} from '../services';
import {
  SQLQueryEditor,
  WorksheetEditFormModal,
  WorksheetResult,
  WorksheetTextToSQLEditor,
  WorksheetDocAnalyzer,
  WorksheetSQLEditor
} from '../components';
import { isFeatureEnabled } from 'utils';

const tabs = [
  {
    label: 'SQL Editor',
    value: 'SQLEditor',
    active: true
  },
  {
    label: 'Text-To-SQL Editor',
    value: 'TextToSQL',
    active: isFeatureEnabled('worksheets', 'nlq')
  },
  {
    label: 'Document Analyzer',
    value: 'DocAnalyzer',
    active: isFeatureEnabled('worksheets', 'nlq')
  }
];

const activeTabs = tabs.filter((tab) => tab.active !== false);

const WorksheetView = () => {
  const navigate = useNavigate();
  const params = useParams();
  const dispatch = useDispatch();
  const client = useClient();
  const { enqueueSnackbar } = useSnackbar();
  const [environmentOptions, setEnvironmentOptions] = useState([]);
  const [worksheet, setWorksheet] = useState({ worksheetUri: '' });
  const [results, setResults] = useState({ rows: [], fields: [] });
  const [loading, setLoading] = useState(true);
  const [sqlBody, setSqlBody] = useState(
    " select 'A' as dim, 23 as nb\n union \n select 'B' as dim, 43 as nb "
  );
  const [textBody, setTextBody] = useState('');
  const [currentEnv, setCurrentEnv] = useState();
  const [loadingEnvs, setLoadingEnvs] = useState(false);
  const [loadingDatabases, setLoadingDatabases] = useState(false);
  const [databaseOptions, setDatabaseOptions] = useState([]);
  const [selectedDatabase, setSelectedDatabase] = useState(null);
  const [selectedTable, setSelectedTable] = useState(null);
  const [columns, setColumns] = useState(null);
  const [loadingColumns, setLoadingColumns] = useState(false);
  const [tableOptions, setTableOptions] = useState([]);
  const [loadingTables, setLoadingTables] = useState(false);
  const [runningQuery, setRunningQuery] = useState(false);
  const [isEditWorksheetOpen, setIsEditWorksheetOpen] = useState(null);
  const [isDeleteWorksheetOpen, setIsDeleteWorksheetOpen] = useState(null);
  const [currentTab, setCurrentTab] = useState(activeTabs[0].value);
  const { settings } = useSettings();

  const handleTabChange = (event, newValue) => {
    setCurrentTab(newValue);
  };

  const handleEditWorksheetModalOpen = () => {
    setIsEditWorksheetOpen(true);
  };
  const handleEditWorksheetModalClose = () => {
    setIsEditWorksheetOpen(false);
  };
  const handleDeleteWorksheetModalOpen = () => {
    setIsDeleteWorksheetOpen(true);
  };
  const handleDeleteWorksheetModalClose = () => {
    setIsDeleteWorksheetOpen(false);
  };

  const fetchEnvironments = useCallback(
    async (group) => {
      setLoadingEnvs(true);
      const response = await client.query(
        listValidEnvironments({
          filter: {
            ...Defaults.selectListFilter,
            SamlGroupName: group
          }
        })
      );
      if (!response.errors) {
        setEnvironmentOptions(
          response.data.listValidEnvironments.nodes.map((e) => ({
            ...e,
            value: e.environmentUri,
            label: e.label
          }))
        );
      } else {
        dispatch({ type: SET_ERROR, error: response.errors[0].message });
      }
      setLoadingEnvs(false);
    },
    [client, dispatch]
  );

  const fetchDatabases = useCallback(
    async (environment, team) => {
      setLoadingDatabases(true);
      let ownedDatabases = [];
      let sharedWithDatabases = [];
      let response = await client.query(
        listS3DatasetsOwnedByEnvGroup({
          filter: Defaults.selectListFilter,
          environmentUri: environment.environmentUri,
          groupUri: team
        })
      );
      if (response.errors) {
        dispatch({ type: SET_ERROR, error: response.errors[0].message });
      }
      if (response.data.listS3DatasetsOwnedByEnvGroup.nodes) {
        ownedDatabases = response.data.listS3DatasetsOwnedByEnvGroup.nodes?.map(
          (d) => ({
            ...d,
            value: d.datasetUri,
            label: d.GlueDatabaseName,
            bucketName: d.S3BucketName
          })
        );
      }
      response = await client.query(
        listS3DatasetsSharedWithEnvGroup({
          environmentUri: environment.environmentUri,
          groupUri: team
        })
      );
      if (response.errors) {
        dispatch({ type: SET_ERROR, error: response.errors[0].message });
      }
      if (response.data.listS3DatasetsSharedWithEnvGroup) {
        sharedWithDatabases =
          response.data.listS3DatasetsSharedWithEnvGroup?.map((d) => ({
            value: d.datasetUri,
            label: d.sharedGlueDatabaseName,
            shareUri: d.shareUri
          }));
      }
      setDatabaseOptions(ownedDatabases.concat(sharedWithDatabases));
      setLoadingDatabases(false);
    },
    [client, dispatch]
  );
  const fetchTables = useCallback(
    async (environment, dataset) => {
      setLoadingTables(true);
      let response = '';
      if (dataset.label.includes(dataset.value + '_shared')) {
        response = await client.query(
          getSharedDatasetTables({
            datasetUri: dataset.value,
            envUri: environment.environmentUri
          })
        );
      } else {
        response = await client.query(
          listDatasetTables({
            datasetUri: dataset.value,
            filter: Defaults.selectListFilter
          })
        );
      }

      if (
        !response.errors &&
        dataset.label.includes(dataset.value + '_shared')
      ) {
        setTableOptions(
          response.data.getSharedDatasetTables.map((t) => ({
            ...t,
            value: t.tableUri,
            label: t.GlueTableName
          }))
        );
      } else if (!response.errors) {
        setTableOptions(
          response.data.getDataset.tables.nodes.map((t) => ({
            ...t,
            value: t.tableUri,
            label: t.GlueTableName
          }))
        );
      } else {
        dispatch({ type: SET_ERROR, error: response.errors[0].message });
      }
      setLoadingTables(false);
    },
    [client, dispatch]
  );
  const fetchColumns = useCallback(
    async (table, database) => {
      setLoadingColumns(true);
      let response;
      if (database?.shareUri) {
        response = await client.query(
          listSharedDatasetTableColumns({
            tableUri: table.tableUri,
            shareUri: database.shareUri,
            filter: Defaults.selectListFilter
          })
        );
      } else {
        response = await client.query(
          listDatasetTableColumns({
            tableUri: table.tableUri,
            filter: Defaults.selectListFilter
          })
        );
      }

      if (!response.errors) {
        if (database?.shareUri) {
          setColumns(
            response.data.listSharedDatasetTableColumns.nodes.map((c) => ({
              ...c,
              value: c.columnUri,
              label: c.name
            }))
          );
        } else {
          setColumns(
            response.data.listDatasetTableColumns.nodes.map((c) => ({
              ...c,
              value: c.columnUri,
              label: c.name
            }))
          );
        }
      } else {
        dispatch({ type: SET_ERROR, error: response.errors[0].message });
      }
      setLoadingColumns(false);
    },
    [client, dispatch]
  );
  const saveWorksheet = useCallback(async () => {
    const response = await client.mutate(
      updateWorksheet({
        worksheetUri: worksheet.worksheetUri,
        input: {
          label: worksheet.label,
          sqlBody,
          description: worksheet.description,
          tags: worksheet.tags
        }
      })
    );
    if (!response.errors) {
      enqueueSnackbar('Worksheet saved', {
        anchorOrigin: {
          horizontal: 'right',
          vertical: 'top'
        },
        variant: 'success'
      });
    } else {
      dispatch({ type: SET_ERROR, error: response.errors[0].message });
    }
  }, [client, dispatch, enqueueSnackbar, worksheet, sqlBody]);

  const runQuery = useCallback(async () => {
    try {
      setRunningQuery(true);
      const response = await client.query(
        runAthenaSqlQuery({
          sqlQuery: sqlBody,
          environmentUri: currentEnv.environmentUri,
          worksheetUri: worksheet.worksheetUri
        })
      );
      if (!response.errors) {
        const athenaResults = response.data.runAthenaSqlQuery;
        setResults({
          rows: athenaResults.rows.map((c, index) => ({ ...c, id: index })),
          columns: athenaResults.columns.map((c, index) => ({
            ...c,
            id: index
          }))
        });
      } else {
        dispatch({ type: SET_ERROR, error: response.errors[0].message });
      }
    } catch (e) {
      dispatch({ type: SET_ERROR, error: e.message });
    } finally {
      setRunningQuery(false);
    }
  }, [client, dispatch, currentEnv, sqlBody]);

  const deleteWorksheetfunction = useCallback(async () => {
    const response = await client.mutate(
      deleteWorksheet(worksheet.worksheetUri)
    );
    if (!response.errors) {
      enqueueSnackbar('Worksheet deleted', {
        anchorOrigin: {
          horizontal: 'right',
          vertical: 'top'
        },
        variant: 'success'
      });
      navigate('/console/worksheets');
    } else {
      dispatch({ type: SET_ERROR, error: response.errors[0].message });
    }
  }, [client, dispatch, enqueueSnackbar, navigate, worksheet]);

  const fetchWorksheet = useCallback(async () => {
    setLoading(true);
    const response = await client.query(getWorksheet(params.uri));
    if (!response.errors) {
      setWorksheet(response.data.getWorksheet);
      setSqlBody(response.data.getWorksheet.sqlBody);
      setResults(response.data.getWorksheet.lastSavedQueryResult);
      fetchEnvironments(response.data.getWorksheet.SamlAdminGroupName).catch(
        (e) => dispatch({ type: SET_ERROR, error: e.message })
      );
    } else {
      dispatch({ type: SET_ERROR, error: response.errors[0].message });
    }
    setLoading(false);
  }, [client, params.uri, fetchEnvironments, dispatch]);

  useEffect(() => {
    if (client) {
      fetchWorksheet().catch((e) =>
        dispatch({ type: SET_ERROR, error: e.message })
      );
    }
  }, [client, dispatch]);

  function handleEnvironmentChange(event) {
    setColumns([]);
    setSelectedDatabase('');
    setSelectedTable('');
    setDatabaseOptions([]);
    setTableOptions([]);
    setCurrentEnv(event.target.value);
    fetchDatabases(event.target.value, worksheet.SamlAdminGroupName).catch(
      (e) => dispatch({ type: SET_ERROR, error: e.message })
    );
  }

  function handleSQLChange(value) {
    setSqlBody(value);
  }

  function handleTextChange(value) {
    setTextBody(value);
  }

  function handleDatabaseChange(event) {
    setColumns([]);
    setTableOptions([]);
    setSelectedTable('');
    setSelectedDatabase(event.target.value);
    fetchTables(currentEnv, event.target.value).catch((e) =>
      dispatch({ type: SET_ERROR, error: e.message })
    );
  }

  function handleTableChange(event) {
    setColumns([]);
    setSelectedTable(event.target.value);
    fetchColumns(event.target.value, selectedDatabase).catch((e) =>
      dispatch({ type: SET_ERROR, error: e.message })
    );
    setSqlBody(
      `SELECT * FROM "${selectedDatabase.label}"."${event.target.value.GlueTableName}" limit 10;`
    );
  }

  if (loading) {
    return <CircularProgress />;
  }

  return (
    <>
      <Helmet>
        <title>Worksheet | data.all</title>
      </Helmet>
      <Tabs
        indicatorColor="primary"
        scrollButtons="auto"
        textColor="primary"
        value={currentTab}
        variant="fullWidth"
        onChange={handleTabChange}
      >
        {activeTabs.map((tab) => (
          <Tab
            key={tab.value}
            label={tab.label}
            value={tab.value}
            icon={settings.tabIcons ? tab.icon : null}
            iconPosition="start"
          />
        ))}
      </Tabs>
      <Box
        sx={{
          backgroundColor: 'background.default',
          display: 'flex',
          height: '100%'
        }}
      >
        <Box
          sx={{
            display: 'flex',
            backgroundColor: 'background.paper',
            borderRight: 1,
            borderBottom: 1,
            borderColor: 'divider',
            flexDirection: 'column',
            maxWidth: '100%',
            width: 350,
            height: '100%'
          }}
        >
          {currentTab === 'SQLEditor' && (
            <WorksheetSQLEditor
              handleEnvironmentChange={handleEnvironmentChange}
              loadingEnvs={loadingEnvs}
              environmentOptions={environmentOptions}
              currentEnv={currentEnv}
              worksheet={worksheet}
              handleDatabaseChange={handleDatabaseChange}
              selectedDatabase={selectedDatabase}
              loadingDatabases={loadingDatabases}
              databaseOptions={databaseOptions}
              handleTableChange={handleTableChange}
              selectedTable={selectedTable}
              loadingTables={loadingTables}
              tableOptions={tableOptions}
              loadingColumns={loadingColumns}
              columns={columns}
            />
          )}
          {currentTab === 'TextToSQL' && (
            <WorksheetTextToSQLEditor
              handleEnvironmentChange={handleEnvironmentChange}
              loadingEnvs={loadingEnvs}
              environmentOptions={environmentOptions}
              currentEnv={currentEnv}
              worksheet={worksheet}
              handleDatabaseChange={handleDatabaseChange}
              selectedDatabase={selectedDatabase}
              loadingDatabases={loadingDatabases}
              databaseOptions={databaseOptions}
              loadingTables={loadingTables}
              tableOptions={tableOptions}
              handleSQLChange={handleSQLChange}
            />
          )}
          {currentTab === 'DocAnalyzer' && (
            <WorksheetDocAnalyzer
              handleEnvironmentChange={handleEnvironmentChange}
              loadingEnvs={loadingEnvs}
              environmentOptions={environmentOptions}
              currentEnv={currentEnv}
              worksheet={worksheet}
              selectedDatabase={selectedDatabase}
              loadingDatabases={loadingDatabases}
              databaseOptions={databaseOptions}
              handleTextChange={handleTextChange}
              setSelectedDatabase={setSelectedDatabase}
            />
          )}
        </Box>
        <Box
          sx={{
            backgroundColor: 'background.default',
            display: 'flex',
            flexDirection: 'column',
            flexGrow: 1
          }}
        >
          <Stack direction="column">
            <Box
              sx={{
                alignItems: 'center',
                backgroundColor: 'background.paper',
                display: 'flex',
                flexShrink: 0,
                height: 48,
                p: 1
              }}
            >
              <Box>
                <Typography color="textPrimary" variant="h5">
                  {worksheet.label}
                </Typography>
              </Box>
              <Box sx={{ flexGrow: 1 }} />
              {currentTab !== 'DocAnalyzer' && (
                <IconButton onClick={saveWorksheet}>
                  <SaveIcon fontSize="small" />
                </IconButton>
              )}
              <IconButton onClick={handleEditWorksheetModalOpen}>
                <PencilAltIcon fontSize="small" />
              </IconButton>
              <IconButton onClick={handleDeleteWorksheetModalOpen}>
                <FaTrash size={16} />
              </IconButton>
              <Divider />
            </Box>
          </Stack>
          {currentTab !== 'SQLEditor' && (
            <Box
              sx={{
                backgroundColor: 'background.paper',
                display: 'flex',
                height: 68,
                p: 1
              }}
            >
              <Typography color="warning.dark" style={{ fontStyle: 'italic' }}>
                <Alert
                  severity="warning"
                  sx={{ xs: '0.7rem', sm: '0.8rem', md: '0.9rem' }}
                >
                  Experimental Feature: Carefully review this AI-generated
                  response for accuracy
                </Alert>
              </Typography>
            </Box>
          )}
          {currentTab !== 'DocAnalyzer' ? (
            <>
              <Divider />
              <Box sx={{ p: 2 }}>
                <SQLQueryEditor sql={sqlBody} setSqlBody={setSqlBody} />
              </Box>
              <Divider />
              <Box
                sx={{
                  alignItems: 'center',
                  backgroundColor: 'background.paper',
                  display: 'flex',
                  flexShrink: 0,
                  height: 68,
                  p: 2
                }}
              >
                <LoadingButton
                  disabled={!currentEnv?.value}
                  loading={runningQuery}
                  color="primary"
                  onClick={runQuery}
                  startIcon={<PlayArrowOutlined fontSize="small" />}
                  sx={{ m: 1 }}
                  variant="contained"
                >
                  Run Query
                </LoadingButton>
              </Box>
              <Divider />
              <Box sx={{ p: 2 }}>
                <WorksheetResult results={results} loading={runningQuery} />
              </Box>
            </>
          ) : (
            <Box sx={{ p: 2 }}>
              <SQLQueryEditor
                sql={textBody}
                setSqlBody={setTextBody}
                height="38rem"
                language="plaintext"
              />
            </Box>
          )}
        </Box>
      </Box>
      {worksheet && isEditWorksheetOpen && (
        <WorksheetEditFormModal
          worksheet={worksheet}
          onApply={handleEditWorksheetModalClose}
          onClose={handleEditWorksheetModalClose}
          reload={fetchWorksheet}
          open={isEditWorksheetOpen}
        />
      )}
      {worksheet && isDeleteWorksheetOpen && (
        <DeleteObjectWithFrictionModal
          objectName={worksheet.label}
          onApply={handleDeleteWorksheetModalClose}
          onClose={handleDeleteWorksheetModalClose}
          open={isDeleteWorksheetOpen}
          deleteFunction={deleteWorksheetfunction}
          isAWSResource={false}
        />
      )}
    </>
  );
};

export default WorksheetView;
