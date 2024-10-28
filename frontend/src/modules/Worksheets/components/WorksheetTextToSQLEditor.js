import { LoadingButton } from '@mui/lab';
import {
  Box,
  Card,
  CircularProgress,
  MenuItem,
  TextField,
  Autocomplete,
  Chip
} from '@mui/material';

import React, { useState } from 'react';
import { Scrollbar } from 'design';
import { SET_ERROR, useDispatch } from 'globalErrors';
import { useClient } from 'services';
import { textToSQL } from '../services';
import PropTypes from 'prop-types';

export const WorksheetTextToSQLEditor = ({
  handleEnvironmentChange,
  loadingEnvs,
  currentEnv,
  environmentOptions,
  worksheet,
  handleDatabaseChange,
  selectedDatabase,
  loadingDatabases,
  databaseOptions,
  loadingTables,
  tableOptions,
  handleSQLChange
}) => {
  const dispatch = useDispatch();
  const client = useClient();
  const [invoking, setInvoking] = useState(false);
  const [selectedTables, setSelectedTables] = useState([]);
  const [prompt, setPrompt] = useState('');

  const handleSubmit = async () => {
    setInvoking(true);
    handleSQLChange('');

    const response = await client.query(
      textToSQL({
        prompt: prompt,
        environmentUri: currentEnv.environmentUri,
        worksheetUri: worksheet.worksheetUri,
        databaseName: selectedDatabase.label,
        tableNames: selectedTables
      })
    );
    if (!response.errors) {
      handleSQLChange(response.data.textToSQL);
    } else {
      dispatch({ type: SET_ERROR, error: response.errors[0].message });
    }
    setInvoking(false);
  };

  function handlePromptChange(prompt) {
    setPrompt(prompt);
  }

  function handleTablesChange(newValue) {
    setSelectedTables(newValue);
    setPrompt('');
  }

  function handleDatabaseChanges(event) {
    setSelectedTables([]);
    setPrompt('');
    handleDatabaseChange(event);
  }

  return (
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
      <Scrollbar options={{ suppressScrollX: true }}>
        <Box sx={{ p: 2 }}>
          <Card>
            <Box sx={{ p: 2, mt: 2 }}>
              <TextField
                fullWidth
                label="Environment"
                name="environment"
                onChange={(event) => {
                  handleEnvironmentChange(event);
                }}
                select
                value={currentEnv}
                variant="outlined"
                InputProps={{
                  endAdornment: (
                    <>
                      {loadingEnvs ? (
                        <CircularProgress color="inherit" size={20} />
                      ) : null}
                    </>
                  )
                }}
              >
                {environmentOptions.map((environment) => (
                  <MenuItem
                    key={environment.environmentUri}
                    value={environment}
                  >
                    {environment.label}
                  </MenuItem>
                ))}
              </TextField>
            </Box>
            <Box sx={{ p: 2, mt: 2 }}>
              <TextField
                disabled
                fullWidth
                label="Team"
                name="team"
                value={worksheet ? worksheet.SamlAdminGroupName : ''}
                variant="outlined"
              />
            </Box>
            <Box sx={{ p: 2 }}>
              <TextField
                fullWidth
                label="Database"
                name="database"
                onChange={(event) => {
                  handleDatabaseChanges(event);
                }}
                select
                value={selectedDatabase}
                variant="outlined"
                InputProps={{
                  endAdornment: (
                    <>
                      {loadingDatabases ? (
                        <CircularProgress color="inherit" size={20} />
                      ) : null}
                    </>
                  )
                }}
              >
                {databaseOptions.length > 0 ? (
                  databaseOptions.map((database) => (
                    <MenuItem key={database.datasetUri} value={database}>
                      {database.label}
                    </MenuItem>
                  ))
                ) : (
                  <MenuItem disabled>No databases found</MenuItem>
                )}
              </TextField>
            </Box>

            <Box sx={{ p: 2 }}>
              <Autocomplete
                multiple
                options={tableOptions.map((t) => t.GlueTableName)}
                value={selectedTables}
                onChange={(_, newValue) => handleTablesChange(newValue)}
                renderInput={(params) => (
                  <>
                    {loadingTables ? (
                      <CircularProgress color="inherit" size={20} />
                    ) : (
                      <TextField
                        {...params}
                        variant="outlined"
                        label="Select Tables"
                        placeholder="Tables"
                      />
                    )}
                  </>
                )}
                renderTags={(value, getTagProps) =>
                  value.map((option, index) => (
                    <Chip
                      variant="outlined"
                      label={option}
                      {...getTagProps({ index })}
                    />
                  ))
                }
                disabled={!selectedDatabase}
                fullWidth
                margin="normal"
              />
            </Box>
            <Box sx={{ p: 2 }}>
              <TextField
                fullWidth
                label="Prompt"
                multiline
                rows={4}
                value={prompt}
                onChange={(e) => handlePromptChange(e.target.value)}
                variant="outlined"
              />
            </Box>
            <Box sx={{ p: 2 }}>
              <LoadingButton
                disabled={
                  !currentEnv ||
                  !selectedDatabase ||
                  !selectedTables.length ||
                  !prompt
                }
                loading={invoking}
                variant="contained"
                onClick={handleSubmit}
                fullWidth
              >
                Generate SQL
              </LoadingButton>
            </Box>
          </Card>
        </Box>
      </Scrollbar>
    </Box>
  );
};

WorksheetTextToSQLEditor.propTypes = {
  handleEnvironmentChange: PropTypes.func.isRequired,
  loadingEnvs: PropTypes.bool.isRequired,
  currentEnv: PropTypes.object.isRequired,
  environmentOptions: PropTypes.array.isRequired,
  worksheet: PropTypes.object.isRequired,
  handleDatabaseChange: PropTypes.func.isRequired,
  selectedDatabase: PropTypes.object.isRequired,
  loadingDatabases: PropTypes.bool.isRequired,
  databaseOptions: PropTypes.array.isRequired,
  handleTableChange: PropTypes.func.isRequired,
  loadingTables: PropTypes.bool.isRequired,
  tableOptions: PropTypes.array.isRequired
};
