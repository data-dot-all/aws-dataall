import { createContext, useEffect, useReducer } from 'react';
import { SET_ERROR } from '../../globalErrors';
import PropTypes from 'prop-types';
import { useAuth } from 'react-oidc-context';
import { Auth } from 'aws-amplify';

const CUSTOM_AUTH = process.env.REACT_APP_CUSTOM_AUTH;

const initialState = {
  isAuthenticated: false,
  isInitialized: false,
  user: null,
  reAuthStatus: false,
  requestInfo: null
};

const handlers = {
  INITIALIZE: (state, action) => {
    const { isAuthenticated, user, isInitialized } = action.payload;

    return {
      ...state,
      isAuthenticated,
      isInitialized,
      reAuthStatus: false,
      user
    };
  },
  LOGIN: (state, action) => {
    const { user } = action.payload;
    return {
      ...state,
      isAuthenticated: true,
      isInitialized: true,
      user
    };
  },
  LOGOUT: (state) => ({
    ...state,
    isAuthenticated: false,
    user: null
  }),
  REAUTH: (state, action) => {
    const { reAuthStatus, requestInfo } = action.payload;

    return {
      ...state,
      reAuthStatus,
      requestInfo
    };
  }
};

const reducer = (state, action) =>
  handlers[action.type] ? handlers[action.type](state, action) : state;

export const GenericAuthContext = createContext({
  ...initialState,
  platform: CUSTOM_AUTH ? CUSTOM_AUTH : 'Amplify',
  login: () => Promise.resolve(),
  logout: () => Promise.resolve(),
  reauth: () => Promise.resolve()
});

export const GenericAuthProvider = (props) => {
  const { children } = props;
  const [state, dispatch] = useReducer(reducer, initialState);
  const auth = useAuth();
  const isLoading = auth ? auth.isLoading : false;
  const userProfile = auth ? auth.user : null;
  const authEvents = auth ? auth.events : null;

  useEffect(() => {
    const initialize = async () => {
      try {
        const user = await getAuthenticatedUser();
        dispatch({
          type: 'INITIALIZE',
          payload: {
            isAuthenticated: true,
            isInitialized: true,
            user: {
              id: user.email,
              email: user.email,
              name: user.email,
              id_token: user.id_token,
              short_id: user.short_id,
              access_token: user.access_token
            }
          }
        });
      } catch (error) {
        if (CUSTOM_AUTH) {
          processLoadingStateChange();
        } else {
          dispatch({
            type: 'INITIALIZE',
            payload: {
              isAuthenticated: false,
              isInitialized: true,
              user: null
            }
          });
        }
      }
    };

    initialize().catch((e) => dispatch({ type: SET_ERROR, error: e.message }));
  }, []);

  // useEffect needed for React OIDC context
  // Process OIDC state when isLoading state changes
  useEffect(() => {
    if (CUSTOM_AUTH) {
      processLoadingStateChange();
    }
  }, [isLoading]);

  // useEffect to process when a user is loaded by react OIDC
  // This is triggered when the userProfile ( i.e. auth.user ) is loaded by react OIDC
  useEffect(() => {
    const processStateChange = async () => {
      try {
        const user = await getAuthenticatedUser();
        dispatch({
          type: 'LOGIN',
          payload: {
            user: {
              id: user.email,
              email: user.email,
              name: user.email,
              id_token: user.id_token,
              short_id: user.short_id,
              access_token: user.access_token
            }
          }
        });
      } catch (error) {
        dispatch({
          type: 'LOGOUT',
          payload: {
            isAuthenticated: false,
            user: null
          }
        });
      }
    };

    if (CUSTOM_AUTH) {
      processStateChange().catch((e) =>
        dispatch({ type: SET_ERROR, error: e.message })
      );
    }
  }, [userProfile]);

  // useEffect to process auth events generated by react OIDC
  // This is used to logout user when the token expires
  useEffect(() => {
    if (CUSTOM_AUTH) {
      return auth.events.addAccessTokenExpired(() => {
        auth.signoutSilent().then((r) => {
          dispatch({
            type: 'LOGOUT',
            payload: {
              isAuthenticated: false,
              user: null
            }
          });
        });
      });
    }
  }, [authEvents]);

  const getAuthenticatedUser = async () => {
    if (CUSTOM_AUTH) {
      if (!auth.user) throw Error('User not initialized');
      return {
        email:
          auth.user.profile[
            process.env.REACT_APP_CUSTOM_AUTH_EMAIL_CLAIM_MAPPING
          ],
        id_token: auth.user.id_token,
        access_token: auth.user.access_token,
        short_id:
          auth.user.profile[
            process.env.REACT_APP_CUSTOM_AUTH_USERID_CLAIM_MAPPING
          ]
      };
    } else {
      const user = await Auth.currentAuthenticatedUser();
      return {
        email: user.attributes.email,
        id_token: user.signInUserSession.idToken.jwtToken,
        access_token: user.signInUserSession.accessToken.jwtToken,
        short_id: 'none'
      };
    }
  };

  // Function to process OIDC State when it transitions from false to true
  function processLoadingStateChange() {
    if (isLoading) {
      dispatch({
        type: 'INITIALIZE',
        payload: {
          isAuthenticated: false,
          isInitialized: false, // setting to false when the OIDC State is loading
          user: null
        }
      });
    } else {
      dispatch({
        type: 'INITIALIZE',
        payload: {
          isAuthenticated: false,
          isInitialized: true, // setting to true when the OIDC state is completely loaded
          user: null
        }
      });
    }
  }

  const login = async () => {
    try {
      if (CUSTOM_AUTH) {
        await auth.signinRedirect();
      } else {
        await Auth.federatedSignIn();
      }
    } catch (error) {
      console.error('Failed to authenticate user', error);
    }
  };

  const logout = async () => {
    try {
      if (CUSTOM_AUTH) {
        await auth.signoutSilent();
        dispatch({
          type: 'LOGOUT',
          payload: {
            isAuthenticated: false,
            user: null
          }
        });
      } else {
        await Auth.signOut({ global: true });
        dispatch({
          type: 'LOGOUT',
          payload: {
            isAuthenticated: false,
            user: null
          }
        });
      }
      sessionStorage.removeItem('window-location');
    } catch (error) {
      console.error('Failed to signout', error);
    }
  };

  const reauth = async () => {
    if (CUSTOM_AUTH) {
      try {
        auth.signoutSilent().then((r) => {
          dispatch({
            type: 'REAUTH',
            payload: {
              reAuthStatus: false,
              requestInfo: null
            }
          });
        });
      } catch (error) {
        console.error('Failed to ReAuth', error);
      }
    } else {
      await Auth.signOut({ global: true });
      dispatch({
        type: 'REAUTH',
        payload: {
          reAuthStatus: false,
          requestInfo: null
        }
      });
    }
    sessionStorage.removeItem('window-location');
  };

  return (
    <GenericAuthContext.Provider
      value={{
        ...state,
        dispatch,
        platform: CUSTOM_AUTH ? CUSTOM_AUTH : 'Amplify',
        login,
        logout,
        reauth,
        isLoading
      }}
    >
      {children}
    </GenericAuthContext.Provider>
  );
};

GenericAuthContext.propTypes = {
  children: PropTypes.node.isRequired
};
