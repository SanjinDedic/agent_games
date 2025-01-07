import React from 'react';
import Tooltip from '@mui/material/Tooltip';
import Zoom from '@mui/material/Zoom';
import { styled } from '@mui/material/styles';
import { tooltipClasses } from '@mui/material/Tooltip';
import { useSelector } from 'react-redux';

const CustomTooltip = styled(({ className, ...props }) => (
  <Tooltip {...props} classes={{ popper: className }} />
))({
  [`& .${tooltipClasses.tooltip}`]: {
    maxWidth: '600px',
    fontSize: '14px',
    backgroundColor: 'rgb(57, 94, 131)', // league-blue color
    color: '#ffffff',
    border: '1px solid rgb(37, 61, 85)', // ui-dark color
    padding: '10px',
    borderRadius: '0.375rem',
    boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)'
  }
});

const UserTooltip = ({ title, children, ...props }) => {
  const showTooltips = useSelector((state) => state.settings.showTooltips);

  return (
    <CustomTooltip
      open={showTooltips}
      title={<div dangerouslySetInnerHTML={{ __html: title }} />}
      TransitionComponent={Zoom}
      {...props}
    >
      {children}
    </CustomTooltip>
  );
};

export default UserTooltip;