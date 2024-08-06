import SendIcon from '@mui/icons-material/Send';
import { LoadingButton } from '@mui/lab';
import {
  Box,
  Button,
  CardContent,
  CircularProgress,
  Dialog,
  TextField,
  Typography,
  Autocomplete
} from '@mui/material';
import { Formik } from 'formik';
import PropTypes from 'prop-types';
import React, { useEffect, useState } from 'react';
import { Defaults } from 'design';
import { SET_ERROR, useDispatch } from 'globalErrors';
import { listValidEnvironments, useClient, useGroups } from 'services';
import { listOrganizations } from '../../Organizations/services';
import { createMetadataForm } from '../services';

export const CreateMetadataFormModal = (props) => {
  const { visibilityDict, onApply, onClose, open, stopLoader, ...other } =
    props;
  const dispatch = useDispatch();
  const client = useClient();
  const groups = useGroups();
  const [loading, setLoading] = useState(false);
  const [environmentOptions, setEnvironmentOptions] = useState([]);
  const [organizationOptions, setOrganizationOptions] = useState([]);
  const [visibilityOptions, setVisibilityOptions] = useState([]);

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

  useEffect(() => {
    setVisibilityOptions(
      Object.entries(visibilityDict).map((elem) => {
        return { name: elem[0], value: elem[1] };
      })
    );

    if (client && open) {
      setLoading(true);
      fetchEnvironments().catch((e) =>
        dispatch({ type: SET_ERROR, error: e.message })
      );
      fetchOrganizations().catch((e) =>
        dispatch({ type: SET_ERROR, error: e.message })
      );
      setLoading(false);
      stopLoader();
    }
  }, [client, open, dispatch]);

  async function submit(values, setStatus, setSubmitting, setErrors) {
    try {
      let homeEntity = '';
      if (values.visibility === visibilityDict.Team) {
        homeEntity = values.group;
      }
      if (values.visibility === visibilityDict.Environment) {
        homeEntity = values.environment;
      }
      if (values.visibility === visibilityDict.Organization) {
        homeEntity = values.organization;
      }
      const response = await client.mutate(
        createMetadataForm({
          name: values.name,
          description: values.description,
          visibility: values.visibility,
          SamlGroupName: values.owner,
          homeEntity: homeEntity
        })
      );
      if (!response.errors) {
        setStatus({ success: true });
        setSubmitting(false);
        onApply();
      } else {
        setStatus({ success: false });
        setErrors({ submit: response.errors[0].message });
        setSubmitting(false);
      }
    } catch (err) {
      console.error(err);
      setStatus({ success: false });
      setErrors({ submit: err.message });
      setSubmitting(false);
      dispatch({ type: SET_ERROR, error: err.message });
    }
  }

  if (loading) {
    return null;
  }

  return (
    <Dialog maxWidth="md" fullWidth onClose={onClose} open={open} {...other}>
      <Box sx={{ p: 3 }}>
        <Typography
          align="center"
          color="textPrimary"
          gutterBottom
          variant="h4"
        >
          Create Metadata Form
        </Typography>
        <Formik
          initialValues={{
            name: '',
            description: '',
            visibility: visibilityDict.Global
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
                  <TextField
                    fullWidth
                    label="Form name"
                    name="name"
                    value={values.name}
                    onChange={handleChange}
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
                    label="Description"
                    name="description"
                    onChange={handleChange}
                    multiline
                    rows={3}
                    value={values.description}
                    variant="outlined"
                  />
                </CardContent>
                <CardContent>
                  <Autocomplete
                    id="owner"
                    disablePortal
                    options={groups}
                    onChange={(event, value) => {
                      setFieldValue('owner', value);
                    }}
                    renderInput={(params) => (
                      <TextField
                        {...params}
                        fullWidth
                        label="Owner"
                        onChange={handleChange}
                        variant="outlined"
                      />
                    )}
                  />
                </CardContent>
                <CardContent>
                  <Autocomplete
                    id="visibility"
                    disablePortal
                    value={values.visibility}
                    options={visibilityOptions.map((option) => option.value)}
                    onChange={(event, value) => {
                      setFieldValue('visibility', value);
                    }}
                    renderInput={(params) => (
                      <TextField
                        {...params}
                        fullWidth
                        label="Visibility"
                        onChange={handleChange}
                        variant="outlined"
                      />
                    )}
                  />
                </CardContent>
                {values.visibility === visibilityDict.Organization && (
                  <CardContent>
                    <Autocomplete
                      id="organization"
                      disablePortal
                      visibility={
                        values.visibility === visibilityDict['Organization']
                      }
                      onChange={(event, value) => {
                        setFieldValue('organization', value.value);
                      }}
                      options={organizationOptions.map((option) => option)}
                      renderInput={(params) => (
                        <TextField
                          {...params}
                          fullWidth
                          label="Organization"
                          onChange={handleChange}
                          variant="outlined"
                        />
                      )}
                    />
                  </CardContent>
                )}
                {values.visibility === visibilityDict.Environment && (
                  <CardContent>
                    <Autocomplete
                      id="environment"
                      disablePortal
                      options={environmentOptions.map((option) => option)}
                      onChange={(event, value) => {
                        setFieldValue('environment', value.value);
                      }}
                      renderInput={(params) => (
                        <TextField
                          {...params}
                          fullWidth
                          label="Environment"
                          onChange={handleChange}
                          variant="outlined"
                        />
                      )}
                    />
                  </CardContent>
                )}
                {values.visibility === visibilityDict.Team && (
                  <CardContent>
                    <Autocomplete
                      id="group"
                      disablePortal
                      options={groups}
                      onChange={(event, value) => {
                        setFieldValue('group', value);
                      }}
                      renderInput={(params) => (
                        <TextField
                          {...params}
                          fullWidth
                          label="Team"
                          onChange={handleChange}
                          variant="outlined"
                        />
                      )}
                    />
                  </CardContent>
                )}
              </Box>
              {isSubmitting ? (
                <CardContent>
                  <CircularProgress sx={{ ml: '45%' }} size={50} />
                </CardContent>
              ) : (
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
                    onClick={onApply}
                    fullWidth
                    color="primary"
                    variant="outlined"
                    disabled={isSubmitting}
                  >
                    Cancel
                  </Button>
                </CardContent>
              )}
            </form>
          )}
        </Formik>
      </Box>
    </Dialog>
  );
};

CreateMetadataFormModal.propTypes = {
  onApply: PropTypes.func,
  onClose: PropTypes.func,
  open: PropTypes.bool.isRequired,
  stopLoader: PropTypes.func
};
