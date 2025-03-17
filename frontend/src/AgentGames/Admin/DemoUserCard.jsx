import React from 'react';
import moment from 'moment-timezone';

const DemoUserCard = ({ user, onDelete }) => {
    // Format timestamp to a readable format
    const formatTimestamp = (timestamp) => {
        return moment(timestamp).format('MMM DD, YYYY HH:mm:ss');
    };

    // Calculate time elapsed since creation (assuming latest_submission is close to creation)
    const getTimeElapsed = (timestamp) => {
        const now = moment();
        const created = moment(timestamp);
        return moment.duration(now.diff(created)).humanize() + ' ago';
    };

    return (
        <div className="bg-ui-lighter rounded-lg overflow-hidden shadow-md border border-ui-light hover:shadow-lg transition-shadow duration-200">
            <div className="bg-league-blue text-white p-4 flex justify-between items-center">
                <div className="font-semibold text-lg truncate">{user.demo_team_name}</div>
                <button
                    onClick={onDelete}
                    className="w-8 h-8 flex items-center justify-center bg-danger hover:bg-danger-hover text-white rounded-full transition-colors"
                    title="Delete demo user"
                >
                    X
                </button>
            </div>

            <div className="p-4 space-y-3">
                <div className="grid grid-cols-2 gap-2">
                    <div className="text-ui text-sm">Team ID:</div>
                    <div className="text-ui-dark font-medium">{user.demo_team_id}</div>

                    <div className="text-ui text-sm">Email:</div>
                    <div className="text-ui-dark font-medium truncate">
                        {user.email || 'Not provided'}
                    </div>

                    <div className="text-ui text-sm">League:</div>
                    <div className="text-ui-dark font-medium">{user.league_name}</div>

                    <div className="text-ui text-sm">Submissions:</div>
                    <div className="text-ui-dark font-medium">{user.number_of_submissions}</div>
                </div>

                <div className="border-t border-ui-light pt-3">
                    <div className="text-ui text-sm">Latest Activity:</div>
                    <div className="text-ui-dark">
                        {formatTimestamp(user.latest_submission)}
                    </div>
                    <div className="text-ui text-xs mt-1">
                        ({getTimeElapsed(user.latest_submission)})
                    </div>
                </div>
            </div>
        </div>
    );
};

export default DemoUserCard;