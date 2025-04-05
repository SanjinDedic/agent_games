// src/AgentGames/Shared/League/LeagueCardList.jsx
import React, { useState, useEffect } from 'react';
import moment from 'moment-timezone';
import { toast } from 'react-toastify';
import { useSelector, useDispatch } from 'react-redux';
import { setCurrentLeague } from '../../../slices/leaguesSlice';
import LeagueCard from './LeagueCard';
import useLeagueAPI from '../hooks/useLeagueAPI';

const LeagueCardList = ({ userRole }) => {
  const dispatch = useDispatch();
  const leagues = useSelector((state) => state.leagues.list);
  const currentLeague = useSelector((state) => state.leagues.currentLeague);
  const teams = useSelector((state) => state.teams.list);
  const [isDeleting, setIsDeleting] = useState(false);
  const [leagueTeamCounts, setLeagueTeamCounts] = useState({});
  
  // Use the shared API hook
  const { deleteLeague } = useLeagueAPI(userRole);

  // Calculate team counts for each league
  useEffect(() => {
    if (teams && teams.length > 0) {
      const counts = {};
      teams.forEach(team => {
        if (team.league) {
          counts[team.league] = (counts[team.league] || 0) + 1;
        }
      });
      setLeagueTeamCounts(counts);
    }
  }, [teams]);
  
  // Handle league selection
  const handleSelectLeague = (leagueName) => {
    dispatch(setCurrentLeague(leagueName));
  };
  
  // Handle league deletion
  const handleDeleteLeague = async (leagueName) => {
    if (leagueName.toLowerCase() === "unassigned") {
      toast.error("Cannot delete the 'unassigned' league");
      return;
    }
    
    if (!window.confirm(`Are you sure you want to delete league "${leagueName}"? All teams will be moved to the unassigned league.`)) {
      return;
    }
    
    setIsDeleting(true);
    try {
      const result = await deleteLeague(leagueName);
      if (result.success) {
        if (currentLeague?.name === leagueName && leagues.length > 0) {
          // Select another league if the current one is deleted
          const nextLeague = leagues.find(l => l.name !== leagueName);
          if (nextLeague) {
            dispatch(setCurrentLeague(nextLeague.name));
          }
        }
        toast.success(`League "${leagueName}" deleted successfully`);
      }
    } catch (error) {
      toast.error(`Failed to delete league: ${error.message}`);
    } finally {
      setIsDeleting(false);
    }
  };
  
  // Sort leagues: active first, then alphabetically
  const sortedLeagues = [...leagues].sort((a, b) => {
    const aActive = moment().isBefore(moment(a.expiry_date));
    const bActive = moment().isBefore(moment(b.expiry_date));
    
    if (aActive && !bActive) return -1;
    if (!aActive && bActive) return 1;
    return a.name.localeCompare(b.name);
  });
  
  return (
    <div className="h-[252px] overflow-y-auto overflow-x-hidden pr-2">
      <div className="grid grid-cols-2 gap-2 pb-1">
        {sortedLeagues.map((league) => (
          <LeagueCard
            key={league.id}
            league={league}
            isSelected={currentLeague?.name === league.name}
            onSelect={handleSelectLeague}
            onDelete={handleDeleteLeague}
            teamCount={leagueTeamCounts[league.name] || 0}
          />
        ))}
      </div>
      {leagues.length === 0 && (
        <div className="p-4 bg-ui-lighter rounded-lg text-center text-ui">
          No leagues available. Create one to get started.
        </div>
      )}
    </div>
  );
};

export default LeagueCardList;