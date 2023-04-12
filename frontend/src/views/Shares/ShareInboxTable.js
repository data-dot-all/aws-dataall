import {
  Box,
  Card,
  CardHeader,
  Container,
  Divider,
  IconButton,
  Link,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow
} from '@mui/material';
import CircularProgress from '@mui/material/CircularProgress';
import { useCallback, useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link as RouterLink } from 'react-router-dom';
import { Defaults, RefreshTableMenu, Scrollbar } from '../../components';
import { SET_ERROR, useDispatch } from '../../globalErrors';
import { useSettings } from '../../hooks';
import { ArrowRightIcon } from '../../icons';
import { getShareRequestsToMe, useClient } from '../../services';

const ShareInboxTable = () => {
  const dispatch = useDispatch();
  const [items, setItems] = useState(Defaults.pagedResponse);
  const [filter] = useState(Defaults.filter);
  const { settings } = useSettings();
  const [loading, setLoading] = useState(true);
  const client = useClient();
  const fetchItems = useCallback(async () => {
    setLoading(true);
    await client
      .query(
        getShareRequestsToMe({
          filter: {
            ...filter
          }
        })
      )
      .then((response) => {
        setItems(response.data.getShareRequestsToMe);
      })
      .catch((error) => {
        dispatch({ type: SET_ERROR, error: error.Error });
      })
      .finally(() => setLoading(false));
  }, [filter, dispatch, client]);

  useEffect(() => {
    if (client) {
      fetchItems().catch((error) => {
        dispatch({ type: SET_ERROR, error: error.message });
      });
    }
  }, [client, filter.page, dispatch, fetchItems]);

  return (
    <>
      <Helmet>
        <title>Shares Inbox | data.all</title>
      </Helmet>
      <Box
        sx={{
          backgroundColor: 'background.default',
          minHeight: '100%',
          py: 1
        }}
      >
        <Container maxWidth={settings.compact ? 'xl' : false}>
          <Box
            sx={{
              flexGrow: 1,
              mt: 3
            }}
          >
            <Card>
              <CardHeader
                action={<RefreshTableMenu refresh={fetchItems} />}
                title={<Box>Requests</Box>}
              />
              <Divider />
              <Scrollbar>
                <Box sx={{ minWidth: 600 }}>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Dataset</TableCell>
                        <TableCell>Requesters</TableCell>
                        <TableCell>AWS Account</TableCell>
                        <TableCell>Region</TableCell>
                        <TableCell>Actions</TableCell>
                      </TableRow>
                    </TableHead>
                    {loading ? (
                      <CircularProgress sx={{ mt: 1 }} />
                    ) : (
                      <TableBody>
                        {items.nodes.length > 0 ? (
                          items.nodes.map((share) => (
                            <TableRow hover key={share.shareUri}>
                              <TableCell>
                                <Link
                                  underline="hover"
                                  component={RouterLink}
                                  color="textPrimary"
                                  variant="subtitle2"
                                  to={`/dataset/${share.dataset.datasetUri}/overview`}
                                >
                                  {share.dataset.datasetName}
                                </Link>
                              </TableCell>
                              <TableCell>
                                {share.principal.principalName}
                              </TableCell>
                              <TableCell>
                                {share.principal.AwsAccountId}
                              </TableCell>
                              <TableCell>{share.principal.region}</TableCell>
                              <TableCell>
                                <IconButton onClick={() => true}>
                                  <ArrowRightIcon fontSize="small" />
                                </IconButton>
                              </TableCell>
                            </TableRow>
                          ))
                        ) : (
                          <TableRow hover>
                            <TableCell>No requests found</TableCell>
                          </TableRow>
                        )}
                      </TableBody>
                    )}
                  </Table>
                </Box>
              </Scrollbar>
            </Card>
          </Box>
        </Container>
      </Box>
    </>
  );
};

export default ShareInboxTable;
