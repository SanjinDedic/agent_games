import React, { useState } from 'react';

import { toast } from 'react-toastify';
import { useDispatch } from 'react-redux';
import { setRewards } from '../../slices/leaguesSlice';

const CustomRewards = () => {
  const dispatch = useDispatch();
  const [inputValue, setInputValue] = useState('');
  const [error, setError] = useState('');

  const handleInputChange = (event) => {
    const value = event.target.value;
    setInputValue(value);
    if (value.trim().endsWith(']')) {
      try {
        const parsed = JSON.parse(value);

        if (Array.isArray(parsed) && parsed.every(item => typeof item === 'number')) {
          dispatch(setRewards(parsed));
          setError('');

        } else {
          throw new Error();

        }
      } catch (e) {
        dispatch(setRewards(null));
        setError('Invalid input. Please enter a valid array of numbers like [10, 8, 5, 3].');
        toast.error('Invalid input. Please enter a valid array of numbers like [10, 8, 5, 3].');
      }
    } else {
      dispatch(setRewards(null));
      setError('Please type the correct format. Example: [10, 8, 5, 3]');
    }
  };

  return (
    <div style={{
      backgroundColor: "#f4f4f4",
      borderRadius: "8px",
      boxShadow: "0 4px 6px rgba(0, 0, 0, 0.1)",
      padding: "10px"
    }}>
      <label>
        Enter numbers (comma separated):
        <input
          type="text"
          value={inputValue}
          onChange={handleInputChange}
        />
      </label>
      {error && <p style={{ color: 'red' }}>{error}</p>}
    </div>
  );
};

export default CustomRewards;