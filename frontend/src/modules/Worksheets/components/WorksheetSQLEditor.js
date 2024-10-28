import {
  Box,
  Card,
  CircularProgress,
  List,
  ListItem,
  ListItemIcon,
  MenuItem,
  TextField,
  Tooltip,
  Typography
} from '@mui/material';
import PropTypes from 'prop-types';
import React from 'react';
import { CgHashtag } from 'react-icons/cg';
import { VscSymbolString } from 'react-icons/vsc';
import { Scrollbar } from 'design';

export const WorksheetSQLEditor = ({
  handleEnvironmentChange,
  loadingEnvs,
  currentEnv,
  environmentOptions,
  worksheet,
  handleDatabaseChange,
  selectedDatabase,
  loadingDatabases,
  databaseOptions,
  handleTableChange,
  selectedTable,
  loadingTables,
  tableOptions,
  loadingColumns,
  columns
}) => {
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
                  handleDatabaseChange(event);
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
              <TextField
                fullWidth
                label="Table"
                name="table"
                onChange={(event) => {
                  handleTableChange(event);
                }}
                select
                value={selectedTable}
                variant="outlined"
                InputProps={{
                  endAdornment: (
                    <>
                      {loadingTables ? (
                        <CircularProgress color="inherit" size={20} />
                      ) : null}
                    </>
                  )
                }}
              >
                {tableOptions.length > 0 ? (
                  tableOptions.map((table) => (
                    <MenuItem key={table.tableUri} value={table}>
                      {table.GlueTableName}
                    </MenuItem>
                  ))
                ) : (
                  <MenuItem disabled>No tables found</MenuItem>
                )}
              </TextField>
            </Box>
            {loadingColumns ? (
              <CircularProgress size={15} />
            ) : (
              <Box sx={{ p: 2 }}>
                {columns && columns.length > 0 && (
                  <Box>
                    <Typography color="textSecondary" variant="subtitle2">
                      Columns
                    </Typography>
                    <List dense>
                      {columns.map((col) => (
                        <Box>
                          <ListItem key={col.columnUri}>
                            {col.typeName !== 'string' ? (
                              <ListItemIcon>
                                <CgHashtag />
                              </ListItemIcon>
                            ) : (
                              <ListItemIcon>
                                <VscSymbolString />
                              </ListItemIcon>
                            )}
                            <Typography
                              sx={{
                                width: '200px',
                                whiteSpace: 'nowrap',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                WebkitBoxOrient: 'vertical',
                                WebkitLineClamp: 2
                              }}
                            >
                              <Tooltip title={col.name}>
                                <Typography
                                  color="textPrimary"
                                  variant="subtitle2"
                                >
                                  {col.name.substring(0, 22)}
                                </Typography>
                              </Tooltip>
                            </Typography>
                          </ListItem>
                        </Box>
                      ))}
                    </List>
                  </Box>
                )}
              </Box>
            )}
          </Card>
        </Box>
      </Scrollbar>
    </Box>
  );
};

WorksheetSQLEditor.propTypes = {
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
  selectedTable: PropTypes.object.isRequired,
  loadingTables: PropTypes.bool.isRequired,
  tableOptions: PropTypes.array.isRequired,
  loadingColumns: PropTypes.bool.isRequired,
  columns: PropTypes.array.isRequired
};
