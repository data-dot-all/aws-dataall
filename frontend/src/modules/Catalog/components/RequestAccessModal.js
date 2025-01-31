import SendIcon from '@mui/icons-material/Send';
import { LoadingButton } from '@mui/lab';
import {
  Autocomplete,
  Box,
  Button,
  CardContent,
  CircularProgress,
  Dialog,
  FormControlLabel,
  FormGroup,
  FormHelperText,
  Switch,
  TextField,
  Typography
} from '@mui/material';
import { Formik } from 'formik';
import { useSnackbar } from 'notistack';
import PropTypes from 'prop-types';
import React, { useCallback, useEffect, useState } from 'react';
import * as Yup from 'yup';
import { Defaults } from 'design';
import { SET_ERROR, useDispatch } from 'globalErrors';
import {
  createShareObject,
  listEnvironmentConsumptionRoles,
  listEnvironmentGroups,
  listValidEnvironments,
  requestDashboardShare,
  getConsumptionRolePolicies,
  fetchEnums,
  useClient
} from 'services';
import { ShareEditForm } from '../../Shared/Shares/ShareEditForm';
import { getShareObject } from '../../Shares/services';
import { getDatasetExpirationDetails } from '../../DatasetsBase/services/getDatasetDetails';
import Checkbox from '@mui/material/Checkbox';

export const RequestAccessModal = (props) => {
  const { hit, onApply, onClose, open, stopLoader, ...other } = props;
  const { enqueueSnackbar } = useSnackbar();
  const dispatch = useDispatch();
  const client = useClient();
  const [environmentOptions, setEnvironmentOptions] = useState([]);
  const [loadingGroups, setLoadingGroups] = useState(false);
  const [loadingEnvs, setLoadingEnvs] = useState(false);
  const [groupOptions, setGroupOptions] = useState([]);
  const [loadingRoles, setLoadingRoles] = useState(false);
  const [loadingPolicies, setLoadingPolicies] = useState(false);
  const [roleOptions, setRoleOptions] = useState([]);
  const [isSharePolicyAttached, setIsSharePolicyAttached] = useState(true);
  const [unAttachedPolicyNames, setUnAttachedPolicyNames] = useState('');

  const [step, setStep] = useState(0);
  const [share, setShare] = useState(false);
  const [loading, setLoading] = useState(false);
  const [alreadyExisted, setAlreadyExisted] = useState(false);
  const [datasetExpirationDetails, setDatasetExpirationDetails] = useState({
    enableExpiration: false
  });
  const [requestNonExpirableShare, setNonExpirableShare] = useState(false);
  const [dataPermsEnum, setDataPermsEnum] = useState([]);

  const fetchDataPermsEnum = useCallback(async () => {
    const backendEnumName = 'ShareObjectDataPermission';
    const backendEnumData = (await fetchEnums(client, [backendEnumName]))[
      backendEnumName
    ];
    if (backendEnumData) setDataPermsEnum(backendEnumData.map((e) => e.value));
    else
      dispatch({
        type: SET_ERROR,
        error: `Could not fetch enum: ${backendEnumName}`
      });
  }, [client, dispatch]);

  const fetchEnvironments = useCallback(async () => {
    setStep(0);
    setLoadingEnvs(true);
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
    } finally {
      setLoadingEnvs(false);
      stopLoader();
    }
  }, [client, dispatch, stopLoader]);

  const fetchShareObject = async (shareUri) => {
    const response = await client.query(getShareObject({ shareUri: shareUri }));
    if (!response.errors) {
      setShare(response.data.getShareObject);
    } else {
      dispatch({ type: SET_ERROR, error: response.errors[0].message });
    }
  };

  const fetchGroups = async (environmentUri) => {
    setLoadingGroups(true);
    try {
      const response = await client.query(
        listEnvironmentGroups({
          filter: Defaults.selectListFilter,
          environmentUri: environmentUri
        })
      );
      if (!response.errors) {
        setGroupOptions(
          response.data.listEnvironmentGroups.nodes.map((g) => ({
            value: g.groupUri,
            label: g.groupUri
          }))
        );
      } else {
        dispatch({ type: SET_ERROR, error: response.errors[0].message });
      }
    } catch (e) {
      dispatch({ type: SET_ERROR, error: e.message });
    } finally {
      setLoadingGroups(false);
    }
  };

  const fetchRoles = async (environmentUri, groupUri) => {
    setLoadingRoles(true);
    try {
      const response = await client.query(
        listEnvironmentConsumptionRoles({
          filter: { ...Defaults.selectListFilter, groupUri: groupUri },
          environmentUri
        })
      );
      if (!response.errors) {
        setRoleOptions(
          response.data.listEnvironmentConsumptionRoles.nodes.map((g) => ({
            value: g.consumptionRoleUri,
            label: [g.consumptionRoleName, ' [', g.IAMRoleArn, ']'].join(''),
            IAMRoleName: g.IAMRoleName,
            dataallManaged: g.dataallManaged
          }))
        );
      } else {
        dispatch({ type: SET_ERROR, error: response.errors[0].message });
      }
    } catch (e) {
      dispatch({ type: SET_ERROR, error: e.message });
    } finally {
      setLoadingRoles(false);
    }
  };

  const fetchRolePolicies = async (environmentUri, IAMRoleName) => {
    setLoadingPolicies(true);
    try {
      const response = await client.query(
        getConsumptionRolePolicies({
          environmentUri,
          IAMRoleName
        })
      );
      if (!response.errors) {
        let isSharePoliciesAttached = response.data.getConsumptionRolePolicies
          .filter((policy) => policy.policy_type === 'SharePolicy')
          .map((policy) => policy.attached);
        const isAllPoliciesAttached = isSharePoliciesAttached.every(
          (value) => value === true
        );
        setIsSharePolicyAttached(isAllPoliciesAttached);
        let policyNameList = response.data.getConsumptionRolePolicies
          .filter((policy) => {
            return (
              policy.policy_type === 'SharePolicy' && policy.attached === false
            );
          })
          .map((policy) => policy.policy_name);
        setUnAttachedPolicyNames(policyNameList);
      } else {
        dispatch({ type: SET_ERROR, error: response.errors[0].message });
      }
    } catch (e) {
      dispatch({ type: SET_ERROR, error: e.message });
    } finally {
      setLoadingPolicies(false);
    }
  };

  const fetchDatasetExpirationDetails = async (datasetUri) => {
    const response = await client.query(
      getDatasetExpirationDetails({
        datasetUri
      })
    );
    if (!response.errors) {
      setDatasetExpirationDetails({
        enableExpiration: response.data.getDataset.enableExpiration,
        expirySetting: response.data.getDataset.expirySetting,
        expiryMinDuration: response.data.getDataset.expiryMinDuration,
        expiryMaxDuration: response.data.getDataset.expiryMaxDuration
      });
    } else {
      dispatch({ type: SET_ERROR, error: response.errors[0].message });
    }
  };

  useEffect(() => {
    if (client && open) {
      fetchEnvironments().catch((e) =>
        dispatch({ type: SET_ERROR, error: e.message })
      );
      fetchDataPermsEnum();
      fetchDatasetExpirationDetails(hit._id).catch((e) => {
        dispatch({ type: SET_ERROR, error: e.message });
      });
    }
  }, [
    client,
    open,
    stopLoader,
    fetchEnvironments,
    fetchDataPermsEnum,
    dispatch
  ]);

  const formDatasetRequestObject = (inputObject) => {
    return {
      datasetUri: hit._id,
      input: inputObject
    };
  };

  const formItemRequestObject = (inputObject) => {
    let types = {
      table: 'DatasetTable',
      folder: 'DatasetStorageLocation'
    };
    return {
      datasetUri: hit.datasetUri,
      itemUri: hit._id,
      itemType: types[hit.resourceKind],
      input: inputObject
    };
  };

  const formRequestObject = (values) => {
    let type = values.consumptionRole ? 'ConsumptionRole' : 'Group';
    let principal = values.consumptionRole.value
      ? values.consumptionRole.value
      : values.groupUri;

    let inputObject = {
      environmentUri: values.environmentUri,
      groupUri: values.groupUri,
      principalId: principal,
      principalType: type,
      requestPurpose: values.comment,
      attachMissingPolicies: values.attachMissingPolicies,
      permissions: values.permissions,
      shareExpirationPeriod: datasetExpirationDetails.enableExpiration
        ? parseInt(values.shareExpirationPeriod)
        : null,
      nonExpirable: values.nonExpirable
    };

    if (hit.resourceKind === 'dataset') {
      return formDatasetRequestObject(inputObject);
    }
    if (hit.resourceKind === 'table' || hit.resourceKind === 'folder') {
      return formItemRequestObject(inputObject);
    }
  };

  async function submit(values, setStatus, setSubmitting, setErrors) {
    try {
      let response;

      if (hit.resourceKind === 'dashboard') {
        response = await client.mutate(
          requestDashboardShare(hit._id, values.groupUri)
        );
      } else {
        response = await client.mutate(
          createShareObject(formRequestObject(values))
        );
      }

      if (response && !response.errors) {
        setStatus({ success: true });
        setSubmitting(false);
        setLoading(true);

        if (hit.resourceKind === 'dashboard') {
          await fetchShareObject(response.data.requestDashboardShare.shareUri);
        } else {
          setAlreadyExisted(response.data.createShareObject.alreadyExisted);
          await fetchShareObject(response.data.createShareObject.shareUri);
        }
        setStep(1);
        setLoading(false);
        const message = response.data.createShareObject.alreadyExisted
          ? 'Redirecting to the existing share'
          : 'Draft share request created';
        enqueueSnackbar(message, {
          anchorOrigin: {
            horizontal: 'right',
            vertical: 'top'
          },
          variant: 'success'
        });
      } else {
        dispatch({ type: SET_ERROR, error: response.errors[0].message });
      }
    } catch (err) {
      console.error(err);
      setStatus({ success: false });
      setErrors({ submit: err.message });
      setSubmitting(false);
      dispatch({ type: SET_ERROR, error: err.message });
    }
  }

  const beforeApply = () => {
    setStep(0);
    onApply();
  };

  if (!hit || loadingEnvs) {
    return null;
  }

  return (
    <Dialog maxWidth="md" fullWidth onClose={onClose} open={open} {...other}>
      {step === 0 && (
        <Box sx={{ p: 3, minHeight: 800 }}>
          <Typography
            align="center"
            color="textPrimary"
            gutterBottom
            variant="h4"
          >
            Request Access
          </Typography>
          <Typography align="center" color="textSecondary" variant="subtitle2">
            Data access is requested for the whole requester Team or for the
            selected Consumption role. The request will be submitted to the data
            owners, track its progress in the Shares menu on the left.
          </Typography>
          <Box sx={{ p: 3 }}>
            <Formik
              initialValues={{
                environmentUri: '',
                comment: '',
                attachMissingPolicies: false,
                permissions: [dataPermsEnum[0]],
                shareExpirationPeriod: 0,
                nonExpirable: false
              }}
              validationSchema={Yup.object().shape({
                environmentUri: Yup.string().required(
                  '*Environment is required'
                ),
                groupUri: Yup.string().required('*Team is required'),
                consumptionRole: Yup.object(),
                comment: Yup.string().max(5000),
                shareExpirationPeriod:
                  datasetExpirationDetails.enableExpiration &&
                  !requestNonExpirableShare
                    ? Yup.number()
                        .min(
                          datasetExpirationDetails.expiryMinDuration,
                          `Minimum share expiration duration is ${
                            datasetExpirationDetails.expiryMinDuration
                          } ${
                            datasetExpirationDetails.expirySetting === 'Monthly'
                              ? 'month(s)'
                              : 'quarter(s)'
                          }`
                        )
                        .max(
                          datasetExpirationDetails.expiryMaxDuration,
                          `Maximum share expiration duration is ${
                            datasetExpirationDetails.expiryMaxDuration
                          } ${
                            datasetExpirationDetails.expirySetting === 'Monthly'
                              ? 'month(s)'
                              : 'quarter(s)'
                          }`
                        )
                        .required('Incorrect input provided')
                    : Yup.number().nullable(),
                nonExpirable: Yup.boolean()
              })}
              onSubmit={async (
                values,
                { setErrors, setStatus, setSubmitting }
              ) => {
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
                      {hit.resourceKind === 'table' && (
                        <TextField
                          fullWidth
                          disabled
                          label="Table name"
                          name="table"
                          value={hit.label}
                          variant="outlined"
                        />
                      )}
                      {hit.resourceKind === 'folder' && (
                        <TextField
                          fullWidth
                          disabled
                          label="Folder name"
                          name="folder"
                          value={hit.label}
                          variant="outlined"
                        />
                      )}
                      {hit.resourceKind === 'dataset' && (
                        <TextField
                          fullWidth
                          disabled
                          label="Dataset name"
                          name="dataset"
                          value={hit.label}
                          variant="outlined"
                        />
                      )}
                      {hit.resourceKind === 'dashboard' && (
                        <TextField
                          fullWidth
                          disabled
                          label="Dashboard name"
                          name="dashboard"
                          value={hit.label}
                          variant="outlined"
                        />
                      )}
                    </CardContent>
                    {hit.resourceKind !== 'dashboard' && (
                      <Box>
                        <CardContent>
                          <Autocomplete
                            id="environment"
                            disablePortal
                            options={environmentOptions.map((option) => option)}
                            onChange={(event, value) => {
                              setFieldValue('groupUri', '');
                              setFieldValue('consumptionRole', '');
                              if (value && value.environmentUri) {
                                setFieldValue(
                                  'environmentUri',
                                  value.environmentUri
                                );
                                fetchGroups(value.environmentUri).catch((e) =>
                                  dispatch({
                                    type: SET_ERROR,
                                    error: e.message
                                  })
                                );
                              } else {
                                setFieldValue('environmentUri', '');
                                setGroupOptions([]);
                                setRoleOptions([]);
                              }
                            }}
                            renderInput={(params) => (
                              <TextField
                                {...params}
                                fullWidth
                                error={Boolean(
                                  touched.environmentUri &&
                                    errors.environmentUri
                                )}
                                helperText={
                                  touched.environmentUri &&
                                  errors.environmentUri
                                }
                                label="Environment"
                                onChange={handleChange}
                                variant="outlined"
                              />
                            )}
                          />
                        </CardContent>
                        <CardContent>
                          {loadingGroups ? (
                            <CircularProgress size={10} />
                          ) : (
                            <Box>
                              {groupOptions.length > 0 ? (
                                <Autocomplete
                                  id="group"
                                  disablePortal
                                  options={groupOptions.map((option) => option)}
                                  onChange={(event, value) => {
                                    setFieldValue('consumptionRole', '');
                                    if (value && value.value) {
                                      setFieldValue('groupUri', value.value);
                                      fetchRoles(
                                        values.environmentUri,
                                        value.value
                                      ).catch((e) =>
                                        dispatch({
                                          type: SET_ERROR,
                                          error: e.message
                                        })
                                      );
                                    } else {
                                      setFieldValue('groupUri', '');
                                      setRoleOptions([]);
                                    }
                                  }}
                                  renderInput={(params) => (
                                    <TextField
                                      {...params}
                                      fullWidth
                                      error={Boolean(
                                        touched.groupUri && errors.groupUri
                                      )}
                                      helperText={
                                        touched.groupUri && errors.groupUri
                                      }
                                      label="Team"
                                      onChange={handleChange}
                                      variant="outlined"
                                    />
                                  )}
                                />
                              ) : (
                                <TextField
                                  error={Boolean(
                                    touched.groupUri && errors.groupUri
                                  )}
                                  helperText={
                                    touched.groupUri && errors.groupUri
                                  }
                                  fullWidth
                                  disabled
                                  label="Team"
                                  value="No teams found for this environment"
                                  variant="outlined"
                                />
                              )}
                            </Box>
                          )}
                        </CardContent>
                        <CardContent>
                          <Autocomplete
                            multiple
                            disablePortal
                            fullWidth
                            options={dataPermsEnum}
                            getOptionLabel={(option) => option}
                            defaultValue={values.permissions}
                            onChange={(e, value) =>
                              setFieldValue('permissions', value)
                            }
                            renderInput={(params) => (
                              <TextField
                                {...params}
                                fullWidth
                                variant="outlined"
                                label="Permissions"
                              />
                            )}
                          />
                        </CardContent>
                        <CardContent>
                          {loadingRoles ? (
                            <CircularProgress size={10} />
                          ) : (
                            <Box>
                              {roleOptions.length > 0 ? (
                                <Autocomplete
                                  id="consumptionRole"
                                  disablePortal
                                  options={roleOptions.map((option) => option)}
                                  getOptionLabel={(option) => option.label}
                                  onChange={(event, value) => {
                                    setFieldValue('consumptionRole', value);
                                    if (value && value.IAMRoleName) {
                                      fetchRolePolicies(
                                        values.environmentUri,
                                        value.IAMRoleName
                                      ).catch((e) =>
                                        dispatch({
                                          type: SET_ERROR,
                                          error: e.message
                                        })
                                      );
                                    } else {
                                      setFieldValue('consumptionRole', '');
                                      setUnAttachedPolicyNames('');
                                    }
                                  }}
                                  renderInput={(params) => (
                                    <TextField
                                      {...params}
                                      fullWidth
                                      error={Boolean(
                                        touched.consumptionRole &&
                                          errors.consumptionRole
                                      )}
                                      helperText={
                                        touched.consumptionRole &&
                                        errors.consumptionRole
                                      }
                                      label="Consumption Role (optional)"
                                      onChange={handleChange}
                                      variant="outlined"
                                    />
                                  )}
                                />
                              ) : (
                                <TextField
                                  error={Boolean(
                                    touched.consumptionRole &&
                                      errors.consumptionRole
                                  )}
                                  helperText={
                                    touched.consumptionRole &&
                                    errors.consumptionRole
                                  }
                                  fullWidth
                                  disabled
                                  label="Consumption Role (optional)"
                                  value="No additional consumption roles owned by this Team in this Environment."
                                  variant="outlined"
                                />
                              )}
                            </Box>
                          )}
                        </CardContent>
                        <CardContent>
                          <Box>
                            {datasetExpirationDetails.enableExpiration && (
                              <>
                                <TextField
                                  error={Boolean(
                                    touched.shareExpirationPeriod &&
                                      errors.shareExpirationPeriod
                                  )}
                                  fullWidth
                                  helperText={
                                    touched.shareExpirationPeriod &&
                                    errors.shareExpirationPeriod
                                  }
                                  label={`Share Expiration Period - Request access for dataset in ${
                                    datasetExpirationDetails.expirySetting ===
                                    'Monthly'
                                      ? 'month(s)'
                                      : 'quarter(s)'
                                  }`}
                                  onBlur={handleBlur}
                                  onChange={(event, value) => {
                                    setFieldValue(
                                      'shareExpirationPeriod',
                                      event.target.value
                                    );
                                  }}
                                  variant="outlined"
                                  inputProps={{ type: 'number' }}
                                  disabled={requestNonExpirableShare}
                                />
                              </>
                            )}
                            {datasetExpirationDetails.enableExpiration && (
                              <Box sx={{ m: 1 }}>
                                <FormGroup>
                                  <FormControlLabel
                                    variant="outlined"
                                    label={
                                      'Request non-expiring share for this dataset'
                                    }
                                    control={
                                      <Checkbox
                                        defaultChecked={false}
                                        onChange={(event, value) => {
                                          setFieldValue('nonExpirable', value);
                                          setNonExpirableShare(value);
                                        }}
                                      />
                                    }
                                  />
                                </FormGroup>
                              </Box>
                            )}
                          </Box>
                        </CardContent>
                      </Box>
                    )}
                    {!values.consumptionRole ||
                    values.consumptionRole.dataallManaged ||
                    isSharePolicyAttached ? (
                      <Box />
                    ) : (
                      <CardContent sx={{ ml: 2 }}>
                        <FormControlLabel
                          control={
                            <Switch
                              checked={values.attachMissingPolicies}
                              onChange={handleChange}
                              color="primary"
                              edge="start"
                              name="attachMissingPolicies"
                            />
                          }
                          label={
                            <div>
                              Let Data.All attach policies to this role
                              <Typography
                                color="textSecondary"
                                component="p"
                                variant="caption"
                              ></Typography>
                              {values.consumptionRole &&
                              !(
                                values.consumptionRole.dataallManaged ||
                                isSharePolicyAttached ||
                                values.attachMissingPolicies
                              ) ? (
                                <FormHelperText error>
                                  Selected consumption role is managed by
                                  customer, but the share policy{' '}
                                  <strong>{unAttachedPolicyNames}</strong> is
                                  not attached.
                                  <br />
                                  Please attach it or let Data.all attach it for
                                  you.
                                </FormHelperText>
                              ) : (
                                ''
                              )}
                            </div>
                          }
                        />
                      </CardContent>
                    )}
                  </Box>
                  {isSubmitting || loading || loadingPolicies ? (
                    <CardContent>
                      <CircularProgress sx={{ ml: '45%' }} size={50} />
                    </CardContent>
                  ) : (
                    <CardContent>
                      <LoadingButton
                        fullWidth
                        startIcon={<SendIcon fontSize="small" />}
                        color="primary"
                        disabled={
                          isSubmitting ||
                          loading ||
                          (values.consumptionRole &&
                            !(
                              values.consumptionRole.dataallManaged ||
                              isSharePolicyAttached ||
                              values.attachMissingPolicies
                            ))
                        }
                        type="submit"
                        variant="contained"
                      >
                        Create Draft Request
                      </LoadingButton>

                      <Button
                        sx={{ mt: 2 }}
                        onClick={onApply}
                        fullWidth
                        color="primary"
                        variant="outlined"
                        disabled={isSubmitting || loading}
                      >
                        Cancel
                      </Button>
                    </CardContent>
                  )}
                </form>
              )}
            </Formik>
          </Box>
        </Box>
      )}
      {step === 1 && (
        <ShareEditForm
          share={share}
          alreadyExisted={alreadyExisted}
          dispatch={dispatch}
          enqueueSnackbar={enqueueSnackbar}
          client={client}
          onApply={beforeApply}
          onCancel={beforeApply}
          showViewShare={true}
        ></ShareEditForm>
      )}
    </Dialog>
  );
};

RequestAccessModal.propTypes = {
  hit: PropTypes.object.isRequired,
  onApply: PropTypes.func,
  onClose: PropTypes.func,
  open: PropTypes.bool.isRequired,
  stopLoader: PropTypes.func
};
