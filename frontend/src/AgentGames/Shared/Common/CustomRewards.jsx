// src/AgentGames/Shared/Common/CustomRewards.jsx
import React, { useState } from 'react';
import { toast } from 'react-toastify';
import { useDispatch } from 'react-redux';
import { setRewards } from '../../../slices/leaguesSlice';

/**
 * Shared component for setting custom rewards
 * Can be used by both Admin and Institution roles
 */
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
    <div className="bg-white rounded-lg shadow-lg p-4">
      <h3 className="font-medium text-lg text-ui-dark mb-2">Custom Rewards</h3>
      <div className="space-y-2">
        <label className="block text-sm text-ui">
          Enter rewards as a JSON array:
          <input
            type="text"
            value={inputValue}
            onChange={handleInputChange}
            placeholder="[10, 8, 6, 4, 3, 2, 1]"
            className="w-full mt-1 p-2 border border-ui-light rounded-lg text-base"
          />
        </label>
        {error && (
          <p className="text-sm text-danger">{error}</p>
        )}
        <div className="text-xs text-ui">
          <p>Default: [10, 8, 6, 4, 3, 2, 1]</p>
          <p>For Prisoner's Dilemma: [4, 0, 6, 0]</p>
        </div>
      </div>
    </div>
  );
};

export default CustomRewards;