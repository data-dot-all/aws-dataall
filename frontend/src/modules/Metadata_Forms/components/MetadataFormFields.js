import { useDispatch } from 'react-redux';
import { v4 as uuidv4 } from 'uuid';
import React, { useEffect, useRef, useState } from 'react';

import PropTypes from 'prop-types';
import {
  Table,
  TableCell,
  TableHead,
  TableRow,
  TableBody,
  Card,
  Box,
  Grid,
  TextField,
  Divider,
  Button,
  Autocomplete,
  Tooltip,
  Chip,
  Typography,
  Dialog,
  FormControlLabel,
  Radio,
  RadioGroup
} from '@mui/material';
import {
  Scrollbar,
  AsteriskIcon,
  PencilAltIcon,
  SaveIcon,
  PlusIcon,
  ChipInput
} from '../../../design';
import { SET_ERROR } from '../../../globalErrors';
import Checkbox from '@mui/material/Checkbox';
import {
  createMetadataFormVersion,
  deleteMetadataFormVersion,
  getMetadataForm,
  listMetadataFormVersions
} from '../services';
import { useClient } from '../../../services';
import { GridActionsCellItem } from '@mui/x-data-grid';
import DeleteIcon from '@mui/icons-material/DeleteOutlined';
import SettingsBackupRestoreOutlinedIcon from '@mui/icons-material/SettingsBackupRestoreOutlined';
import DragIndicatorOutlinedIcon from '@mui/icons-material/DragIndicatorOutlined';
import { batchMetadataFormFieldUpdates } from '../services/batchMetadataFormFieldUpdates';
import CircularProgress from '@mui/material/CircularProgress';
import { listGlossaries } from '../../Glossaries/services';
import FormControl from '@mui/material/FormControl';
import { useSnackbar } from 'notistack';

const EditTable = (props) => {
  const { fields, fieldTypeOptions, saveChanges, formUri, glossaryNodes } =
    props;
  const [localFields, setLocalFields] = useState(fields);
  const dragItem = useRef();
  const dragOverItem = useRef();

  const swap = (i1, i2) => {
    const copyListItems = [...localFields];
    const dragItemContent = copyListItems[i1];
    copyListItems.splice(i1, 1);
    copyListItems.splice(i2, 0, dragItemContent);
    setLocalFields(copyListItems);
  };

  const dragStart = (e) => {
    dragItem.current = e.target.id;
  };

  const dragEnter = (e) => {
    dragOverItem.current = e.currentTarget;
    e.currentTarget.style.backgroundColor = 'aliceblue';
  };

  const dragLeave = (e) => {
    e.currentTarget.style.backgroundColor = 'white';
  };

  const drop = (e) => {
    swap(dragItem.current, dragOverItem.current.id);
    dragOverItem.current.style.backgroundColor = 'white';
    dragItem.current = null;
    dragOverItem.current = null;
  };

  const updateField = (index, propertyName, value) => {
    localFields[index][propertyName] = value;
    setLocalFields([...localFields]);
  };
  const addField = () => {
    localFields.push({
      id: uuidv4(),
      name: 'New Field',
      required: false,
      metadataFormUri: formUri,
      type: fieldTypeOptions[0].value,
      possibleValues: [],
      deleted: false
    });
    setLocalFields([...localFields]);
  };

  return (
    <>
      <Button
        color="primary"
        startIcon={<PlusIcon size={15} />}
        sx={{ mt: 1 }}
        onClick={addField}
        type="button"
      >
        Add field
      </Button>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell sx={{ width: '100px' }}>Required</TableCell>
            <TableCell>Name</TableCell>
            <TableCell sx={{ width: '10%' }}>Type</TableCell>
            <TableCell sx={{ width: '30%' }}>Description</TableCell>
            <TableCell sx={{ width: '20%' }}>
              Possible Values or Glossary Term
            </TableCell>
            <TableCell sx={{ width: '20px' }}>
              <Button
                color="primary"
                startIcon={<SaveIcon size={15} />}
                sx={{ mt: 1 }}
                onClick={() => {
                  saveChanges(localFields);
                }}
                type="button"
                variant="outlined"
              >
                Save
              </Button>
            </TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {localFields.length === 0 ? (
            <TableRow>
              <TableCell colSpan={6} align="center">
                No fields found
              </TableCell>
            </TableRow>
          ) : (
            localFields.map((field, index) => (
              <TableRow
                id={index}
                key={field.uri ? field.uri : field.id}
                onDragStart={dragStart}
                onDragEnter={dragEnter}
                onDragLeave={dragLeave}
                onDragEnd={drop}
                onDragOver={(e) => e.preventDefault()}
                draggable
                sx={{
                  backgroundColor: field.deleted ? 'whitesmoke' : 'white'
                }}
              >
                <TableCell>
                  <Checkbox
                    defaultChecked={field.required}
                    disabled={field.deleted}
                    onChange={(event, value) => {
                      updateField(index, 'required', value);
                    }}
                  />
                </TableCell>
                <TableCell>
                  <TextField
                    disabled={field.deleted}
                    defaultValue={field.name}
                    onKeyUp={(event) => {
                      updateField(index, 'name', event.target.value);
                    }}
                    sx={{ width: '100%' }}
                  />
                </TableCell>
                <TableCell>
                  <Autocomplete
                    disablePortal
                    disabled={field.deleted}
                    options={fieldTypeOptions.map((option) => option.value)}
                    defaultValue={field.type}
                    onChange={(event, value) => {
                      updateField(
                        index,
                        'type',
                        value || fieldTypeOptions[0].value
                      );
                    }}
                    renderInput={(params) => (
                      <TextField
                        sx={{ minWidth: '150px' }}
                        {...params}
                        label="Type"
                        variant="outlined"
                      />
                    )}
                  />
                </TableCell>
                <TableCell>
                  <TextField
                    disabled={field.deleted}
                    defaultValue={field.description}
                    sx={{ width: '100%' }}
                    onKeyUp={(event) => {
                      updateField(index, 'description', event.target.value);
                    }}
                  />
                </TableCell>
                <TableCell>
                  {field.type !==
                  fieldTypeOptions.find((o) => o.name === 'GlossaryTerm')
                    .value ? (
                    <ChipInput
                      fullWidth
                      variant="outlined"
                      placeholder="Hit enter after typing"
                      defaultValue={field.possibleValues}
                      disabled={
                        field.deleted ||
                        field.type ===
                          fieldTypeOptions.find((o) => o.name === 'Boolean')
                            .value
                      }
                      onChange={(chip) => {
                        updateField(index, 'possibleValues', [...chip]);
                      }}
                    />
                  ) : (
                    <Autocomplete
                      disablePortal
                      disabled={field.deleted}
                      options={glossaryNodes.map((node) => {
                        return { label: node.label, value: node.nodeUri };
                      })}
                      defaultValue={glossaryNodes.find(
                        (node) => field.glossaryNodeUri === node.nodeUri
                      )}
                      onChange={(event, node) => {
                        if (node) {
                          updateField(index, 'glossaryNodeUri', node.value);
                        }
                      }}
                      renderInput={(params) => (
                        <TextField {...params} variant="outlined" />
                      )}
                    />
                  )}
                </TableCell>
                <TableCell
                  sx={{
                    width: '20px',
                    alignContent: 'center',
                    textAlign: 'center'
                  }}
                >
                  <Tooltip title={field.deleted ? 'Restore' : 'Delete'}>
                    <GridActionsCellItem
                      icon={
                        field.deleted ? (
                          <SettingsBackupRestoreOutlinedIcon />
                        ) : (
                          <DeleteIcon />
                        )
                      }
                      label={field.deleted ? 'Restore' : 'Delete'}
                      sx={{
                        color: 'primary.main'
                      }}
                      onClick={() => {
                        updateField(index, 'deleted', !field.deleted);
                      }}
                    />
                  </Tooltip>
                  <GridActionsCellItem
                    icon={<DragIndicatorOutlinedIcon size={15} />}
                    label="drag"
                    sx={{
                      color: 'primary.main'
                    }}
                  />
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </>
  );
};

EditTable.propTypes = {
  fields: PropTypes.array.isRequired,
  fieldTypeOptions: PropTypes.array.isRequired,
  saveChanges: PropTypes.func.isRequired,
  formUri: PropTypes.string.isRequired,
  glossaryNodes: PropTypes.array.isRequired
};

const DisplayTable = (props) => {
  const { fields, startEdit, userRole, userRolesMF, enableEdit } = props;
  return (
    <Table>
      <TableHead>
        <TableRow>
          <TableCell sx={{ width: '20px' }}>Required</TableCell>
          <TableCell>Name</TableCell>
          <TableCell sx={{ width: '10%' }}>Type</TableCell>
          <TableCell sx={{ width: '30%' }}>Description</TableCell>
          <TableCell sx={{ width: '20%' }}>
            Possible Values or Glossary Term
          </TableCell>
          <TableCell sx={{ width: '20px', alignContent: 'center' }}>
            {userRole === userRolesMF.Owner && (
              <Button
                color="primary"
                startIcon={<PencilAltIcon size={15} />}
                sx={{ mt: 1 }}
                onClick={startEdit}
                disabled={!enableEdit}
                type="button"
                variant="outlined"
              >
                Edit
              </Button>
            )}
          </TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {fields.length === 0 ? (
          <TableRow>
            <TableCell colSpan={6} align="center">
              No fields found
            </TableCell>
          </TableRow>
        ) : (
          fields.map((field) => (
            <TableRow key={field.uri}>
              <TableCell
                sx={{
                  textAlign: 'center'
                }}
              >
                {field.required ? <AsteriskIcon /> : ''}
              </TableCell>
              <TableCell>{field.name}</TableCell>
              <TableCell>{field.type}</TableCell>
              <TableCell>{field.description}</TableCell>
              <TableCell>
                {field.possibleValues?.map((val) => (
                  <Chip
                    sx={{ mr: 0.5, mb: 0.5 }}
                    key={val}
                    label={val}
                    variant="outlined"
                  />
                ))}
                {field.glossaryNodeUri && field.glossaryNodeName}
              </TableCell>
              <TableCell></TableCell>
            </TableRow>
          ))
        )}
      </TableBody>
    </Table>
  );
};
DisplayTable.propTypes = {
  fields: PropTypes.array.isRequired,
  startEdit: PropTypes.func.isRequired
};

const NewVersionModal = (props) => {
  const { versions, createNewVersion, currentVersion, onClose } = props;
  const [blankVersion, setBlankVersion] = useState(false);
  const [copyVersion, setCopyVersion] = useState(currentVersion);

  const handleCreateNewVersion = () => {
    if (blankVersion) {
      createNewVersion();
    } else {
      createNewVersion(copyVersion);
    }
    onClose();
  };

  return (
    <Dialog maxWidth="sm" fullWidth onClose={onClose} open={() => {}}>
      <Box sx={{ p: 3 }}>
        <Typography
          align="center"
          color="textPrimary"
          gutterBottom
          variant="h4"
        >
          Create New Version
        </Typography>
        <Typography color="textPrimary" gutterBottom>
          All enforcement rules will be updated to use the latest version.
        </Typography>
        <FormControl>
          <RadioGroup
            value={blankVersion}
            onChange={(event, value) => setBlankVersion(value)}
          >
            <FormControlLabel
              sx={{ pt: 1 }}
              value={false}
              control={<Radio />}
              label="As a copy of"
            />
            <FormControlLabel
              sx={{ mt: 2 }}
              value={true}
              control={<Radio />}
              label="Blank version"
            />
          </RadioGroup>
        </FormControl>
        <FormControl>
          <Autocomplete
            disablePortal
            options={versions.map((option) => {
              return {
                label: 'version ' + option.version,
                value: option.version
              };
            })}
            defaultValue={'version ' + copyVersion}
            onChange={(event, value) => {
              setCopyVersion(value ? value.value : currentVersion[0]);
            }}
            renderInput={(params) => (
              <TextField
                sx={{ minWidth: '150px' }}
                {...params}
                label="Version"
                variant="outlined"
              />
            )}
          />
        </FormControl>
      </Box>
      <Box sx={{ mb: 2, textAlign: 'center' }}>
        <Button
          sx={{ mt: 2, minWidth: '150px' }}
          onClick={handleCreateNewVersion}
          color="primary"
          variant="contained"
        >
          Create
        </Button>
        <Button
          sx={{ mt: 2, ml: 2, minWidth: '150px' }}
          onClick={onClose}
          color="primary"
          variant="outlined"
        >
          Cancel
        </Button>
      </Box>
    </Dialog>
  );
};

export const ConfirmationPopUp = (props) => {
  const { version, attachedFormCount, onClose, onDelete } = props;
  return (
    <Dialog maxWidth="sm" fullWidth onClose={onClose} open={() => {}}>
      <Box sx={{ p: 3 }}>
        <Typography
          align="center"
          color="textPrimary"
          gutterBottom
          variant="h4"
        >
          Delete Version {version}
        </Typography>
        <Typography color="textPrimary" align="center" gutterBottom>
          If you delete this version,
          <br /> all data associated with it will be lost. <br />
          All enforcement rules will be updated to use the latest version.
          <br />
          Attached entities: {attachedFormCount}
        </Typography>
      </Box>
      <Box sx={{ mb: 2, textAlign: 'center' }}>
        <Button
          sx={{ mt: 2, minWidth: '150px' }}
          onClick={() => {
            onDelete();
            onClose();
          }}
          color="primary"
          variant="contained"
        >
          Delete
        </Button>
        <Button
          sx={{ mt: 2, ml: 2, minWidth: '150px' }}
          onClick={onClose}
          color="primary"
          variant="outlined"
        >
          Cancel
        </Button>
      </Box>
    </Dialog>
  );
};

export const MetadataFormFields = (props) => {
  const dispatch = useDispatch();
  const { enqueueSnackbar } = useSnackbar();

  const client = useClient();
  const { metadataForm, fieldTypeOptions, userRolesMF } = props;
  const [loading, setLoading] = useState(false);
  const [editOn, setEditOn] = useState(false);
  const [fields, setFields] = useState(metadataForm.fields);
  const [glossaryNodes, setGlossaryNodes] = useState([]);
  const [currentVersion, setCurrentVersion] = useState(0);
  const [attachedFormCount, setAttachedFormCount] = useState(0);
  const [versionOptions, setVersionOptions] = useState([]);
  const [showNewVersionModal, setShowNewVersionModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);

  const startEdit = () => {
    setEditOn(true);
  };

  const fetchGlossaryNodes = async () => {
    const response = await client.query(listGlossaries({}));
    if (
      !response.errors &&
      response.data &&
      response.data.listGlossaries !== null
    ) {
      setGlossaryNodes(response.data.listGlossaries.nodes);
    } else {
      const error = response.errors
        ? response.errors[0].message
        : 'Glossary Nodes not found';
      dispatch({ type: SET_ERROR, error });
    }
  };

  const deleteVersion = async () => {
    setLoading(true);
    const response = await client.mutate(
      deleteMetadataFormVersion(metadataForm.uri, currentVersion)
    );
    if (
      !response.errors &&
      response.data &&
      response.data.deleteMetadataFormVersion !== null
    ) {
      metadataForm.versions = metadataForm.versions.filter(
        (v) => v !== currentVersion
      );
      await fetchVersions();
      await fetchItems(metadataForm.versions[0].version);
      enqueueSnackbar('Version deleted', {
        anchorOrigin: {
          horizontal: 'right',
          vertical: 'top'
        },
        variant: 'success'
      });
    } else {
      const error = response.errors
        ? response.errors[0].message
        : 'Delete version failed';
      dispatch({ type: SET_ERROR, error });
    }
    setLoading(false);
  };

  const createNewVersion = async (copyVersion = null) => {
    setLoading(true);
    const response = await client.mutate(
      createMetadataFormVersion(metadataForm.uri, copyVersion)
    );
    if (
      !response.errors &&
      response.data &&
      response.data.createMetadataFormVersion !== null
    ) {
      await fetchVersions();
      await fetchItems(response.data.createMetadataFormVersion);
      enqueueSnackbar('Version created', {
        anchorOrigin: {
          horizontal: 'right',
          vertical: 'top'
        },
        variant: 'success'
      });
    } else {
      const error = response.errors
        ? response.errors[0].message
        : 'Create version failed';
      dispatch({ type: SET_ERROR, error });
    }
    setLoading(false);
  };

  const fetchVersions = async () => {
    const response = await client.query(
      listMetadataFormVersions(metadataForm.uri)
    );
    if (
      !response.errors &&
      response.data &&
      response.data.listMetadataFormVersions !== null
    ) {
      setCurrentVersion(response.data.listMetadataFormVersions[0].version);
      setAttachedFormCount(
        response.data.listMetadataFormVersions[0].attached_forms
      );
      setVersionOptions(response.data.listMetadataFormVersions);
    } else {
      const error = response.errors
        ? response.errors[0].message
        : 'Versions not found';
      dispatch({ type: SET_ERROR, error });
    }
  };
  const fetchItems = async (version = null) => {
    setLoading(true);
    const response = await client.query(
      getMetadataForm(metadataForm.uri, version)
    );

    if (
      !response.errors &&
      response.data &&
      response.data.getMetadataForm !== null
    ) {
      setFields(response.data.getMetadataForm.fields);
    } else {
      const error = response.errors
        ? response.errors[0].message
        : 'Metadata Forms not found';
      dispatch({ type: SET_ERROR, error });
    }
    setLoading(false);
  };

  const saveChanges = async (updatedFields) => {
    const badfield = updatedFields.find(
      (field) =>
        !field.deleted &&
        field.type ===
          fieldTypeOptions.find((o) => o.name === 'GlossaryTerm').value &&
        !field.glossaryNodeUri
    );
    if (badfield) {
      dispatch({
        type: SET_ERROR,
        error: 'Glossary Term is required for field ' + badfield.name
      });
      return;
    }
    setLoading(true);
    // remove new fields (not yet saved in DB), that were deleted during editing
    const data = updatedFields.filter((field) => !field.deleted || field.uri);
    data.forEach((field, index) => {
      delete field.__typename;
      delete field.glossaryNodeName;
      delete field.id;
      field.displayNumber = index;
    });
    const response = await client.mutate(
      batchMetadataFormFieldUpdates(metadataForm.uri, data)
    );
    if (
      !response.errors &&
      response.data &&
      response.data.batchMetadataFormFieldUpdates !== null
    ) {
      setFields(response.data.batchMetadataFormFieldUpdates);
      setEditOn(false);
    } else {
      const error = response.errors
        ? response.errors[0].message
        : 'Update failed';
      dispatch({ type: SET_ERROR, error });
    }
    setLoading(false);
  };

  useEffect(() => {
    if (client) {
      fetchItems().catch((e) =>
        dispatch({ type: SET_ERROR, error: e.message })
      );
      fetchVersions().catch((e) =>
        dispatch({ type: SET_ERROR, error: e.message })
      );
      if (glossaryNodes.length === 0) {
        fetchGlossaryNodes().catch((e) =>
          dispatch({ type: SET_ERROR, error: e.message })
        );
      }
    }
  }, [client, dispatch]);

  return (
    <Box>
      <Card>
        <Box
          sx={{
            alignItems: 'center',
            display: 'flex',
            flexWrap: 'wrap',
            m: -1,
            p: 2
          }}
        >
          <Grid container spacing={2}>
            <Grid item lg={2} xl={2} xs={6}>
              {currentVersion > 0 && (
                <Autocomplete
                  disablePortal
                  options={versionOptions.map((option) => {
                    return {
                      label: 'version ' + option.version,
                      value: option.version,
                      attached: option.attached_forms
                    };
                  })}
                  value={'version ' + currentVersion}
                  onChange={async (event, value) => {
                    setCurrentVersion(
                      value ? value.value : versionOptions[0].version
                    );
                    setAttachedFormCount(value ? value.attached : 0);
                    await fetchItems(
                      value ? value.value : versionOptions[0].version
                    );
                  }}
                  renderInput={(params) => (
                    <TextField
                      sx={{ minWidth: '150px' }}
                      {...params}
                      label="Version"
                      variant="outlined"
                    />
                  )}
                />
              )}
            </Grid>
            <Grid item lg={2} xl={2} xs={6}>
              {metadataForm.userRole === userRolesMF.Owner && (
                <Button
                  color="primary"
                  startIcon={<PlusIcon size={15} />}
                  sx={{ mt: 1 }}
                  onClick={() => setShowNewVersionModal(true)}
                  type="button"
                >
                  New Version
                </Button>
              )}
              {showNewVersionModal && (
                <NewVersionModal
                  onClose={() => setShowNewVersionModal(false)}
                  currentVersion={currentVersion}
                  versions={versionOptions}
                  createNewVersion={createNewVersion}
                ></NewVersionModal>
              )}
            </Grid>
            <Grid
              item
              lg={6}
              xl={6}
              xs={4}
              sx={{
                textAlign: 'right'
              }}
            >
              {metadataForm.userRole === userRolesMF.Owner && (
                <Typography
                  sx={{ pt: 2 }}
                  variant="subtitle2"
                  color="textPrimary"
                >
                  Attached entities : {attachedFormCount}
                </Typography>
              )}
            </Grid>
            <Grid
              item
              lg={2}
              xl={2}
              xs={4}
              sx={{
                textAlign: 'right'
              }}
            >
              {metadataForm.userRole === userRolesMF.Owner && (
                <Button
                  color="primary"
                  startIcon={<DeleteIcon size={15} />}
                  sx={{ mt: 1 }}
                  onClick={() => setShowDeleteModal(true)}
                  type="button"
                  disabled={versionOptions.length === 1}
                >
                  Delete Version
                </Button>
              )}
              {showDeleteModal && (
                <ConfirmationPopUp
                  onClose={() => setShowDeleteModal(false)}
                  onDelete={deleteVersion}
                  version={currentVersion}
                  attachedFormCount={attachedFormCount}
                ></ConfirmationPopUp>
              )}
            </Grid>
          </Grid>
        </Box>
        <Divider />
        {loading ? (
          <Box
            sx={{
              p: 2,
              minHeight: '400px',
              alignContent: 'center',
              display: 'flex',
              justifyContent: 'center'
            }}
          >
            <CircularProgress size={100} />
          </Box>
        ) : (
          <Scrollbar>
            <Box
              sx={{
                p: 2,
                minHeight: '400px'
              }}
            >
              {editOn ? (
                <EditTable
                  fields={fields}
                  fieldTypeOptions={fieldTypeOptions}
                  saveChanges={saveChanges}
                  formUri={metadataForm.uri}
                  glossaryNodes={glossaryNodes}
                />
              ) : (
                <DisplayTable
                  fields={fields}
                  startEdit={startEdit}
                  userRole={metadataForm.userRole}
                  userRolesMF={userRolesMF}
                  enableEdit={attachedFormCount === 0}
                />
              )}
            </Box>
          </Scrollbar>
        )}
      </Card>
    </Box>
  );
};

MetadataFormFields.propTypes = {
  metadataForm: PropTypes.any.isRequired,
  fieldTypeOptions: PropTypes.any.isRequired
};
