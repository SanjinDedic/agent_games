import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import useLeagueAPI from "../Shared/hooks/useLeagueAPI";
import DirectClassicSignup from "./DirectClassicSignup";
import DirectSchoolLeagueSignup from "./DirectSchoolLeagueSignup";

function DirectLeagueSignup() {
  const { leagueToken } = useParams();
  const { getLeagueInfo } = useLeagueAPI();

  const [leagueInfo, setLeagueInfo] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchLeagueInfo = async () => {
      if (!leagueToken) return;

      const result = await getLeagueInfo(leagueToken);
      if (result.success) {
        setLeagueInfo(result.data);
      } else {
        setError("Invalid signup link or league not found");
      }
    };

    fetchLeagueInfo();
  }, [leagueToken, getLeagueInfo]);

  return (
    <div className="min-h-screen pt-16 flex flex-col items-center justify-center bg-ui-lighter">
      <div className="w-full max-w-md px-4">
        <div className="bg-white rounded-lg shadow-lg p-8">
          <h1 className="text-2xl font-bold text-ui-dark mb-4 text-center">
            Team Sign Up
          </h1>

          {leagueInfo ? (
            leagueInfo.school_league ? (
              <DirectSchoolLeagueSignup
                leagueToken={leagueToken}
                leagueInfo={leagueInfo}
              />
            ) : (
              <DirectClassicSignup
                leagueToken={leagueToken}
                leagueInfo={leagueInfo}
              />
            )
          ) : error ? (
            <div className="text-center text-red-600 p-4">
              <p>{error}</p>
              <p className="mt-2">
                <a href="/" className="text-blue-600">
                  Return to home page
                </a>
              </p>
            </div>
          ) : (
            <div className="text-center p-4">
              <p className="text-gray-600">Loading league information...</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default DirectLeagueSignup;
