import React, { useEffect } from 'react';
import ResultsDisplay from './ResultsDisplay';
import FeedbackSelector from '../../Feedback/FeedbackSelector';
import { toast } from 'react-toastify';
import moment from 'moment-timezone';
import { useDispatch, useSelector } from 'react-redux';
import { fetchAllRankings, setRanking } from '../../../slices/rankingsSlice';

function AgentRankings() {
  const dispatch = useDispatch();
  const rankingOutput = useSelector((state) => state.rankings.currentRanking);
  const allRankings = useSelector((state) => state.rankings.allRankings);

  moment.tz.setDefault("Australia/Sydney");

  useEffect(() => {
    dispatch(fetchAllRankings()).then((res) => {
      if (res && res.success === false) {
        toast.error(res.error || 'Failed to fetch rankings');
      }
    });
  }, [dispatch]);

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