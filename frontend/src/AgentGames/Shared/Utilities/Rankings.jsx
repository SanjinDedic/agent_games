import React, { useEffect } from 'react';
import ResultsDisplay from './ResultsDisplay';
import FeedbackSelector from '../../Feedback/FeedbackSelector';
import { toast } from 'react-toastify';
import moment from 'moment-timezone';
import { useDispatch, useSelector } from 'react-redux';
import { setAllRankings, setRanking } from '../../../slices/rankingsSlice';

function AgentRankings() {
  const dispatch = useDispatch();
  const apiUrl = useSelector((state) => state.settings.agentApiUrl);
  const rankingOutput = useSelector((state) => state.rankings.currentRanking);
  const allRankings = useSelector((state) => state.rankings.allRankings);

  moment.tz.setDefault("Australia/Sydney");

  useEffect(() => {
    fetch(`${apiUrl}/user/get-published-results-for-all-leagues`)
      .then(response => response.json())
      .then(data => {
        if (data.status === "success") {
          dispatch(setAllRankings(data.data.all_results));
        } else {
          toast.error(data.message || 'Failed to fetch rankings');
        }
      })
      .catch(() => toast.error('Failed to show results'));
  }, [apiUrl, dispatch]);

  return (
    <div className="w-full max-w-6xl mx-auto px-4 py-6">
      <div className="mb-6">
        <select
          onChange={(e) => dispatch(setRanking(e.target.value))}
          className="w-full max-w-md p-2 border border-ui-light rounded-lg bg-white text-ui-dark"
        >
          {allRankings.map((league, index) => {
            const isActive = moment().isBefore(moment(league.expiry_date));
            return (
              <option
                key={index}
                value={league.league_name}
                className={`${isActive ? 'text-success' : 'text-danger'}`}
              >
                {isActive ? '🟢' : '🔴'} {league.league_name}
              </option>
            );
          })}
        </select>
      </div>

      <div className="bg-white rounded-lg shadow-md p-6">
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
          <p className="text-center text-ui text-lg">Loading results...</p>
        )}
      </div>
    </div>
  );
}

export default AgentRankings;