import React from 'react';
import { Grid, Typography, Paper, Button } from '@mui/material';

const SubitemDescriptionsGrid = ({ subitemDescriptions, onClose, onSave }) => {
  return (
    <div>
      <Paper elevation={3}>
        <Grid container>
          <Grid item xs={12}>
            <Grid container>
              <Grid item xs={4}>
                <Typography color="textSecondary" variant="h6" paddingLeft={15}>
                  Label
                </Typography>
              </Grid>
              <Grid item xs={8}>
                <Typography color="textSecondary" variant="h6">
                  Description
                </Typography>
              </Grid>
            </Grid>
          </Grid>
          {subitemDescriptions.map((item) => (
            <Grid item xs={12} key={item.subitem_id}>
              <Grid container>
                <Grid item xs={4}>
                  <Typography
                    color="textPrimary"
                    variant="body2"
                    component="div"
                    paddingLeft={15}
                  >
                    {item.label}
                  </Typography>
                </Grid>
                <Grid item xs={8}>
                  <Typography
                    color="textPrimary"
                    variant="body2"
                    component="div"
                  >
                    {item.description}
                  </Typography>
                </Grid>
              </Grid>
            </Grid>
          ))}
        </Grid>
        <Grid container justifyContent="flex-end" padding={2}>
          <Grid item alignSelf="flex-end">
            <Button
              color="inherit"
              variant="contained"
              type="button"
              size="small"
              style={{ marginRight: 8 }}
              onClick={onClose}
            >
              Close
            </Button>
            <Button
              color="inherit"
              variant="contained"
              type="button"
              size="small"
              style={{ marginRight: 8 }}
              onClick={onSave}
            >
              Save
            </Button>
          </Grid>
        </Grid>
      </Paper>
    </div>
  );
};

export default SubitemDescriptionsGrid;
