import {
  CopyAllOutlined,
  GroupAddOutlined,
  SupervisedUserCircleRounded
} from '@mui/icons-material';
import { LoadingButton } from '@mui/lab';
import {
  Box,
  Button,
  Card,
  CardHeader,
  Chip,
  Divider,
  Grid,
  InputAdornment,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/DeleteOutlined';
import SaveIcon from '@mui/icons-material/Save';
import CancelIcon from '@mui/icons-material/Close';
import CircularProgress from '@mui/material/CircularProgress';
import { useTheme } from '@mui/styles';
import { useSnackbar } from 'notistack';
import PropTypes from 'prop-types';
import React, { useCallback, useEffect, useState } from 'react';
import * as FaIcons from 'react-icons/fa';
import { HiUserRemove } from 'react-icons/hi';
import { VscChecklist } from 'react-icons/vsc';
import {
  Defaults,
  DeleteObjectWithFrictionModal,
  Label,
  Pager,
  RefreshTableMenu,
  Scrollbar,
  SearchIcon,
  UserModal
} from 'design';
import { SET_ERROR, useDispatch } from 'globalErrors';
import { isFeatureEnabled } from 'utils';
import {
  getConsumptionRolePolicies,
  useClient,
  useFetchGroups
} from 'services';
import {
  generateEnvironmentAccessToken,
  getEnvironmentAssumeRoleUrl,
  listAllEnvironmentConsumptionRoles,
  listAllEnvironmentGroups,
  removeConsumptionRoleFromEnvironment,
  removeGroupFromEnvironment,
  updateConsumptionRole
} from '../services';
import { EnvironmentRoleAddForm } from './EnvironmentRoleAddForm';
import { EnvironmentTeamInviteEditForm } from './EnvironmentTeamInviteEditForm';
import { EnvironmentTeamInviteForm } from './EnvironmentTeamInviteForm';
import { DataGrid, GridActionsCellItem, GridRowModes } from '@mui/x-data-grid';

function TeamRow({
  team,
  environment,
  fetchItems,
  handleDeleteTeamModalOpen,
  handleDeleteTeamModalClose,
  handleTeamEditModalOpen,
  handleTeamEditModalClose,
  isDeleteTeamModalOpenId,
  isTeamEditModalOpenId
}) {
  const client = useClient();
  const dispatch = useDispatch();
  const theme = useTheme();
  const { enqueueSnackbar } = useSnackbar();
  const [accessingConsole, setAccessingConsole] = useState(false);
  const [loadingCreds, setLoadingCreds] = useState(false);

  const [openUserModal, setIsModalOpen] = useState(false);
  const [selectedTeam, setSelectedTeam] = useState(null);

  const handleOpenModal = (team) => {
    setSelectedTeam(team.groupUri);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedTeam(null);
  };

  const removeGroup = async (groupUri) => {
    try {
      const response = await client.mutate(
        removeGroupFromEnvironment({
          environmentUri: environment.environmentUri,
          groupUri
        })
      );
      if (!response.errors) {
        enqueueSnackbar('Team removed from environment', {
          anchorOrigin: {
            horizontal: 'right',
            vertical: 'top'
          },
          variant: 'success'
        });
        if (handleDeleteTeamModalClose) {
          handleDeleteTeamModalClose();
        }
        if (fetchItems) {
          fetchItems();
        }
      } else {
        dispatch({ type: SET_ERROR, error: response.errors[0].message });
      }
    } catch (e) {
      dispatch({ type: SET_ERROR, error: e.message });
    }
  };

  const getConsoleLink = async (groupUri) => {
    setAccessingConsole(true);
    const response = await client.query(
      getEnvironmentAssumeRoleUrl({
        environmentUri: environment.environmentUri,
        groupUri
      })
    );
    if (!response.errors) {
      window.open(response.data.getEnvironmentAssumeRoleUrl, '_blank');
    } else {
      dispatch({ type: SET_ERROR, error: response.errors[0].message });
    }
    setAccessingConsole(false);
  };

  const generateCredentials = async (groupUri) => {
    setLoadingCreds(true);
    const response = await client.query(
      generateEnvironmentAccessToken({
        environmentUri: environment.environmentUri,
        groupUri
      })
    );
    if (!response.errors) {
      await navigator.clipboard.writeText(
        response.data.generateEnvironmentAccessToken
      );
      enqueueSnackbar('Credentials copied to clipboard', {
        anchorOrigin: {
          horizontal: 'right',
          vertical: 'top'
        },
        variant: 'success'
      });
    } else {
      dispatch({ type: SET_ERROR, error: response.errors[0].message });
    }
    setLoadingCreds(false);
  };
  return (
    <TableRow hover>
      <TableCell
        onClick={() => handleOpenModal(team)}
        style={{ cursor: 'pointer' }}
      >
        {team.groupUri}{' '}
        {team.groupUri === environment.SamlGroupName && (
          <Label color="primary">Admins</Label>
        )}
      </TableCell>

      {openUserModal && (
        <UserModal
          team={selectedTeam}
          open={openUserModal}
          onClose={handleCloseModal}
        />
      )}

      <TableCell>{team.environmentIAMRoleArn}</TableCell>
      <TableCell>{team.environmentAthenaWorkGroup}</TableCell>
      <TableCell>
        {team.groupUri !== environment.SamlGroupName ? (
          <LoadingButton onClick={() => handleTeamEditModalOpen(team.groupUri)}>
            <VscChecklist
              size={20}
              color={
                theme.palette.mode === 'dark'
                  ? theme.palette.primary.contrastText
                  : theme.palette.primary.main
              }
            />
          </LoadingButton>
        ) : (
          <Chip
            size="small"
            sx={{ ml: 1.5 }}
            key="ALL"
            label="ALL"
            variant="outlined"
          />
        )}
        {isTeamEditModalOpenId === team.groupUri && (
          <EnvironmentTeamInviteEditForm
            environment={environment}
            team={team}
            open={isTeamEditModalOpenId === team.groupUri}
            reloadTeams={fetchItems}
            onClose={() => handleTeamEditModalClose()}
          />
        )}
      </TableCell>

      <TableCell>
        <Box>
          {isFeatureEnabled('core', 'env_aws_actions') && (
            <>
              <LoadingButton
                loading={accessingConsole}
                onClick={() => getConsoleLink(team.groupUri)}
              >
                <FaIcons.FaAws
                  size={25}
                  color={
                    theme.palette.mode === 'dark'
                      ? theme.palette.primary.contrastText
                      : theme.palette.primary.main
                  }
                />
              </LoadingButton>
              <LoadingButton
                loading={loadingCreds}
                onClick={() => generateCredentials(team.groupUri)}
              >
                <CopyAllOutlined
                  sx={{
                    color:
                      theme.palette.mode === 'dark'
                        ? theme.palette.primary.contrastText
                        : theme.palette.primary.main
                  }}
                />
              </LoadingButton>
            </>
          )}
          {team.groupUri !== environment.SamlGroupName && (
            <LoadingButton
              onClick={() => handleDeleteTeamModalOpen(team.groupUri)}
            >
              <HiUserRemove
                size={25}
                color={
                  theme.palette.mode === 'dark'
                    ? theme.palette.primary.contrastText
                    : theme.palette.primary.main
                }
              />
            </LoadingButton>
          )}
          {team.groupUri !== environment.SamlGroupName && (
            <DeleteObjectWithFrictionModal
              objectName={team.groupUri}
              onApply={() => handleDeleteTeamModalClose()}
              onClose={() => handleDeleteTeamModalClose()}
              open={isDeleteTeamModalOpenId === team.groupUri}
              isAWSResource={false}
              deleteFunction={() => removeGroup(team.groupUri)}
            />
          )}
        </Box>
      </TableCell>
    </TableRow>
  );
}

TeamRow.propTypes = {
  team: PropTypes.any,
  environment: PropTypes.any,
  fetchItems: PropTypes.any,
  handleDeleteTeamModalOpen: PropTypes.any,
  handleDeleteTeamModalClose: PropTypes.any,
  handleTeamEditModalOpen: PropTypes.any,
  handleTemaEditModalClose: PropTypes.any,
  isDeleteTeamModalOpenId: PropTypes.string,
  isTeamEditModalOpenId: PropTypes.string
};

export const IAMRolePolicyDataGridCell = ({ environmentUri, IAMRoleName }) => {
  const [isLoading, setLoading] = useState(true);
  const [managedPolicyDetails, setManagedPolicyDetails] = useState(null);
  const dispatch = useDispatch();
  const { enqueueSnackbar } = useSnackbar();
  const client = useClient();

  useEffect(() => {
    if (client) {
      getRolePolicies().catch((e) =>
        dispatch({ type: SET_ERROR, error: e.message })
      );
    }
  }, [client, dispatch, enqueueSnackbar]);

  const getRolePolicies = async () => {
    setLoading(true);
    try {
      const response = await client.query(
        getConsumptionRolePolicies({
          environmentUri: environmentUri,
          IAMRoleName: IAMRoleName
        })
      );
      if (!response.errors) {
        setManagedPolicyDetails(response.data.getConsumptionRolePolicies);
      } else {
        dispatch({ type: SET_ERROR, error: response.errors[0].message });
      }
    } catch (e) {
      dispatch({ type: SET_ERROR, error: e.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      {isLoading ? (
        <CircularProgress size={30} />
      ) : (
        <Box>
          <Label
            sx={{ ml: 5 }}
            color={
              managedPolicyDetails
                .map((policy) => policy.attached)
                .includes(false)
                ? 'error'
                : 'success'
            }
          >
            {managedPolicyDetails
              .map((policy) => policy.attached)
              .includes(false)
              ? 'Not Attached'
              : 'Attached'}
          </Label>
          <LoadingButton
            onClick={async () => {
              await navigator.clipboard.writeText(
                managedPolicyDetails.map((policy) => policy.policy_name)
              );
              enqueueSnackbar('Policy Name is copied to clipboard', {
                anchorOrigin: {
                  horizontal: 'right',
                  vertical: 'top'
                },
                variant: 'success'
              });
            }}
          >
            <CopyAllOutlined />
          </LoadingButton>
        </Box>
      )}
    </Box>
  );
};

IAMRolePolicyDataGridCell.propTypes = {
  environmentUri: PropTypes.any,
  IAMRoleName: PropTypes.any
};

export const EnvironmentTeams = ({ environment }) => {
  const client = useClient();
  const dispatch = useDispatch();
  const { enqueueSnackbar } = useSnackbar();
  const [items, setItems] = useState(Defaults.pagedResponse);
  const [roles, setRoles] = useState(Defaults.pagedResponse);
  const [filter, setFilter] = useState(Defaults.filter);
  const [filterRoles, setFilterRoles] = useState(Defaults.filter);
  const [loading, setLoading] = useState(true);
  const [loadingRoles, setLoadingRoles] = useState(true);
  const [inputValue, setInputValue] = useState('');
  const [inputValueRoles, setInputValueRoles] = useState('');
  const [isTeamInviteModalOpen, setIsTeamInviteModalOpen] = useState(false);
  const [isAddRoleModalOpen, setIsAddRoleModalOpen] = useState(false);
  const [isDeleteRoleModalOpenId, setIsDeleteRoleModalOpen] = useState(0);
  const [isTeamEditModalOpenId, setIsTeamEditModalOpen] = useState('');
  const [isDeleteTeamModalOpenId, setIsDeleteTeamModalOpen] = useState('');

  const handleDeleteTeamModalOpen = (groupUri) => {
    setIsDeleteTeamModalOpen(groupUri);
  };

  const handleDeleteTeamModalClose = () => {
    setIsDeleteTeamModalOpen('');
  };

  const handleTeamEditModalOpen = (groupUri) => {
    setIsTeamEditModalOpen(groupUri);
  };

  const handleTeamEditModalClose = () => {
    setIsTeamEditModalOpen('');
  };

  const handleDeleteRoleModalOpen = (id) => {
    setIsDeleteRoleModalOpen(id);
  };
  const handleDeleteRoleModalClosed = (id) => {
    setIsDeleteRoleModalOpen(0);
  };

  const handleTeamInviteModalOpen = () => {
    setIsTeamInviteModalOpen(true);
  };
  const handleTeamInviteModalClose = () => {
    setIsTeamInviteModalOpen(false);
  };
  const handleAddRoleModalOpen = () => {
    setIsAddRoleModalOpen(true);
  };
  const handleAddRoleModalClose = () => {
    setIsAddRoleModalOpen(false);
  };

  const fetchItems = useCallback(async () => {
    setLoading(true);
    try {
      const response = await client.query(
        listAllEnvironmentGroups({
          environmentUri: environment.environmentUri,
          filter: filter
        })
      );
      if (!response.errors) {
        setItems({ ...response.data.listAllEnvironmentGroups });
      } else {
        dispatch({ type: SET_ERROR, error: response.errors[0].message });
      }
    } catch (e) {
      dispatch({ type: SET_ERROR, error: e.message });
    } finally {
      setLoading(false);
    }
  }, [client, dispatch, environment, filter]);

  const fetchRoles = useCallback(async () => {
    try {
      setLoadingRoles(true);
      const response = await client.query(
        listAllEnvironmentConsumptionRoles({
          environmentUri: environment.environmentUri,
          filter: filterRoles
        })
      );
      if (!response.errors) {
        setRoles({ ...response.data.listAllEnvironmentConsumptionRoles });
      } else {
        dispatch({ type: SET_ERROR, error: response.errors[0].message });
      }
    } catch (e) {
      dispatch({ type: SET_ERROR, error: e.message });
    } finally {
      setLoadingRoles(false);
    }
  }, [client, dispatch, environment, filterRoles]);

  const removeConsumptionRole = async (consumptionGroupUri) => {
    try {
      const response = await client.mutate(
        removeConsumptionRoleFromEnvironment({
          environmentUri: environment.environmentUri,
          consumptionRoleUri: consumptionGroupUri
        })
      );
      if (!response.errors) {
        enqueueSnackbar('Consumption Role removed from environment', {
          anchorOrigin: {
            horizontal: 'right',
            vertical: 'top'
          },
          variant: 'success'
        });
        fetchRoles();
      } else {
        dispatch({ type: SET_ERROR, error: response.errors[0].message });
      }
    } catch (e) {
      dispatch({ type: SET_ERROR, error: e.message });
    }
  };

  const updateConsumptionRoleHandler = async (newRow) => {
    const response = await client.mutate(
      updateConsumptionRole({
        environmentUri: environment.environmentUri,
        consumptionRoleUri: newRow.consumptionRoleUri,
        input: {
          groupUri: newRow.groupUri,
          consumptionRoleName: newRow.consumptionRoleName
        }
      })
    );
    if (!response.errors) {
      enqueueSnackbar('Consumption Role was updated', {
        anchorOrigin: {
          horizontal: 'right',
          vertical: 'top'
        },
        variant: 'success'
      });
      fetchRoles();
    } else {
      throw new Error(response.errors[0].message);
    }
  };

  useEffect(() => {
    if (client) {
      fetchItems().catch((e) =>
        dispatch({ type: SET_ERROR, error: e.message })
      );
      fetchRoles().catch((e) =>
        dispatch({ type: SET_ERROR, error: e.message })
      );
    }
  }, [client, filter.page, filterRoles.page, fetchItems, fetchRoles, dispatch]);

  const handleInputChange = (event) => {
    setInputValue(event.target.value);
    setFilter({ ...filter, term: event.target.value });
  };

  const handleInputKeyup = (event) => {
    if (event.code === 'Enter') {
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

  const handleInputChangeRoles = (event) => {
    setInputValueRoles(event.target.value);
    setFilterRoles({ ...filterRoles, term: event.target.value });
  };

  const handleInputKeyupRoles = (event) => {
    if (event.code === 'Enter') {
      fetchRoles().catch((e) =>
        dispatch({ type: SET_ERROR, error: e.message })
      );
    }
  };

  const handlePageChangeRoles = async (page) => {
    page += 1; //expecting 1-indexing
    if (page <= roles.pages && page !== roles.page) {
      await setFilterRoles({ ...filterRoles, page: page });
    }
  };

  const [rowModesModel, setRowModesModel] = useState({});

  const handleRowEditStart = (params, event) => {
    event.defaultMuiPrevented = true;
  };

  const handleRowEditStop = (params, event) => {
    event.defaultMuiPrevented = true;
  };

  const handleEditClick = (id) => () => {
    setRowModesModel({ ...rowModesModel, [id]: { mode: GridRowModes.Edit } });
  };

  const handleSaveClick = (id) => () => {
    setRowModesModel({ ...rowModesModel, [id]: { mode: GridRowModes.View } });
  };

  const handleCancelClick = (id) => () => {
    setRowModesModel({
      ...rowModesModel,
      [id]: { mode: GridRowModes.View, ignoreModifications: true }
    });
  };

  const processRowUpdate = async (newRow) => {
    await updateConsumptionRoleHandler(newRow);
    return newRow;
  };

  let { groupOptions } = useFetchGroups(environment);

  return (
    <Box>
      <Box>
        <Card>
          <CardHeader
            action={<RefreshTableMenu refresh={fetchItems} />}
            title={
              <Box>
                <SupervisedUserCircleRounded style={{ marginRight: '10px' }} />{' '}
                Environment Teams
              </Box>
            }
          />
          <Divider />
          <Box
            sx={{
              alignItems: 'center',
              display: 'flex',
              flexWrap: 'wrap',
              m: -1,
              p: 2
            }}
          >
            <Grid item md={10} sm={6} xs={12}>
              <Box
                sx={{
                  m: 1,
                  maxWidth: '100%',
                  width: 500
                }}
              >
                <TextField
                  fullWidth
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <SearchIcon fontSize="small" />
                      </InputAdornment>
                    )
                  }}
                  onChange={handleInputChange}
                  onKeyUp={handleInputKeyup}
                  placeholder="Search"
                  value={inputValue}
                  variant="outlined"
                />
              </Box>
            </Grid>
            <Grid item md={2} sm={6} xs={12}>
              <Button
                color="primary"
                startIcon={<GroupAddOutlined fontSize="small" />}
                sx={{ m: 1 }}
                onClick={handleTeamInviteModalOpen}
                variant="contained"
              >
                Invite
              </Button>
              {isTeamInviteModalOpen && (
                <EnvironmentTeamInviteForm
                  environment={environment}
                  open
                  reloadTeams={fetchItems}
                  onClose={handleTeamInviteModalClose}
                />
              )}
            </Grid>
          </Box>
          <Scrollbar>
            <Box sx={{ minWidth: 600 }}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Name</TableCell>
                    <TableCell>IAM Role</TableCell>
                    <TableCell>Athena WorkGroup</TableCell>
                    <TableCell>Permissions</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                {loading ? (
                  <CircularProgress sx={{ mt: 1 }} />
                ) : (
                  <TableBody>
                    {items.nodes.length > 0 ? (
                      items.nodes.map((team) => (
                        <TeamRow
                          team={team}
                          environment={environment}
                          fetchItems={fetchItems}
                          handleDeleteTeamModalOpen={handleDeleteTeamModalOpen}
                          handleDeleteTeamModalClose={
                            handleDeleteTeamModalClose
                          }
                          handleTeamEditModalOpen={handleTeamEditModalOpen}
                          handleTeamEditModalClose={handleTeamEditModalClose}
                          isDeleteTeamModalOpenId={isDeleteTeamModalOpenId}
                          isTeamEditModalOpenId={isTeamEditModalOpenId}
                        />
                      ))
                    ) : (
                      <TableRow hover>
                        <TableCell>No Team invited</TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                )}
              </Table>
              {!loading && items.nodes.length > 0 && (
                <Pager
                  mgTop={2}
                  mgBottom={2}
                  items={items}
                  onChange={handlePageChange}
                />
              )}
            </Box>
          </Scrollbar>
        </Card>
      </Box>
      <Box sx={{ mt: 3 }}>
        <Card>
          <CardHeader
            action={<RefreshTableMenu refresh={fetchRoles} />}
            title={
              <Box>
                <SupervisedUserCircleRounded style={{ marginRight: '10px' }} />{' '}
                Environment Consumption IAM roles
              </Box>
            }
          />
          <Divider />
          <Box
            sx={{
              alignItems: 'center',
              display: 'flex',
              flexWrap: 'wrap',
              m: -1,
              p: 2
            }}
          >
            <Grid item md={10} sm={6} xs={12}>
              <Box
                sx={{
                  m: 1,
                  maxWidth: '100%',
                  width: 500
                }}
              >
                <TextField
                  fullWidth
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <SearchIcon fontSize="small" />
                      </InputAdornment>
                    )
                  }}
                  onChange={handleInputChangeRoles}
                  onKeyUp={handleInputKeyupRoles}
                  placeholder="Search"
                  value={inputValueRoles}
                  variant="outlined"
                />
              </Box>
            </Grid>
            <Grid item md={2} sm={6} xs={12}>
              <Button
                color="primary"
                startIcon={<GroupAddOutlined fontSize="small" />}
                sx={{ m: 1 }}
                onClick={handleAddRoleModalOpen}
                variant="contained"
              >
                Add Consumption Role
              </Button>
              {isAddRoleModalOpen && (
                <EnvironmentRoleAddForm
                  environment={environment}
                  open
                  reloadRoles={fetchRoles}
                  onClose={handleAddRoleModalClose}
                />
              )}
            </Grid>
          </Box>
          <Scrollbar>
            <Box sx={{ minWidth: 600 }}>
              <DataGrid
                autoHeight
                getRowId={(node) => node.consumptionRoleUri}
                rows={roles.nodes}
                columns={[
                  { field: 'id', hide: true },
                  {
                    field: 'consumptionRoleName',
                    headerName: 'Name',
                    flex: 0.5,
                    editable: true
                  },
                  {
                    field: 'IAMRoleArn',
                    headerName: 'IAM Role',
                    flex: 1
                  },
                  {
                    field: 'groupUri',
                    headerName: 'Role Owner',
                    flex: 0.5,
                    editable: true,
                    type: 'singleSelect',
                    valueOptions: groupOptions.map((group) => group.label)
                  },
                  {
                    field: 'dataallManaged',
                    headerName: 'Policy Management',
                    valueGetter: (params) => {
                      return `${
                        params.row.dataallManaged
                          ? 'Data.all managed'
                          : 'Customer managed'
                      }`;
                    },
                    flex: 0.6
                  },
                  {
                    field: 'policiesNames',
                    headerName: 'IAM Policies',
                    flex: 0.5,
                    renderCell: (params: GridRenderCellParams<any, Date>) => (
                      <IAMRolePolicyDataGridCell
                        environmentUri={params.row.environmentUri}
                        IAMRoleName={params.row.IAMRoleArn.split('/').pop()}
                      />
                    )
                  },
                  {
                    field: 'actions',
                    headerName: 'Actions',
                    flex: 0.5,
                    type: 'actions',
                    cellClassName: 'actions',
                    getActions: ({ id, ...props }) => {
                      const name = props.row.consumptionRoleName;
                      const isInEditMode =
                        rowModesModel[id]?.mode === GridRowModes.Edit;

                      if (isInEditMode) {
                        return [
                          <GridActionsCellItem
                            icon={<SaveIcon />}
                            label="Save"
                            sx={{
                              color: 'primary.main'
                            }}
                            onClick={handleSaveClick(id)}
                          />,
                          <GridActionsCellItem
                            icon={<CancelIcon />}
                            label="Cancel"
                            className="textPrimary"
                            onClick={handleCancelClick(id)}
                            color="inherit"
                          />
                        ];
                      }
                      return [
                        <GridActionsCellItem
                          icon={<EditIcon />}
                          label="Edit"
                          className="textPrimary"
                          onClick={handleEditClick(id)}
                          color="inherit"
                        />,
                        <GridActionsCellItem
                          icon={<DeleteIcon />}
                          label="Delete"
                          onClick={() => handleDeleteRoleModalOpen(id)}
                          color="inherit"
                        />,
                        <DeleteObjectWithFrictionModal
                          objectName={name}
                          onApply={() => handleDeleteRoleModalClosed(id)}
                          onClose={() => handleDeleteRoleModalClosed(id)}
                          open={isDeleteRoleModalOpenId === id}
                          isAWSResource={false}
                          deleteFunction={() => removeConsumptionRole(id)}
                        />
                      ];
                    }
                  }
                ]}
                editMode="row"
                rowModesModel={rowModesModel}
                onRowModesModelChange={setRowModesModel}
                onRowEditStart={handleRowEditStart}
                onRowEditStop={handleRowEditStop}
                processRowUpdate={processRowUpdate}
                onProcessRowUpdateError={(error) =>
                  dispatch({ type: SET_ERROR, error: error.message })
                }
                experimentalFeatures={{ newEditingApi: true }}
                rowCount={roles.count}
                page={roles.page - 1}
                pageSize={filterRoles.pageSize}
                paginationMode="server"
                onPageChange={handlePageChangeRoles}
                loading={loadingRoles}
                onPageSizeChange={(pageSize) => {
                  setFilterRoles({ ...filterRoles, pageSize: pageSize });
                }}
                getRowHeight={() => 'auto'}
                disableSelectionOnClick
                sx={{ wordWrap: 'break-word' }}
              />
            </Box>
          </Scrollbar>
        </Card>
      </Box>
    </Box>
  );
};

EnvironmentTeams.propTypes = {
  environment: PropTypes.object.isRequired
};
