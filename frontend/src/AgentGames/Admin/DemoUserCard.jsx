import React, { useState } from "react";
import moment from "moment-timezone";

const DemoUserCard = ({ user, onDelete }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  // Format timestamp to a readable format
  const formatTimestamp = (timestamp) => {
    return moment(timestamp).format("MMM DD, YYYY HH:mm:ss");
  };

  // Calculate time elapsed since creation
  const getTimeElapsed = (timestamp) => {
    const now = moment();
    const created = moment(timestamp);
    return moment.duration(now.diff(created)).humanize() + " ago";
  };

  const toggleExpand = (e) => {
    // Prevent expanding when clicking the delete button
    if (e.target.closest(".delete-btn")) return;
    setIsExpanded(!isExpanded);
  };

  return (
    <div className="bg-white rounded-lg overflow-hidden shadow-sm border border-ui-light hover:shadow transition-shadow duration-200">
      <div
        onClick={toggleExpand}
        className="bg-league-blue text-white p-2 flex justify-between items-center cursor-pointer"
      >
        <div className="font-medium text-sm truncate">
          {user.demo_team_name}
        </div>
        <div className="flex items-center gap-1">
          <span className="text-xs text-league-text">
            {isExpanded ? "▲" : "▼"}
          </span>
          <button
            onClick={onDelete}
            className="delete-btn w-5 h-5 flex items-center justify-center bg-danger hover:bg-danger-hover text-white rounded-full transition-colors text-xs"
            title="Delete demo user"
          >
            ✕
          </button>
        </div>
      </div>

      <div className="p-2 text-sm">
        <div className="flex flex-col">
          <div className="text-ui-dark truncate">
            {user.email || "No email"}
          </div>
          <div className="text-ui">
            League: <span className="text-ui-dark">{user.league_name}</span>
          </div>
        </div>

        {isExpanded && (
          <div className="mt-2 pt-2 border-t border-ui-light">
            <div className="grid grid-cols-2 gap-x-2 gap-y-1 mb-2">
              <div className="text-ui">Team ID:</div>
              <div className="text-ui-dark">{user.demo_team_id}</div>

              <div className="text-ui">Submissions:</div>
              <div className="text-ui-dark">{user.number_of_submissions}</div>
            </div>

            <div>
              <div className="text-ui">Latest Activity:</div>
              <div className="text-ui-dark">
                {formatTimestamp(user.latest_submission)}
              </div>
              <div className="text-ui text-xs">
                ({getTimeElapsed(user.latest_submission)})
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default DemoUserCard;
