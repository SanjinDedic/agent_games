// src/AgentGames/Shared/League/LeaguePublish.jsx
import React, { useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import { toast } from "react-toastify";
import { setPublishLink } from "../../../slices/leaguesSlice";
import useLeagueAPI from "../hooks/useLeagueAPI";

/**
 * Shared component for publishing league results
 *
 * @param {Object} props - Component props
 * @param {string} props.simulation_id - ID of the simulation to publish
 * @param {string} props.selected_league_name - Name of the selected league
 * @param {string} props.userRole - User role ('admin' or 'institution')
 */
const LeaguePublish = ({ simulation_id, selected_league_name, userRole }) => {
  const dispatch = useDispatch();
  const currentSimulation = useSelector(
    (state) => state.leagues.currentLeagueResultSelected
  );
  const [publishSuccess, setPublishSuccess] = useState(false);
  const [publishLink, setPublishLink] = useState("");
  const [copied, setCopied] = useState(false);

  // Use the shared API hook
  const { publishResults, isLoading } = useLeagueAPI(userRole);

  const handlePublish = async () => {
    if (!simulation_id || !selected_league_name) {
      return;
    }

    const publishData = {
      league_name: selected_league_name,
      id: simulation_id,
      feedback: currentSimulation?.feedback || null,
    };

    try {
      const result = await publishResults(publishData);
      console.log("Publish result:", result); // Debug log

      if (result.success && result.data) {
        console.log("Publish data:", result.data); // Debug log
        const link = result.data.publish_link;

        if (link) {
          // First update local state
          setPublishLink(link);
          setPublishSuccess(true);

          // Then safely dispatch Redux action
          try {
            const action = setPublishLink(link);
            console.log("Dispatching action:", action); // Debug action
            if (action) {
              dispatch(action);
            } else {
              console.error("Generated action is undefined");
              toast.warning("Success, but state update failed");
            }
          } catch (err) {
            console.error("Error dispatching action:", err);
          }
        } else {
          console.error("No publish_link in response data");
          toast.warning("Published successfully, but no link was returned");
          setPublishSuccess(true);
        }
      } else {
        toast.error(result.error || "Failed to publish results");
      }
    } catch (error) {
      console.error("Error in handlePublish:", error);
      toast.error("An error occurred while publishing");
    }
  };

  // Copy function for the results link
  const copyLinkToClipboard = () => {
    const baseUrl = `${window.location.protocol}//${window.location.host}`;
    const resultsUrl = `/results/${publishLink}`;
    const fullUrl = `${baseUrl}${resultsUrl}`;

    navigator.clipboard.writeText(fullUrl);
    setCopied(true);
    toast.success("Link copied to clipboard!");
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div>
      {!publishSuccess ? (
        <button
          onClick={handlePublish}
          disabled={isLoading || !simulation_id || !selected_league_name}
          className="w-full bg-success hover:bg-success-hover text-white py-3 px-4 rounded-lg text-lg font-medium transition-colors shadow-sm focus:ring-2 focus:ring-success focus:ring-offset-2 outline-none disabled:bg-ui-light disabled:cursor-not-allowed"
        >
          {isLoading ? "PUBLISHING..." : "PUBLISH RESULT"}
        </button>
      ) : (
        <div className="space-y-3">
          <div className="p-3 bg-success-light rounded-lg text-sm">
            <p className="font-medium text-success mb-2">
              Results published successfully!
            </p>
            <div className="flex items-center">
              <input
                type="text"
                readOnly
                value={`${window.location.protocol}//${window.location.host}/results/${publishLink}`}
                className="flex-1 p-2 border border-ui-light rounded-lg text-xs bg-white overflow-hidden"
              />
              <button
                onClick={copyLinkToClipboard}
                className="ml-2 p-2 bg-primary hover:bg-primary-hover text-white rounded"
                title="Copy to clipboard"
              >
                {copied ? "✓" : "Copy"}
              </button>
            </div>
          </div>
          <button
            onClick={() => setPublishSuccess(false)}
            className="w-full bg-ui hover:bg-ui-dark text-white py-2 px-4 rounded-lg text-sm transition-colors"
          >
            Publish Another Result
          </button>
        </div>
      )}
    </div>
  );
};

export default LeaguePublish;