import React, { useState } from 'react';
import './css/adminleague.css';

const CustomRewards = () => {
    const [inputValue, setInputValue] = useState('');
    
    const handleInputChange = (event) => {
        const value = event.target.value;
        setInputValue(value);
        
    };

    
    return (
        <div style={{backgroundColor: "#f4f4f4",
            borderRadius: "8px",
            boxShadow: "0 4px 6px rgba(0, 0, 0, 0.1)",
            padding: "10px"}}>
      <label>
        Enter numbers (comma separated):
      <input
        type="text"
        value={inputValue}
        onChange={handleInputChange}
      />
      </label>
    </div>
      );
    };
  
  export default CustomRewards;