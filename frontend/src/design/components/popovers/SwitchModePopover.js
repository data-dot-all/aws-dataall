import { IconButton, Tooltip } from '@mui/material';
import { useSettings } from 'design/hooks';
import { RefreshIcon } from 'design/icons';

/**
 * @description Toggle "advanced" / "basic" mode.
 * @returns {JSX.Element}
 */
export const SwitchModePopover = () => {
  const { settings, saveSettings } = useSettings();

  /**
   * @description Toggle mode.
   */
  const handleSwitch = () =>
    saveSettings({
      ...settings,
      isAdvancedMode: !settings.isAdvancedMode
    });

  return (
    <Tooltip title="Switch mode">
      <IconButton onClick={handleSwitch}>
        <RefreshIcon fontSize="small" />
      </IconButton>
    </Tooltip>
  );
};
