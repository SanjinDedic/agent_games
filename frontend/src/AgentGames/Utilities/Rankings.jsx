// Rankings.jsx
import React, { useState, useEffect } from 'react';
import ResultsDisplay from './ResultsDisplay';
import FeedbackSelector from './FeedbackSelector';
import { toast } from 'react-toastify';
import moment from 'moment-timezone';
import { useDispatch, useSelector } from 'react-redux';
import { setAllRankings, setRanking } from '../../slices/rankingsSlice';

function AgentRankings() {
  const dispatch = useDispatch();
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const rankingOutput = useSelector((state) => state.rankings.currentRanking);
  const allRankings = useSelector((state) => state.rankings.allRankings);
  
  moment.tz.setDefault("Australia/Sydney");

  useEffect(() => {
    fetch(`${apiUrl}/get_published_results_for_all_leagues`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    })
      .then(response => response.json())
      .then(data => {
        if (data.status === "success") {
          dispatch(setAllRankings(data.data.all_results));
        } else if (data.status === "failed") {
          toast.error(data.message);
        } else if (data.status === "error") {
          toast.error(data.message);
        }
      })
      .catch(error => {
        toast.error(`Failed to show results`);
      });
  }, []);

  const handleDropdownChange = (event) => {
    dispatch(setRanking(event.target.value));
  }

  return (
    <>
      <div className="main-container">
        <select onChange={handleDropdownChange}>
          {allRankings.map((league, index) => (
            <option 
              key={index} 
              value={league.league_name} 
              style={{ color: moment().isBefore(moment(league.expiry_date)) ? 'green' : 'red' }}
            >
              {moment().isBefore(moment(league.expiry_date)) ? '🟢' : '🔴'} {league.league_name}
            </option>
          ))}
        </select>
      </div>
      <div className="output-container">
        {rankingOutput ? (
          <>
            <ResultsDisplay 
              data={rankingOutput} 
              data_message={`Rankings for ${rankingOutput.league_name}`} 
              tablevisible={true} 
            />
            {rankingOutput.feedback && (
              <FeedbackSelector feedback={rankingOutput.feedback} />
            )}
          </>
        ) : (
          <p>Loading results...</p>
        )}
      </div>
    </>
  );
}

export default AgentRankings;