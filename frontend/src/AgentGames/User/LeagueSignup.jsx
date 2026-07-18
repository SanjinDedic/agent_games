import React, { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import moment from "moment-timezone";
import { setCurrentLeague } from "../../slices/leaguesSlice";
import {
  selectCurrentUser,
  selectInstitutionName,
  selectIsDemo,
  selectLeagueId,
} from "../../slices/authSlice";
import useLeagueAPI from "../Shared/hooks/useLeagueAPI";
import { useTerms } from "../Shared/terminology";

function AgentLeagueSignUp() {
  const T = useTerms();
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const currentUser = useSelector(selectCurrentUser);
  const currentLeague = useSelector((state) => state.leagues.currentLeague);
  const allLeagues = useSelector((state) => state.leagues.list);
  const isDemo = useSelector(selectIsDemo);
  const assignedLeagueId = useSelector(selectLeagueId);
  const institutionName = useSelector(selectInstitutionName);

  const { fetchUserLeagues, assignToLeague, isLoading } = useLeagueAPI();

  const [pendingLeague, setPendingLeague] = useState(null);
  const preselectedRef = useRef(false);

  moment.tz.setDefault("Australia/Sydney");

  useEffect(() => {
    fetchUserLeagues();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Resolve the assigned-league record from JWT league_id + loaded leagues.
  const assignedLeague = useMemo(
    () => (assignedLeagueId ? allLeagues?.find((l) => l.id === assignedLeagueId) : null),
    [assignedLeagueId, allLeagues],
  );
  const assignedLeagueName = assignedLeague?.name ?? null;

  // Pre-select team's currently assigned league once leagues are loaded (one-shot)
  useEffect(() => {
    if (preselectedRef.current) return;
    if (!assignedLeague) return;
    if (assignedLeague.name.toLowerCase() !== "unassigned") {
      dispatch(setCurrentLeague(assignedLeague.name));
    }
    preselectedRef.current = true;
  }, [assignedLeague, dispatch]);

  const isAssignedToReal =
    assignedLeagueName && assignedLeagueName.toLowerCase() !== "unassigned";

  const handleLeagueClick = (league) => {
    if (
      isAssignedToReal &&
      league.id !== assignedLeagueId &&
      currentLeague?.id !== league.id
    ) {
      setPendingLeague(league);
      return;
    }
    dispatch(setCurrentLeague(league.name));
  };

  const confirmLeagueChange = () => {
    if (pendingLeague) {
      dispatch(setCurrentLeague(pendingLeague.name));
      setPendingLeague(null);
    }
  };

  const cancelLeagueChange = () => setPendingLeague(null);

  const handleSignUp = async () => {
    if (!currentLeague) return;
    const result = await assignToLeague(currentLeague.id);
    if (result.success) {
      navigate("/AgentSubmission");
    }
  };

  const displayLeagues = allLeagues
    .filter((league) => league.name.toLowerCase() !== "unassigned")
    .filter((league) =>
      isDemo
        ? league.name.toLowerCase().includes("_demo")
        : !league.name.toLowerCase().includes("_demo")
    );

  return (
    <div className="min-h-screen pt-16 flex items-center justify-center bg-ui-lighter">
      <div className="w-full max-w-4xl mx-4">
        <div className="bg-white rounded-lg shadow-lg p-8">
          <h1 className="text-2xl font-bold text-ui-dark mb-2 text-center">
            {`PICK A ${T.League.toUpperCase()} TO JOIN`}
          </h1>

          {isAssignedToReal && (
            <p className="text-sm text-ui-dark/70 mb-6 text-center">
              {`Your ${T.team} `}
              <span className="font-semibold">{currentUser?.name}</span> is
              already assigned to{" "}
              <span className="font-semibold">{assignedLeagueName}</span>.
            </p>
          )}

          {isDemo && (
            <div className="mb-6 bg-notice-yellowBg border border-notice-yellow rounded-lg p-4">
              <div className="flex items-center space-x-2">
                <p className="text-ui-dark font-medium">
                  DEMO MODE - You are using the demo version of Agent Games
                </p>
              </div>
              <p className="text-ui-dark mt-2">
                {`Only demo ${T.leagues} are displayed. Your progress will be available for the duration of your demo session.`}
              </p>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-ui-lighter p-6 rounded-lg max-h-[304px] overflow-y-auto">
            {displayLeagues.length > 0 ? (
              displayLeagues.map((league) => (
                <label
                  key={league.id}
                  className={`
                    flex items-center p-4 rounded-lg cursor-pointer
                    ${isDemo ? "bg-notice-orange hover:bg-notice-orange/90" : "bg-league-blue hover:bg-league-hover"}
                    transform transition-all duration-200 hover:scale-105
                    shadow-md
                  `}
                >
                  <input
                    type="checkbox"
                    name={league.name}
                    checked={currentLeague?.name === league.name}
                    onChange={() => handleLeagueClick(league)}
                    className="w-5 h-5 mr-4 rounded border-league-text"
                  />
                  <div className="text-white">
                    <span className="block font-bold text-lg">
                      {league.name}
                    </span>
                    <span className="block text-league-text text-sm italic">
                      {league.game}
                    </span>
                  </div>
                </label>
              ))
            ) : (
              <div className="col-span-3 text-center p-4">
                <p className="text-ui-dark">
                  {`No ${T.leagues} available at this time.`}
                </p>
              </div>
            )}
          </div>

          <div className="mt-8">
            <button
              onClick={handleSignUp}
              disabled={isLoading || !currentLeague}
              className={`w-full py-3 px-4 text-lg font-medium text-white bg-primary hover:bg-primary-hover
                       rounded-lg transition-colors duration-200
                       shadow-md hover:shadow-lg
                       disabled:bg-ui-light disabled:cursor-not-allowed`}
            >
              {isLoading ? "Joining..." : `Join ${T.League}`}
            </button>
          </div>
        </div>
      </div>

      {pendingLeague && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
            <h2 className="text-xl font-bold text-ui-dark mb-4">
              {`Change ${T.league}?`}
            </h2>
            <p className="text-ui-dark mb-3">
              <span className="font-semibold">
                {institutionName || (currentUser?.is_teacher ? "Your teacher" : "Your institution")}
              </span>{" "}
              assigned you to{" "}
              <span className="font-semibold">{assignedLeagueName}</span>.{" "}
              {`Are you sure you want to change ${T.leagues}?`}
            </p>
            <p className="text-ui-dark mb-6">
              {`You may not be matched against the ${T.teams} you are intended to play against.`}
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={cancelLeagueChange}
                className="px-4 py-2 rounded-md bg-ui-light hover:bg-ui-light/80 text-ui-dark"
              >
                Cancel
              </button>
              <button
                onClick={confirmLeagueChange}
                className="px-4 py-2 rounded-md bg-primary hover:bg-primary-hover text-white"
              >
                {`Yes, change ${T.league}`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default AgentLeagueSignUp;
