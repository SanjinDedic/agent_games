import React, { useState,useEffect } from 'react';
import PureMarkdown from './Utilities/PureMarkdown';

function AgentHome() {
    const content = `Testing`
  
    return (
      <div style={{display:'flex'}}>
      <PureMarkdown content={content}/>
      </div>
    );
}

export default AgentHome;