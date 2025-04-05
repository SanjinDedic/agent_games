import React from 'react';
import moment from 'moment-timezone';

const LeagueCard = ({ league, isSelected, onSelect, onDelete, teamCount = 0 }) => {
  const isActive = moment().isBefore(moment(league.expiry_date));
  
  const handleDelete = (e) => {
    e.stopPropagation(); // Prevent triggering onSelect when clicking delete
    onDelete(league.name);
  };
  
  return (
    <div 
      onClick={() => onSelect(league.name)}
      className={`
        p-3 rounded-lg border cursor-pointer transition-all h-[80px] flex flex-col justify-between
        ${isSelected 
          ? 'border-primary bg-primary-light/20' 
          : 'border-ui-light hover:border-primary-light bg-white'}
      `}
    >
      <div className="flex justify-between items-start">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${isActive ? 'bg-success' : 'bg-danger'}`}></div>
            <h3 className="font-medium truncate max-w-[150px]">{league.name}</h3>
          </div>
          <div className="text-xs text-ui mt-1">Game: {league.game}</div>
        </div>
        <button 
          onClick={handleDelete}
          className="p-1 rounded-full hover:bg-danger hover:text-white transition-colors"
          title="Delete league"
        >
          ×
        </button>
      </div>
      <div className="flex justify-between items-end">
        <div className="text-xs text-ui">{moment(league.expiry_date).format('MMM D, YYYY')}</div>
        <div className="text-xs font-medium">
          <span className="text-primary">{teamCount}</span> teams
        </div>
      </div>
    </div>
  );
};

export default LeagueCard;