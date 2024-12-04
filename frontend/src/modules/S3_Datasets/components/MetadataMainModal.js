import { Dialog } from '@mui/material';
import PropTypes from 'prop-types';
import { useEffect, useState } from 'react';
import { Defaults } from 'design';
import { GenerateMetadataComponent } from './GenerateMetadataComponent';
import { ReviewMetadataComponent } from './ReviewMetadataComponent';

export const MetadataMainModal = (props) => {
  const { dataset, onApply, onClose, open, ...other } = props;
  const [currentView, setCurrentView] = useState('GENERATE_FORM');
  const [targetType, setTargetType] = useState('');
  const [targets, setTargets] = useState([]);
  const [targetOptions, setTargetOptions] = useState([]);
  const [selectedMetadataTypes, setSelectedMetadataTypes] = useState({
    label: false,
    description: false,
    tags: false,
    topics: false,
    subitem_descriptions: false
  });

  useEffect(() => {
    if (!open) {
      setCurrentView('GENERATE_FORM');
      setTargetType('');
      setTargets([]);
      setTargetOptions(Defaults.pagedResponse);
      setSelectedMetadataTypes({});
    }
  }, [open]);

  if (!dataset) {
    return null;
  }

  return (
    <Dialog maxWidth="lg" fullWidth onClose={onClose} open={open} {...other}>
      {currentView === 'GENERATE_FORM' && (
        <GenerateMetadataComponent
          dataset={dataset}
          targetType={targetType}
          setTargetType={setTargetType}
          targets={targets}
          setTargets={setTargets}
          targetOptions={targetOptions}
          setTargetOptions={setTargetOptions}
          selectedMetadataTypes={selectedMetadataTypes}
          setSelectedMetadataTypes={setSelectedMetadataTypes}
          currentView={currentView}
          setCurrentView={setCurrentView}
        />
      )}
      {currentView === 'REVIEW_METADATA' && (
        <ReviewMetadataComponent
          dataset={dataset}
          targetType={targetType}
          targets={targets}
          setTargets={setTargets}
          selectedMetadataTypes={selectedMetadataTypes}
        />
      )}
    </Dialog>
  );
};

MetadataMainModal.propTypes = {
  dataset: PropTypes.object.isRequired,
  onApply: PropTypes.func,
  onClose: PropTypes.func,
  open: PropTypes.bool.isRequired
};
