import { CloudDownloadOutlined, CopyAllOutlined } from '@mui/icons-material';
import { LoadingButton } from '@mui/lab';
import Autocomplete from '@mui/lab/Autocomplete';
import {
  Box,
  Breadcrumbs,
  Button,
  Card,
  CardContent,
  CardHeader,
  CircularProgress,
  Container,
  Divider,
  FormControlLabel,
  FormGroup,
  FormHelperText,
  Grid,
  IconButton,
  Link,
  MenuItem,
  Switch,
  TextField,
  Typography
} from '@mui/material';
import { useTheme } from '@mui/styles';
import { Formik } from 'formik';
import { useSnackbar } from 'notistack';
import React, { useCallback, useEffect, useState } from 'react';
import { CopyToClipboard } from 'react-copy-to-clipboard/lib/Component';
import { Helmet } from 'react-helmet-async';
import { Link as RouterLink, useNavigate, useParams } from 'react-router-dom';
import * as Yup from 'yup';
import {
  ArrowLeftIcon,
  ChevronRightIcon,
  ChipInput,
  useSettings
} from 'design';
import { SET_ERROR, useDispatch } from 'globalErrors';
import {
  getOrganization,
  getTrustAccount,
  useClient,
  useGroups
} from 'services';
import {
  createEnvironment,
  getPivotRoleExternalId,
  getPivotRoleName,
  getPivotRolePresignedUrl
} from '../services';
import { AwsRegions } from 'utils';

const EnvironmentCreateForm = (props) => {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { enqueueSnackbar } = useSnackbar();
  const params = useParams();
  const client = useClient();
  const groups = useGroups();
  const theme = useTheme();
  const { settings } = useSettings();
  const [organization, setOrganization] = useState({});
  const [trustedAccount, setTrustedAccount] = useState(null);
  const [pivotRoleName, setPivotRoleName] = useState(null);
  const [loading, setLoading] = useState(true);
  const groupOptions = groups
    ? groups.map((g) => ({ value: g, label: g }))
    : [];
  const fetchItem = useCallback(async () => {
    setLoading(true);
    const response = await client.query(getOrganization(params.uri));
    if (!response.errors) {
      setOrganization(response.data.getOrganization);
    } else {
      dispatch({ type: SET_ERROR, error: response.errors[0].message });
    }
    setLoading(false);
  }, [client, dispatch, params.uri]);
  const fetchTrustedAccount = useCallback(async () => {
    const response = await client.query(getTrustAccount());
    if (!response.errors) {
      setTrustedAccount(response.data.getTrustAccount);
    } else {
      dispatch({ type: SET_ERROR, error: response.errors[0].message });
    }
  }, [client, dispatch]);
  const getRoleName = useCallback(async () => {
    const response = await client.query(getPivotRoleName(params.uri));
    if (!response.errors) {
      setPivotRoleName(response.data.getPivotRoleName);
    } else {
      dispatch({ type: SET_ERROR, error: response.errors[0].message });
    }
  }, [client, dispatch, params.uri]);
  const getPivotRoleUrl = async () => {
    const response = await client.query(getPivotRolePresignedUrl(params.uri));
    if (!response.errors) {
      window.open(response.data.getPivotRolePresignedUrl, '_blank');
    } else {
      dispatch({ type: SET_ERROR, error: response.errors[0].message });
    }
  };

  const getCDKExecPolicyUrl = async () => {
    const response = await client.query(getCDKExecPolicyPresignedUrl(params.uri));
    if (!response.errors) {
      window.open(response.data.getCDKExecPolicyPresignedUrl, '_blank');
    } else {
      dispatch({ type: SET_ERROR, error: response.errors[0].message });
    }
  };

  const getExternalId = async () => {
    const response = await client.query(getPivotRoleExternalId(params.uri));
    if (!response.errors) {
      await navigator.clipboard.writeText(response.data.getPivotRoleExternalId);
      enqueueSnackbar('External Id copied to clipboard', {
        anchorOrigin: {
          horizontal: 'right',
          vertical: 'top'
        },
        variant: 'success'
      });
    } else {
      dispatch({ type: SET_ERROR, error: response.errors[0].message });
    }
  };
  const copyPivotRoleName = async () => {
    await navigator.clipboard.writeText(pivotRoleName);
    enqueueSnackbar('Pivot role name copied to clipboard', {
      anchorOrigin: {
        horizontal: 'right',
        vertical: 'top'
      },
      variant: 'success'
    });
  };
  const copyNotification = () => {
    enqueueSnackbar('Copied to clipboard', {
      anchorOrigin: {
        horizontal: 'right',
        vertical: 'top'
      },
      variant: 'success'
    });
  };
  useEffect(() => {
    if (client) {
      fetchTrustedAccount().catch((e) =>
        dispatch({ type: SET_ERROR, error: e.message })
      );
      getRoleName().catch((e) =>
        dispatch({ type: SET_ERROR, error: e.message })
      );
      fetchItem().catch((e) => dispatch({ type: SET_ERROR, error: e.message }));
    }
  }, [client, dispatch, fetchItem, fetchTrustedAccount, getRoleName]);

  async function submit(values, setStatus, setSubmitting, setErrors) {
    try {
      const response = await client.mutate(
        createEnvironment({
          organizationUri: organization.organizationUri,
          AwsAccountId: values.AwsAccountId,
          label: values.label,
          SamlGroupName: values.SamlGroupName,
          tags: values.tags,
          description: values.description,
          region: values.region,
          EnvironmentDefaultIAMRoleName: values.EnvironmentDefaultIAMRoleName,
          resourcePrefix: values.resourcePrefix,
          parameters: [
            {
              key: 'notebooksEnabled',
              value: String(values.notebooksEnabled)
            },
            {
              key: 'dashboardsEnabled',
              value: String(values.dashboardsEnabled)
            },
            {
              key: 'mlStudiosEnabled',
              value: String(values.mlStudiosEnabled)
            },
            {
              key: 'pipelinesEnabled',
              value: String(values.pipelinesEnabled)
            }
          ]
        })
      );
      if (!response.errors) {
        setStatus({ success: true });
        setSubmitting(false);
        enqueueSnackbar('Environment Created', {
          anchorOrigin: {
            horizontal: 'right',
            vertical: 'top'
          },
          variant: 'success'
        });
        navigate(
          `/console/environments/${response.data.createEnvironment.environmentUri}`
        );
      } else {
        dispatch({ type: SET_ERROR, error: response.errors[0].message });
      }
    } catch (err) {
      setStatus({ success: false });
      setErrors({ submit: err.message });
      setSubmitting(false);
      dispatch({ type: SET_ERROR, error: err.message });
    }
  }

  const regions = AwsRegions.map((region) => ({
    label: region.name,
    value: region.code
  }));

  if (loading) {
    return <CircularProgress />;
  }

  return (
    <>
      <Helmet>
        <title>Environments: Environment Create | data.all</title>
      </Helmet>
      <Box
        sx={{
          backgroundColor: 'background.default',
          minHeight: '100%',
          py: 8
        }}
      >
        <Container maxWidth={settings.compact ? 'xl' : false}>
          <Grid container justifyContent="space-between" spacing={3}>
            <Grid item>
              <Typography color="textPrimary" variant="h5">
                Create a new environment
              </Typography>
              <Breadcrumbs
                aria-label="breadcrumb"
                separator={<ChevronRightIcon fontSize="small" />}
                sx={{ mt: 1 }}
              >
                <Link
                  underline="hover"
                  color="textPrimary"
                  component={RouterLink}
                  to="/console/organizations"
                  variant="subtitle2"
                >
                  Organizations
                </Link>
                <Link
                  underline="hover"
                  color="textPrimary"
                  component={RouterLink}
                  to={`/console/organizations/${organization.organizationUri}`}
                  variant="subtitle2"
                >
                  {organization.label}
                </Link>
                <Link
                  underline="hover"
                  color="textPrimary"
                  component={RouterLink}
                  to={`/console/organizations/${organization.organizationUri}/link`}
                  variant="subtitle2"
                >
                  Link environment
                </Link>
              </Breadcrumbs>
            </Grid>
            <Grid item>
              <Box sx={{ m: -1 }}>
                <Button
                  color="primary"
                  component={RouterLink}
                  startIcon={<ArrowLeftIcon fontSize="small" />}
                  sx={{ mt: 1 }}
                  to={`/console/organizations/${organization.organizationUri}`}
                  variant="outlined"
                >
                  Cancel
                </Button>
              </Box>
            </Grid>
          </Grid>
          <Card sx={{ mt: 3 }}>
            <CardHeader title="Prerequisites" />
            <Divider />
            <CardContent>
              <Box>
                <Typography color="textSecondary" variant="subtitle2">
                  Bootstrap your AWS account with AWS CDK
                </Typography>
                <Typography color="textPrimary" variant="subtitle2">
                  <CopyToClipboard
                    onCopy={() => copyNotification()}
                    text={`cdk bootstrap --trust ${trustedAccount} -c @aws-cdk/core:newStyleStackSynthesis=true --cloudformation-execution-policies arn:aws:iam::aws:policy/AdministratorAccess aws://ACCOUNT_ID/REGION`}
                  >
                    <IconButton>
                      <CopyAllOutlined
                        sx={{
                          color:
                            theme.palette.mode === 'dark'
                              ? theme.palette.primary.contrastText
                              : theme.palette.primary.main
                        }}
                      />
                    </IconButton>
                  </CopyToClipboard>
                  {`cdk bootstrap --trust ${trustedAccount} -c @aws-cdk/core:newStyleStackSynthesis=true --cloudformation-execution-policies arn:aws:iam::aws:policy/AdministratorAccess aws://ACCOUNT_ID/REGION`}
                </Typography>
              </Box>
              <Box>
                <Typography color="textSecondary" variant="subtitle2">
                Use the below CloudFormation stack to create the custom IAM policy.
                </Typography>
                <Button
                            color="primary"
                            startIcon={<CloudDownloadOutlined fontSize="small" />}
                            sx={{ mt: 1, mb: 2, ml: 2 }}
                            variant="outlined"
                            onClick={() => {
                              getCDKExecPolicyUrl().catch((e) =>
                                dispatch({ type: SET_ERROR, error: e.message })
                              );
                            }}
                          >
                            CloudFormation stack for CDK custom execution policy
                </Button>
                <Typography color="textPrimary" variant="subtitle2">
                  <CopyToClipboard
                    onCopy={() => copyNotification()}
                    text={`cdk bootstrap --trust ${trustedAccount} -c @aws-cdk/core:newStyleStackSynthesis=true --cloudformation-execution-policies arn:aws:iam::ACCOUNT_ID:policy/DataAllCustomCDKPolicy aws://ACCOUNT_ID/REGION`}
                  >
                    <IconButton>
                      <CopyAllOutlined
                        sx={{
                          color:
                            theme.palette.mode === 'dark'
                              ? theme.palette.primary.contrastText
                              : theme.palette.primary.main
                        }}
                      />
                    </IconButton>
                  </CopyToClipboard>
                  {`cdk bootstrap --trust ${trustedAccount} -c @aws-cdk/core:newStyleStackSynthesis=true --cloudformation-execution-policies arn:aws:iam::ACCOUNT_ID:policy/DataAllCustomCDKPolicy aws://ACCOUNT_ID/REGION`}
                </Typography>
              </Box>
              {process.env.REACT_APP_ENABLE_PIVOT_ROLE_AUTO_CREATE ===
              'True' ? (
                <Box>
                  <Typography color="textSecondary" variant="subtitle2">
                    As part of the environment CloudFormation stack data.all
                    will create an IAM role (Pivot Role) to manage AWS
                    operations in the environment AWS Account.
                  </Typography>
                </Box>
              ) : (
                <Box>
                  <Box>
                    <Typography color="textSecondary" variant="subtitle2">
                      Create an IAM role named <b>{pivotRoleName}</b> using the
                      AWS CloudFormation stack below
                    </Typography>
                  </Box>
                  <Grid container justifyContent="space-between" spacing={3}>
                    <Grid item lg={6} xl={6} xs={6}>
                      <Button
                        color="primary"
                        startIcon={<CloudDownloadOutlined fontSize="small" />}
                        sx={{ mt: 1, mb: 2, ml: 2 }}
                        variant="outlined"
                        onClick={() => {
                          getPivotRoleUrl().catch((e) =>
                            dispatch({ type: SET_ERROR, error: e.message })
                          );
                        }}
                      >
                        CloudFormation stack
                      </Button>
                      <Button
                        color="primary"
                        startIcon={<CopyAllOutlined fontSize="small" />}
                        sx={{ mt: 1, mb: 2, ml: 2 }}
                        variant="outlined"
                        onClick={() => {
                          copyPivotRoleName().catch((e) =>
                            dispatch({ type: SET_ERROR, error: e.message })
                          );
                        }}
                      >
                        Pivot role name
                      </Button>
                      <Button
                        color="primary"
                        startIcon={<CopyAllOutlined fontSize="small" />}
                        sx={{ mt: 1, mb: 2, ml: 2 }}
                        variant="outlined"
                        onClick={() => {
                          getExternalId().catch((e) =>
                            dispatch({ type: SET_ERROR, error: e.message })
                          );
                        }}
                      >
                        External Id
                      </Button>
                    </Grid>
                  </Grid>
                </Box>
              )}
              <Box>
                <Typography color="textSecondary" variant="subtitle2">
                  Make sure that the services needed for the selected
                  environment features are available in your AWS Account.
                </Typography>
              </Box>
            </CardContent>
          </Card>
          <Box sx={{ mt: 3 }}>
            <Formik
              initialValues={{
                label: '',
                description: '',
                SamlGroupName: '',
                AwsAccountId: '',
                region: '',
                tags: [],
                dashboardsEnabled: true,
                notebooksEnabled: true,
                mlStudiosEnabled: true,
                pipelinesEnabled: true,
                EnvironmentDefaultIAMRoleName: '',
                resourcePrefix: 'dataall'
              }}
              validationSchema={Yup.object().shape({
                label: Yup.string()
                  .max(255)
                  .required('*Environment name is required'),
                description: Yup.string().max(5000),
                SamlGroupName: Yup.string()
                  .max(255)
                  .required('*Team is required'),
                AwsAccountId: Yup.number(
                  '*AWS account ID must be a number'
                ).required('*AWS account number is required'),
                region: Yup.string()
                  .required('*Region is required')
                  .test(
                    'region',
                    'Region is not supported',
                    (region) =>
                      regions.filter((option) =>
                        [option.label, option.value].includes(region)
                      ).length >= 1
                  ),
                tags: Yup.array().nullable(),
                privateSubnetIds: Yup.array().nullable(),
                publicSubnetIds: Yup.array().nullable(),
                vpcId: Yup.string().nullable(),
                EnvironmentDefaultIAMRoleName: Yup.string().nullable(),
                resourcePrefix: Yup.string()
                  .trim()
                  .matches(
                    '^[a-z-]*$',
                    '*Resource prefix is not valid (^[a-z-]*$)'
                  )
                  .min(1, '*Resource prefix must have at least 1 character')
                  .max(
                    20,
                    "*Resource prefix can't be longer than 20 characters"
                  )
                  .required('*Resource prefix is required')
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
                <form onSubmit={handleSubmit} {...props}>
                  <Grid container spacing={3}>
                    <Grid item lg={5} md={6} xs={12}>
                      <Card>
                        <CardHeader title="Details" />
                        <CardContent>
                          <TextField
                            error={Boolean(touched.label && errors.label)}
                            fullWidth
                            helperText={touched.label && errors.label}
                            label="Environment Name"
                            name="label"
                            onBlur={handleBlur}
                            onChange={handleChange}
                            value={values.label}
                            variant="outlined"
                          />
                        </CardContent>
                        <CardContent>
                          <TextField
                            FormHelperTextProps={{
                              sx: {
                                textAlign: 'right',
                                mr: 0
                              }
                            }}
                            fullWidth
                            helperText={`${
                              200 - values.description.length
                            } characters left`}
                            label="Short description"
                            name="description"
                            multiline
                            onBlur={handleBlur}
                            onChange={handleChange}
                            rows={5}
                            value={values.description}
                            variant="outlined"
                          />
                          {touched.description && errors.description && (
                            <Box sx={{ mt: 2 }}>
                              <FormHelperText error>
                                {errors.description}
                              </FormHelperText>
                            </Box>
                          )}
                        </CardContent>
                        <CardContent>
                          <ChipInput
                            fullWidth
                            error={Boolean(touched.tags && errors.tags)}
                            helperText={touched.tags && errors.tags}
                            variant="outlined"
                            label="Tags"
                            placeholder="Hit enter after typing value"
                            onChange={(chip) => {
                              setFieldValue('tags', [...chip]);
                            }}
                          />
                        </CardContent>
                      </Card>
                      <Box sx={{ mt: 3 }}>
                        <Card>
                          <CardHeader title="Features management" />
                          <CardContent>
                            <Box sx={{ ml: 2 }}>
                              <FormGroup>
                                <FormControlLabel
                                  color="primary"
                                  control={
                                    <Switch
                                      defaultChecked
                                      color="primary"
                                      onChange={handleChange}
                                      edge="start"
                                      name="dashboardsEnabled"
                                      value={values.dashboardsEnabled}
                                    />
                                  }
                                  label={
                                    <Typography
                                      color="textSecondary"
                                      gutterBottom
                                      variant="subtitle2"
                                    >
                                      Dashboards{' '}
                                      <small>
                                        (Requires Amazon QuickSight Enterprise
                                        Subscription)
                                      </small>
                                    </Typography>
                                  }
                                  labelPlacement="end"
                                  value={values.dashboardsEnabled}
                                />
                              </FormGroup>
                            </Box>
                            <Box sx={{ ml: 2 }}>
                              <FormGroup>
                                <FormControlLabel
                                  color="primary"
                                  control={
                                    <Switch
                                      defaultChecked
                                      color="primary"
                                      onChange={handleChange}
                                      edge="start"
                                      name="notebooksEnabled"
                                      value={values.notebooksEnabled}
                                    />
                                  }
                                  label={
                                    <Box>
                                      <Typography
                                        color="textSecondary"
                                        gutterBottom
                                        variant="subtitle2"
                                      >
                                        Notebooks{' '}
                                        <small>
                                          (Requires Amazon Sagemaker notebook
                                          instances)
                                        </small>
                                      </Typography>
                                    </Box>
                                  }
                                  labelPlacement="end"
                                  value={values.notebooksEnabled}
                                />
                              </FormGroup>
                            </Box>
                            <Box sx={{ ml: 2 }}>
                              <FormGroup>
                                <FormControlLabel
                                  color="primary"
                                  control={
                                    <Switch
                                      defaultChecked
                                      color="primary"
                                      onChange={handleChange}
                                      edge="start"
                                      name="mlStudiosEnabled"
                                      value={values.mlStudiosEnabled}
                                    />
                                  }
                                  label={
                                    <Typography
                                      color="textSecondary"
                                      gutterBottom
                                      variant="subtitle2"
                                    >
                                      ML Studio{' '}
                                      <small>
                                        (Requires Amazon Sagemaker Studio)
                                      </small>
                                    </Typography>
                                  }
                                  labelPlacement="end"
                                />
                              </FormGroup>
                            </Box>
                            <Box sx={{ ml: 2 }}>
                              <FormGroup>
                                <FormControlLabel
                                  color="primary"
                                  control={
                                    <Switch
                                      defaultChecked
                                      color="primary"
                                      onChange={handleChange}
                                      edge="start"
                                      name="pipelinesEnabled"
                                      value={values.pipelinesEnabled}
                                    />
                                  }
                                  label={
                                    <Typography
                                      color="textSecondary"
                                      gutterBottom
                                      variant="subtitle2"
                                    >
                                      Pipelines{' '}
                                      <small>(Requires AWS DevTools)</small>
                                    </Typography>
                                  }
                                  labelPlacement="end"
                                  value={values.pipelinesEnabled}
                                />
                              </FormGroup>
                            </Box>
                          </CardContent>
                        </Card>
                      </Box>
                    </Grid>
                    <Grid item lg={7} md={6} xs={12}>
                      <Box>
                        <Card>
                          <CardHeader title="Deployment" />
                          <CardContent>
                            <TextField
                              error={Boolean(
                                touched.AwsAccountId && errors.AwsAccountId
                              )}
                              fullWidth
                              helperText={
                                touched.AwsAccountId && errors.AwsAccountId
                              }
                              label="Account Number"
                              name="AwsAccountId"
                              onBlur={handleBlur}
                              onChange={handleChange}
                              value={values.AwsAccountId}
                              variant="outlined"
                            />
                          </CardContent>
                          <CardContent>
                            <Autocomplete
                              id="region"
                              freeSolo
                              options={regions.map((option) => option.label)}
                              onChange={(event, value) => {
                                const selectedRegion = regions.filter(
                                  (option) => option.label === value
                                );
                                setFieldValue(
                                  'region',
                                  selectedRegion
                                    ? selectedRegion[0].value
                                    : null
                                );
                              }}
                              renderInput={(regionParams) => (
                                <TextField
                                  {...regionParams}
                                  label="Region"
                                  margin="normal"
                                  error={Boolean(
                                    touched.region && errors.region
                                  )}
                                  helperText={touched.region && errors.region}
                                  onChange={handleChange}
                                  value={values.region}
                                  variant="outlined"
                                />
                              )}
                            />
                          </CardContent>
                          <CardContent>
                            <TextField
                              fullWidth
                              label="Team"
                              name="SamlGroupName"
                              error={Boolean(
                                touched.SamlGroupName && errors.SamlGroupName
                              )}
                              helperText={
                                touched.SamlGroupName && errors.SamlGroupName
                              }
                              onChange={handleChange}
                              select
                              value={values.SamlGroupName}
                              variant="outlined"
                            >
                              {groupOptions.map((group) => (
                                <MenuItem key={group.value} value={group.value}>
                                  {group.label}
                                </MenuItem>
                              ))}
                            </TextField>
                          </CardContent>
                          <CardContent>
                            <TextField
                              error={Boolean(
                                touched.resourcePrefix && errors.resourcePrefix
                              )}
                              fullWidth
                              helperText={
                                touched.resourcePrefix && errors.resourcePrefix
                              }
                              label="Resources Prefix"
                              placeholder="Prefix will be applied to All AWS resources created on this environment"
                              name="resourcePrefix"
                              onBlur={handleBlur}
                              onChange={handleChange}
                              value={values.resourcePrefix}
                              variant="outlined"
                            />
                          </CardContent>
                          <CardContent>
                            <TextField
                              error={Boolean(
                                touched.EnvironmentDefaultIAMRoleName &&
                                  errors.EnvironmentDefaultIAMRoleName
                              )}
                              fullWidth
                              helperText={
                                touched.EnvironmentDefaultIAMRoleName &&
                                errors.EnvironmentDefaultIAMRoleName
                              }
                              label="IAM Role Name"
                              placeholder="Bring your own IAM role (Optional)"
                              name="EnvironmentDefaultIAMRoleName"
                              onBlur={handleBlur}
                              onChange={handleChange}
                              value={values.EnvironmentDefaultIAMRoleName}
                              variant="outlined"
                            />
                          </CardContent>
                        </Card>
                      </Box>
                      {errors.submit && (
                        <Box sx={{ mt: 3 }}>
                          <FormHelperText error>{errors.submit}</FormHelperText>
                        </Box>
                      )}
                      <Box
                        sx={{
                          display: 'flex',
                          justifyContent: 'flex-end',
                          mt: 3
                        }}
                      >
                        <LoadingButton
                          color="primary"
                          loading={isSubmitting}
                          type="submit"
                          variant="contained"
                        >
                          Create Environment
                        </LoadingButton>
                      </Box>
                    </Grid>
                  </Grid>
                </form>
              )}
            </Formik>
          </Box>
        </Container>
      </Box>
    </>
  );
};

export default EnvironmentCreateForm;
