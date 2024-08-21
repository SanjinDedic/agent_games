import React, { useState, useEffect } from 'react';
import Tooltip from '@mui/material/Tooltip';
import Zoom from '@mui/material/Zoom';
import { styled } from '@mui/material/styles';
import { tooltipClasses } from '@mui/material/Tooltip';
import { useSelector } from 'react-redux';

const NoMaxWidthTooltip = styled(({ className, ...props }) => (
  <Tooltip {...props} classes={{ popper: className }} />
))({
  [`& .${tooltipClasses.tooltip}`]: {
    maxWidth: '600px', // or any other custom styles
    fontSize: '14px',
    backgroundColor: '#395e83',
    color: '#ffffff',
    border: '1px solid #253d55',
    padding: '10px'
  },
});


const UserTooltip = ({ title, children, ...props }) => {
  const showTooltips = useSelector((state) => state.settings.showTooltips);

    return (
        <NoMaxWidthTooltip open={showTooltips} title={<div dangerouslySetInnerHTML={{ __html: title }} />}
        TransitionComponent={Zoom}
        
        {...props}>
            {children}
        </NoMaxWidthTooltip>
    );
};


export default UserTooltip;