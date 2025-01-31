import React, { useEffect, useState } from 'react';

import { useDispatch } from 'react-redux';

import {
  Autocomplete,
  Box,
  Button,
  Card,
  CardContent,
  Divider,
  Grid,
  TextField,
  Typography
} from '@mui/material';
import {
  deleteAttachedMetadataForm,
  getAttachedMetadataForm,
  getEntityMetadataFormPermissions,
  getMetadataForm,
  listAttachedMetadataForms,
  listEntityMetadataForms
} from '../services';
import { Defaults, PlusIcon } from 'design';
import CircularProgress from '@mui/material/CircularProgress';
import { useClient } from 'services';
import { RenderedMetadataForm } from './renderedMetadataForm';
import { SET_ERROR } from 'globalErrors';
import { AttachedFormCard } from './AttachedFormCard';
import DoNotDisturbAltOutlinedIcon from '@mui/icons-material/DoNotDisturbAltOutlined';
import DeleteIcon from '@mui/icons-material/DeleteOutlined';

export const MetadataAttachment = (props) => {
  const { entityType, entityUri, affectingRules } = props;
  const client = useClient();
  const dispatch = useDispatch();
  const [selectedForm, setSelectedForm] = useState(null);
  const [selectedAttachedForm, setSelectedAttachedForm] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingFields, setLoadingFields] = useState(false);
  const [formsList, setFormsList] = useState([]);
  const [fields, setFields] = useState([]);
  const [canEdit, setCanEdit] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [values, setValues] = useState({});
  const [attachedMFUri, setAttachedMFUri] = useState(-1);
  const [filter] = useState({
    ...Defaults.filter,
    pageSize: 20,
    entityType: entityType,
    entityUri: entityUri
  });
  const [addNewForm, setAddNewForm] = useState(false);
  const [availableForms, setAvailableForms] = useState([]);
  const [missingRules, setMissingRules] = useState([]);

  const fetchAvailableForms = async () => {
    const response = await client.query(
      listEntityMetadataForms({
        ...Defaults.filter,
        entityType: entityType,
        entityUri: entityUri,
        hideAttached: true
      })
    );
    if (!response.errors) {
      setAvailableForms(
        response.data.listEntityMetadataForms.nodes.map((form) => ({
          label: form.name,
          value: form.uri,
          form: form
        }))
      );
    } else {
      dispatch({ type: SET_ERROR, error: response.errors[0].message });
    }
  };

  const fetchList = async () => {
    setLoading(true);
    const response = await client.query(listAttachedMetadataForms(filter));
    if (!response.errors) {
      response.data.listAttachedMetadataForms.nodes.forEach((form) => {
        const r = affectingRules.find(
          (r) => r.metadataFormUri === form.metadataForm.uri
        );
        if (r) {
          form.required = r.severity;
          form.required_version = r.version;
        }
      });
      const missing = affectingRules.filter(
        (r) =>
          !response.data.listAttachedMetadataForms.nodes.find(
            (form) => r.metadataFormUri === form.metadataForm.uri
          )
      );

      setMissingRules([...missing]);
      setFormsList(response.data.listAttachedMetadataForms.nodes);
      if (
        response.data.listAttachedMetadataForms.nodes.length > 0 &&
        !selectedAttachedForm
      ) {
        setSelectedAttachedForm(
          response.data.listAttachedMetadataForms.nodes[0]
        );
        await fetchAttachedFields(
          response.data.listAttachedMetadataForms.nodes[0].uri
        );
      }
    } else {
      dispatch({ type: SET_ERROR, error: response.errors[0].message });
    }
    setLoading(false);
  };

  const fetchFields = async (uri) => {
    setLoadingFields(true);
    const response = await client.query(getMetadataForm(uri));
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
    setLoadingFields(false);
  };
  const fetchAttachedFields = async (uri) => {
    setLoadingFields(true);
    const response = await client.query(getAttachedMetadataForm(uri));
    if (
      !response.errors &&
      response.data &&
      response.data.getAttachedMetadataForm !== null
    ) {
      setFields(response.data.getAttachedMetadataForm.fields);
    } else {
      const error = response.errors
        ? response.errors[0].message
        : 'Attached Metadata Form not found';
      dispatch({ type: SET_ERROR, error });
    }
    setLoadingFields(false);
  };

  const deleteAttachedForm = async (uri) => {
    const response = await client.mutate(deleteAttachedMetadataForm(uri));
    if (!response.errors) {
      fetchList().catch((e) => dispatch({ type: SET_ERROR, error: e.message }));
      fetchAvailableForms().catch((e) =>
        dispatch({ type: SET_ERROR, error: e.message })
      );
      setSelectedAttachedForm(null);
    } else {
      const error = response.errors
        ? response.errors[0].message
        : 'Fail to delete attached form';
      dispatch({ type: SET_ERROR, error });
    }
  };

  const getPermissions = async () => {
    const response = await client.query(
      getEntityMetadataFormPermissions(entityUri)
    );
    if (!response.errors) {
      setCanEdit(
        response.data.getEntityMetadataFormPermissions.includes(
          'ATTACH_METADATA_FORM'
        )
      );
    }
  };

  useEffect(() => {
    if (client) {
      fetchList().catch((e) => dispatch({ type: SET_ERROR, error: e.message }));
      getPermissions().catch((e) =>
        dispatch({ type: SET_ERROR, error: e.message })
      );
      fetchAvailableForms().catch((e) =>
        dispatch({ type: SET_ERROR, error: e.message })
      );
    }
  }, [client, dispatch, filter]);

  if (loading) {
    return (
      <Box
        sx={{
          pt: 10,
          minHeight: '400px',
          alignContent: 'center',
          display: 'flex',
          justifyContent: 'center'
        }}
      >
        <CircularProgress size={100} />
      </Box>
    );
  }

  return (
    <Grid container spacing={2} sx={{ height: 'calc(100vh - 320px)', mb: -5 }}>
      <Grid item lg={6} xl={6} xs={12}>
        <Card sx={{ height: '100%' }}>
          {canEdit && (
            <>
              <CardContent>
                <Button
                  color="primary"
                  startIcon={<PlusIcon size={15} />}
                  sx={{ mt: 1 }}
                  type="button"
                  onClick={() => {
                    setSelectedForm(null);
                    setAddNewForm(true);
                  }}
                >
                  Attach form
                </Button>
              </CardContent>
              <Divider />
            </>
          )}
          {addNewForm && !editMode && (
            <CardContent>
              <Autocomplete
                disablePortal
                options={availableForms}
                value={selectedForm.name}
                onChange={async (event, value) => {
                  if (value) {
                    setSelectedForm(value.form);
                    setEditMode(false);
                    setValues({});
                    await fetchFields(value.value);
                  } else setSelectedForm(null);
                }}
                renderInput={(params) => (
                  <TextField
                    sx={{ width: '100%' }}
                    {...params}
                    label="Select Metadata Form"
                    variant="outlined"
                  />
                )}
              />
            </CardContent>
          )}
          {missingRules.length > 0 &&
            missingRules.map((rule) => (
              <CardContent>
                <Grid container spacing={2}>
                  <Grid item lg={8} xl={8}>
                    <Typography
                      color="textPrimary"
                      variant="subtitle2"
                      sx={{
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        maxLines: 1
                      }}
                    >
                      {rule.metadataFormName + ' v.' + rule.version}
                    </Typography>
                  </Grid>
                  <Grid item lg={3} xl={3}>
                    <Typography
                      variant="subtitle2"
                      sx={{
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        maxLines: 1,
                        color: rule.severity === 'Mandatory' ? 'red' : 'orange'
                      }}
                    >
                      {'Missing ' + rule.severity}
                    </Typography>
                  </Grid>
                  <Grid item lg={1} xl={1}>
                    {canEdit && (
                      <PlusIcon
                        size={15}
                        sx={{ color: 'primary.main', opacity: 0.5 }}
                        onMouseOver={(e) => {
                          e.currentTarget.style.opacity = 1;
                        }}
                        onMouseOut={(e) => {
                          e.currentTarget.style.opacity = 0.5;
                        }}
                        onClick={async () => {
                          {
                            setSelectedForm(
                              availableForms.find(
                                (form) => form.value === rule.metadataFormUri
                              ).form
                            );
                            setEditMode(false);
                            setAddNewForm(true);
                            setValues({});
                            await fetchFields(rule.metadataFormUri);
                          }
                        }}
                      />
                    )}
                  </Grid>
                </Grid>
              </CardContent>
            ))}

          {formsList.length > 0 ? (
            formsList.map((attachedForm) => (
              <CardContent
                sx={{
                  backgroundColor:
                    selectedAttachedForm &&
                    selectedAttachedForm.uri === attachedForm.uri
                      ? '#e6e6e6'
                      : 'white'
                }}
              >
                <Grid container spacing={2}>
                  <Grid
                    item
                    lg={8}
                    xl={8}
                    onClick={async () => {
                      setSelectedAttachedForm(attachedForm);
                      setEditMode(false);
                      setAddNewForm(false);
                      setValues({});
                      await fetchAttachedFields(attachedForm.uri);
                    }}
                  >
                    <Typography
                      color="textPrimary"
                      variant="subtitle2"
                      sx={{
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        maxLines: 1
                      }}
                    >
                      {attachedForm.metadataForm.name +
                        ' v.' +
                        attachedForm.version}
                    </Typography>
                  </Grid>
                  <Grid item lg={3} xl={3}>
                    {attachedForm.required && (
                      <Typography
                        variant="subtitle2"
                        sx={{
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          maxLines: 1,
                          color:
                            attachedForm.required === 'Mandatory'
                              ? 'red'
                              : 'green'
                        }}
                      >
                        {attachedForm.required}{' '}
                        {attachedForm.version < attachedForm.required_version
                          ? 'v. ' + attachedForm.required_version
                          : ''}
                      </Typography>
                    )}
                  </Grid>
                  <Grid item lg={1} xl={1}>
                    {canEdit && (
                      <DeleteIcon
                        sx={{ color: 'primary.main', opacity: 0.5 }}
                        onMouseOver={(e) => {
                          e.currentTarget.style.opacity = 1;
                        }}
                        onMouseOut={(e) => {
                          e.currentTarget.style.opacity = 0.5;
                        }}
                        onClick={() => deleteAttachedForm(attachedForm.uri)}
                      />
                    )}
                  </Grid>
                </Grid>
              </CardContent>
            ))
          ) : (
            <CardContent sx={{ display: 'flex', justifyContent: 'center' }}>
              <DoNotDisturbAltOutlinedIcon sx={{ mr: 1 }} />
              <Typography variant="subtitle2" color="textPrimary">
                No Metadata Forms Attached
              </Typography>
            </CardContent>
          )}
        </Card>
      </Grid>
      <Grid item lg={6} xl={6} xs={12}>
        {loadingFields && (
          <Box
            sx={{
              pt: 10,
              minHeight: '400px',
              alignContent: 'center',
              display: 'flex',
              justifyContent: 'center'
            }}
          >
            <CircularProgress size={100} />
          </Box>
        )}
        {addNewForm && selectedForm && !loadingFields && (
          <RenderedMetadataForm
            fields={fields}
            values={values}
            editMode={editMode}
            metadataForm={selectedForm}
            preview={false}
            onCancel={() => {
              setAddNewForm(false);
              setSelectedForm(null);
              setFields([]);
              setEditMode(false);
              setValues({});
              setAttachedMFUri(-1);
            }}
            entityUri={entityUri}
            entityType={entityType}
            attachedUri={attachedMFUri}
            onSubmit={async (attachedForm) => {
              setSelectedAttachedForm(attachedForm);
              setEditMode(false);
              setValues({});
              setFields(attachedForm.fields);
              fetchList().catch((e) =>
                dispatch({ type: SET_ERROR, error: e.message })
              );
              fetchAvailableForms().catch((e) =>
                dispatch({ type: SET_ERROR, error: e.message })
              );
              setAddNewForm(false);
              setAttachedMFUri(-1);
            }}
          />
        )}
        {!addNewForm && !loadingFields && selectedAttachedForm && (
          <AttachedFormCard
            fields={fields}
            attachedForm={selectedAttachedForm}
            onEdit={() => {
              setSelectedForm(selectedAttachedForm.metadataForm);
              const tmp_dict = {};
              fields.forEach((f) => {
                tmp_dict[f.field.name] = f.value;
              });
              setValues(tmp_dict);
              setEditMode(true);
              setAddNewForm(true);
              setAttachedMFUri(selectedAttachedForm.uri);
            }}
          />
        )}
      </Grid>
    </Grid>
  );
};
