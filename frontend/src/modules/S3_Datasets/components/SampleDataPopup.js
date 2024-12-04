import React from 'react';
import { Modal, Box, Button, Typography } from '@mui/material';
import SampleDataTableComponent from './SampleDataTableComponent';

const SampleDataPopup = ({
  open,
  sampleData,
  handleClose,
  handleRegenerate
}) => {
  return (
    <Modal open={open} onClose={handleClose}>
      <Box
        sx={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          bgcolor: 'background.paper',
          boxShadow: 24,
          p: 4
        }}
      >
        <SampleDataTableComponent data={sampleData} />
        <Typography variant="body1" color="textSecondary" gutterBottom>
          By clicking the button below, you agree to share this sample data with
          a third-party language model.
        </Typography>
        <Box display="flex" justifyContent="flex-end">
          <Button
            variant="contained"
            color="primary"
            onClick={handleRegenerate}
          >
            Accept and Regenerate
          </Button>{' '}
        </Box>
      </Box>
    </Modal>
  );
};

export default SampleDataPopup;
