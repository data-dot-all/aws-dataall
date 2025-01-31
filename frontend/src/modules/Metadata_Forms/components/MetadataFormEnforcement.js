import PropTypes from 'prop-types';
import {
  Autocomplete,
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
  Checkbox,
  Chip,
  CircularProgress,
  Dialog,
  FormControlLabel,
  Grid,
  TextField,
  Typography
} from '@mui/material';
import { Defaults, Label, PlusIcon } from 'design';
import React, { useEffect, useState } from 'react';
import DoNotDisturbAltOutlinedIcon from '@mui/icons-material/DoNotDisturbAltOutlined';
import { fetchEnums, listValidEnvironments, useClient } from 'services';
import { useDispatch } from 'react-redux';
import { SET_ERROR } from 'globalErrors';
import {
  createMetadataFormEnforcementRule,
  listMetadataFormEnforcementRules,
  listEntityAffectedByEnforcementRules,
  deleteMetadataFormEnforcementRule,
  listEntityTypesWithScope
} from '../services';
import { Formik } from 'formik';
import { LoadingButton } from '@mui/lab';
import SendIcon from '@mui/icons-material/Send';
import { listOrganizations } from '../../Organizations/services';
import { listDatasets } from '../../DatasetsBase/services';
import { useTheme } from '@mui/styles';
import DeleteIcon from '@mui/icons-material/DeleteOutlined';
import { DataGrid } from '@mui/x-data-grid';

const CreateEnforcementRuleModal = (props) => {
  const {
    onCancel,
    onSubmit,
    open,
    metadataForm,
    severityOptions,
    entityTypesOptions,
    enforcementScopeOptions,
    ...other
  } = props;

  const client = useClient();
  const dispatch = useDispatch();

  const [environmentOptions, setEnvironmentOptions] = useState([]);
  const [organizationOptions, setOrganizationOptions] = useState([]);
  const [datasetOptions, setDatasetOptions] = useState([]);
  const [entityTypes, setEntityTypes] = useState([...entityTypesOptions]);

  const enforcementScopeDict = {};
  for (const option of enforcementScopeOptions) {
    enforcementScopeDict[option.name] = option.value;
  }

  const fetchOrganizations = async () => {
    try {
      const response = await client.query(
        listOrganizations({
          filter: Defaults.selectListFilter
        })
      );
      if (!response.errors) {
        setOrganizationOptions(
          response.data.listOrganizations.nodes.map((e) => ({
            ...e,
            value: e.organizationUri,
            label: e.label
          }))
        );
      } else {
        dispatch({ type: SET_ERROR, error: response.errors[0].message });
      }
    } catch (e) {
      dispatch({ type: SET_ERROR, error: e.message });
    }
  };
  const fetchEnvironments = async () => {
    try {
      const response = await client.query(
        listValidEnvironments({
          filter: Defaults.selectListFilter
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
    } catch (e) {
      dispatch({ type: SET_ERROR, error: e.message });
    }
  };

  const fetchDatasets = async () => {
    try {
      const response = await client.query(
        listDatasets({
          filter: Defaults.selectListFilter
        })
      );
      if (!response.errors) {
        setDatasetOptions(
          response.data.listDatasets.nodes.map((e) => ({
            ...e,
            value: e.datasetUri,
            label: e.label
          }))
        );
      } else {
        dispatch({ type: SET_ERROR, error: response.errors[0].message });
      }
    } catch (e) {
      dispatch({ type: SET_ERROR, error: e.message });
    }
  };

  useEffect(async () => {
    if (client) {
      await fetchEnvironments();
      await fetchOrganizations();
      await fetchDatasets();
    }
    setEntityTypes([
      ...entityTypesOptions.map((t) => ({ ...t, disabled: false }))
    ]);
  }, [client, open, dispatch]);

  async function submit(values, setStatus, setSubmitting, setErrors) {
    let homeEntity = null;
    if (values.scope === enforcementScopeDict['Organization']) {
      homeEntity = values.organization;
    }
    if (values.scope === enforcementScopeDict['Environment']) {
      homeEntity = values.environment;
    }
    if (values.scope === enforcementScopeDict['Dataset']) {
      homeEntity = values.dataset;
    }

    const input = {
      metadataFormUri: metadataForm.uri,
      level: values.scope,
      severity: values.severity,
      homeEntity: homeEntity,
      entityTypes: values.entityTypes
    };
    const response = await client.mutate(
      createMetadataFormEnforcementRule(input)
    );
    if (response.errors) {
      setStatus({ success: false });
      setErrors({ submit: response.errors[0].message });
      const error = response.errors[0].message;
      dispatch({ type: SET_ERROR, error });
      setSubmitting(false);
    } else {
      setStatus({ success: true });
      setSubmitting(false);
      onSubmit();
    }
  }

  return (
    <Dialog maxWidth="md" fullWidth onClose={onCancel} open={open} {...other}>
      <Box sx={{ p: 3 }}>
        <Typography
          align="center"
          color="textPrimary"
          gutterBottom
          variant="h4"
        >
          Enforce {metadataForm.name + ' v. ' + metadataForm.versions[0]}
        </Typography>
        <Formik
          initialValues={{
            version: metadataForm.versions[0],
            scope: enforcementScopeDict['Global'],
            severity: severityOptions[0].value,
            entityTypes: []
          }}
          onSubmit={async (values, { setErrors, setStatus, setSubmitting }) => {
            await submit(values, setStatus, setSubmitting, setErrors);
          }}
        >
          {({
            errors,
            handleBlur,
            handleChange,
            handleSubmit,
            isSubmitting,
            setFieldValue,
            touched,
            values
          }) => (
            <form onSubmit={handleSubmit}>
              <Box>
                <CardContent>
                  <Autocomplete
                    id="scope"
                    disablePortal
                    options={enforcementScopeOptions.map((option) => {
                      return {
                        label: option.name,
                        value: option.value
                      };
                    })}
                    defaultValue={enforcementScopeDict['Global']}
                    onChange={async (event, value) => {
                      entityTypesOptions.forEach((entityType) => {
                        entityType.disabled = !entityType.levels.includes(
                          value.value
                        );
                      });
                      setEntityTypes([...entityTypesOptions]);
                      const active = entityTypesOptions
                        .filter((t) => !t.disabled)
                        .map((t) => t.name);
                      await setFieldValue('scope', value.value);
                      await setFieldValue('entityTypes', [
                        ...values.entityTypes.filter((t) => active.includes(t))
                      ]);
                    }}
                    renderInput={(params) => (
                      <TextField
                        {...params}
                        fullWidth
                        error={Boolean(touched.scope && errors.scope)}
                        helperText={touched.scope && errors.scope}
                        label="Enforcement Level"
                        onChange={handleChange}
                        variant="outlined"
                      />
                    )}
                  />
                </CardContent>
                {values.scope === enforcementScopeDict['Organization'] && (
                  <CardContent>
                    <Autocomplete
                      id="organization"
                      disablePortal
                      onChange={(event, value) => {
                        setFieldValue('organization', value.value);
                      }}
                      options={organizationOptions}
                      renderInput={(params) => (
                        <TextField
                          {...params}
                          fullWidth
                          error={Boolean(
                            touched.organization && errors.organization
                          )}
                          helperText={
                            touched.organization && errors.organization
                          }
                          label="Organization"
                          onChange={handleChange}
                          variant="outlined"
                        />
                      )}
                    />
                  </CardContent>
                )}
                {values.scope === enforcementScopeDict['Environment'] && (
                  <CardContent>
                    <Autocomplete
                      id="environment"
                      disablePortal
                      options={environmentOptions}
                      onChange={(event, value) => {
                        setFieldValue('environment', value.value);
                      }}
                      renderInput={(params) => (
                        <TextField
                          {...params}
                          fullWidth
                          error={Boolean(
                            touched.environment && errors.environment
                          )}
                          helperText={touched.environment && errors.environment}
                          label="Environment"
                          onChange={handleChange}
                          variant="outlined"
                        />
                      )}
                    />
                  </CardContent>
                )}
                {values.scope === enforcementScopeDict['Dataset'] && (
                  <CardContent>
                    <Autocomplete
                      id="dataset"
                      disablePortal
                      options={datasetOptions}
                      onChange={(event, value) => {
                        setFieldValue('dataset', value.value);
                      }}
                      renderInput={(params) => (
                        <TextField
                          {...params}
                          fullWidth
                          error={Boolean(touched.dataset && errors.dataset)}
                          helperText={touched.dataset && errors.dataset}
                          label="Dataset"
                          onChange={handleChange}
                          variant="outlined"
                        />
                      )}
                    />
                  </CardContent>
                )}
                <CardContent>
                  <Autocomplete
                    id="severity"
                    disablePortal
                    options={severityOptions.map((option) => {
                      return {
                        label: option.name,
                        value: option.value
                      };
                    })}
                    onChange={(event, value) => {
                      setFieldValue('severity', value.value);
                    }}
                    defaultValue={severityOptions[0].value}
                    renderInput={(params) => (
                      <TextField
                        {...params}
                        fullWidth
                        error={Boolean(touched.severity && errors.severity)}
                        helperText={touched.severity && errors.severity}
                        label="Severity"
                        onChange={handleChange}
                        variant="outlined"
                      />
                    )}
                  />
                </CardContent>
                <CardContent>
                  <Grid container spacing={2}>
                    {entityTypes.map((entityType) => (
                      <Grid item lg={4} xl={4}>
                        <FormControlLabel
                          control={
                            <Checkbox
                              disabled={entityType.disabled}
                              checked={values.entityTypes.includes(
                                entityType.name
                              )}
                              id={entityType.name}
                              onChange={(event, value) => {
                                if (value) {
                                  setFieldValue('entityTypes', [
                                    ...values.entityTypes,
                                    entityType.name
                                  ]);
                                } else {
                                  setFieldValue(
                                    'entityTypes',
                                    values.entityTypes.filter(
                                      (item) => item !== entityType.name
                                    )
                                  );
                                }
                              }}
                            />
                          }
                          label={entityType.name}
                        />
                      </Grid>
                    ))}
                  </Grid>
                </CardContent>
                <CardContent>
                  <LoadingButton
                    fullWidth
                    startIcon={<SendIcon fontSize="small" />}
                    color="primary"
                    disabled={isSubmitting}
                    type="submit"
                    variant="contained"
                  >
                    Create
                  </LoadingButton>

                  <Button
                    sx={{ mt: 2 }}
                    onClick={onCancel}
                    fullWidth
                    color="primary"
                    variant="outlined"
                    disabled={isSubmitting}
                  >
                    Cancel
                  </Button>
                </CardContent>
              </Box>
            </form>
          )}
        </Formik>
      </Box>
    </Dialog>
  );
};

export const MetadataFormEnforcement = (props) => {
  const { canEdit, metadataForm } = props;
  const client = useClient();
  const theme = useTheme();
  const dispatch = useDispatch();
  const [showCreateRuleModal, setShowCreateRuleModal] = useState(false);
  const [rules, setRules] = useState([]);
  const [selectedRule, setSelectedRule] = useState(null);
  const [severityOptions, setSeverityOptions] = useState({});
  const [entityTypesOptions, setEntityTypesOptions] = useState({});
  const [enforcementScopeOptions, setEnforcementScopeOptions] = useState({});
  const [affectedEntities, setAffectedEntities] = useState([]);
  const [paginationModel, setPaginationModel] = useState({
    pageSize: 5,
    page: 0
  });
  const [selectedEntity, setSelectedEntity] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingAffected, setLoadingAffected] = useState(true);

  const header = [
    { field: 'type', width: 150, headerName: 'Type', editable: false },
    { field: 'name', width: 300, headerName: 'Name', editable: false },
    { field: 'owner', width: 200, headerName: 'Owner', editable: false },
    {
      field: 'attached',
      width: 100,
      headerName: 'Attached',
      editable: false,
      renderCell: (params) => {
        return (
          <Label color={params.row.attached ? 'success' : 'error'}>
            {params.row.attached ? 'Yes' : 'No'}
          </Label>
        );
      }
    }
  ];

  const fetchEntityTypesWithScope = async () => {
    const response = await client.query(listEntityTypesWithScope());
    if (
      !response.errors &&
      response.data &&
      response.data.listEntityTypesWithScope
    ) {
      setEntityTypesOptions(response.data.listEntityTypesWithScope);
    } else {
      const error = 'Could not fetch entity types';
      dispatch({ type: SET_ERROR, error });
    }
  };

  const fetchEnforcementRules = async () => {
    setLoading(true);
    const response = await client.query(
      listMetadataFormEnforcementRules(metadataForm.uri)
    );
    if (
      !response.errors &&
      response.data &&
      response.data.listMetadataFormEnforcementRules
    ) {
      setRules(response.data.listMetadataFormEnforcementRules);
      if (response.data.listMetadataFormEnforcementRules.length > 0) {
        setSelectedRule(response.data.listMetadataFormEnforcementRules[0]);
        await fetchAffectedEntities(
          response.data.listMetadataFormEnforcementRules[0]
        );
      }
    } else {
      const error = 'Could not fetch rules';
      dispatch({ type: SET_ERROR, error });
    }
    setLoading(false);
  };

  const deleteRule = async (rule_uri) => {
    const response = await client.mutate(
      deleteMetadataFormEnforcementRule(metadataForm.uri, rule_uri)
    );
    if (!response.errors) {
      if (selectedRule.uri === rule_uri) {
        setSelectedRule(null);
        setAffectedEntities([]);
      }
      await fetchEnforcementRules();
    } else {
      const error = 'Could not delete rule';
      dispatch({ type: SET_ERROR, error });
    }
  };

  const fetchAffectedEntities = async (
    rule,
    page = paginationModel.page,
    pageSize = paginationModel.pageSize
  ) => {
    setLoadingAffected(true);
    const response = await client.query(
      listEntityAffectedByEnforcementRules(rule.uri, {
        pageSize: pageSize,
        page: page + 1
      })
    );
    if (
      !response.errors &&
      response.data &&
      response.data.listEntityAffectedByEnforcementRules
    ) {
      response.data.listEntityAffectedByEnforcementRules.nodes.forEach(
        (entity) => {
          entity.id = entity.uri;
        }
      );
      setAffectedEntities(response.data.listEntityAffectedByEnforcementRules);
    } else {
      const error = 'Could not fetch affeceted entities';
      dispatch({ type: SET_ERROR, error });
    }
    setLoadingAffected(false);
  };

  const fetchEnforcementEnums = async () => {
    const enums = await fetchEnums(client, [
      'MetadataFormEnforcementSeverity',
      'MetadataFormEnforcementScope'
    ]);
    if (enums['MetadataFormEnforcementSeverity'].length > 0) {
      setSeverityOptions(enums['MetadataFormEnforcementSeverity']);
    } else {
      const error = 'Could not fetch enforcement severity options';
      dispatch({ type: SET_ERROR, error });
    }
    if (enums['MetadataFormEnforcementScope'].length > 0) {
      setEnforcementScopeOptions(enums['MetadataFormEnforcementScope']);
    } else {
      const error = 'Could not fetch enforcement scope options';
      dispatch({ type: SET_ERROR, error });
    }
  };

  useEffect(() => {
    if (client) {
      fetchEnforcementRules()
        .then()
        .catch((e) => dispatch({ type: SET_ERROR, error: e.message }));
      fetchEnforcementEnums().catch((e) =>
        dispatch({ type: SET_ERROR, error: e.message })
      );
      fetchEntityTypesWithScope().catch((e) =>
        dispatch({ type: SET_ERROR, error: e.message })
      );
    }
  }, [client]);

  return (
    <Box>
      <Grid
        container
        spacing={2}
        sx={{ height: 'calc(100vh - 320px)', mb: -5 }}
      >
        <Grid item lg={6} xl={6}>
          <Card sx={{ height: '100%' }}>
            <Grid container spacing={2}>
              <Grid item lg={8} xl={8}>
                <CardHeader title="Enforcement rules"></CardHeader>
              </Grid>
              <Grid
                item
                lg={4}
                xl={4}
                sx={{
                  textAlign: 'right'
                }}
              >
                {canEdit && (
                  <CardContent>
                    <Button
                      color="primary"
                      startIcon={<PlusIcon size={15} />}
                      type="button"
                      onClick={() => setShowCreateRuleModal(true)}
                    >
                      Add rule
                    </Button>
                  </CardContent>
                )}
              </Grid>
            </Grid>
            {rules.length > 0 && !loading ? (
              rules.map((rule) => (
                <CardContent
                  onClick={async () => {
                    setSelectedRule(rule);
                    await fetchAffectedEntities(rule);
                  }}
                  sx={{
                    backgroundColor:
                      selectedRule &&
                      selectedRule.uri === rule.uri &&
                      theme.palette.action.selected
                  }}
                >
                  <Grid container spacing={2}>
                    <Grid
                      item
                      lg={2}
                      xl={2}
                      sx={{
                        mt: 1
                      }}
                    >
                      <Typography color="textPrimary" variant="subtitle2">
                        {rule.severity}
                      </Typography>
                    </Grid>
                    <Grid item lg={3} xl={3}>
                      <Typography
                        color="textPrimary"
                        variant="subtitle2"
                        sx={{
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          maxLines: 1,
                          mt: 1
                        }}
                      >
                        {rule.level}
                      </Typography>
                    </Grid>
                    <Grid item lg={3} xl={3}>
                      <Typography
                        color="textPrimary"
                        variant="subtitle2"
                        sx={{
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          maxLines: 1,
                          mt: 1
                        }}
                      >
                        {rule.homeEntityName}
                      </Typography>
                    </Grid>
                    <Grid item lg={3} xl={3}>
                      {rule.entityTypes.map((et) => (
                        <Chip label={et} sx={{ mt: 1, mr: 1 }} />
                      ))}
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
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteRule(rule.uri);
                          }}
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
                  Metadata Form is not enforced
                </Typography>
              </CardContent>
            )}
            {loading && (
              <CardContent sx={{ display: 'flex', justifyContent: 'center' }}>
                <CircularProgress />
              </CardContent>
            )}
          </Card>
        </Grid>
        <Grid item lg={6} xl={6}>
          <Card sx={{ height: '100%' }}>
            <CardHeader title="Attached Entities" />
            <CardContent>
              {!loadingAffected &&
              affectedEntities.nodes &&
              affectedEntities.nodes.length > 0 ? (
                <DataGrid
                  rows={affectedEntities.nodes}
                  columns={header}
                  pageSize={paginationModel.pageSize}
                  rowsPerPageOptions={[5, 10, 20]}
                  onPageSizeChange={async (newPageSize) => {
                    setPaginationModel({
                      ...paginationModel,
                      pageSize: newPageSize
                    });
                    await fetchAffectedEntities(
                      selectedRule,
                      paginationModel.page,
                      newPageSize
                    );
                  }}
                  page={paginationModel.page}
                  onPageChange={async (newPage) => {
                    setPaginationModel({ ...paginationModel, page: newPage });
                    await fetchAffectedEntities(
                      selectedRule,
                      newPage,
                      paginationModel.pageSize
                    );
                  }}
                  rowCount={affectedEntities.count}
                  autoHeight={true}
                  onSelectionModelChange={async (newSelection) => {
                    setSelectedEntity(newSelection);
                  }}
                  selectionModel={selectedEntity}
                  hideFooterSelectedRowCount={true}
                />
              ) : (
                <Typography color="textPrimary" variant="subtitle2">
                  {loadingAffected ? '' : 'No entities affected.'}
                </Typography>
              )}
              {loadingAffected && selectedRule && (
                <CardContent sx={{ display: 'flex', justifyContent: 'center' }}>
                  <CircularProgress />
                </CardContent>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
      {showCreateRuleModal && (
        <CreateEnforcementRuleModal
          open={showCreateRuleModal}
          metadataForm={metadataForm}
          enforcementScopeOptions={enforcementScopeOptions}
          entityTypesOptions={entityTypesOptions}
          severityOptions={severityOptions}
          onSubmit={async (rule) => {
            setShowCreateRuleModal(false);
            fetchEnforcementRules().catch((e) =>
              dispatch({ type: SET_ERROR, error: e.message })
            );
          }}
          onCancel={() => setShowCreateRuleModal(false)}
        />
      )}
    </Box>
  );
};

MetadataFormEnforcement.propTypes = {
  metadataForm: PropTypes.any.isRequired
};
