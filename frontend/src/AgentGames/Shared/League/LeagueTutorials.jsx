import React, { useEffect, useState } from "react";
import LeagueTutorialSelector from "./LeagueTutorialSelector";
import useLeagueAPI from "../hooks/useLeagueAPI";
import { useTerms } from "../terminology";

/**
 * "Tutorials" section for an existing league: shows which tutorials are
 * attached (i.e. visible to the league's teams) and lets admins/institutions
 * change the set. Saving replaces the league's whole attachment list.
 */
function LeagueTutorials({ leagueId, userRole }) {
  const T = useTerms();
  const { getLeagueTutorials, updateLeagueTutorials } = useLeagueAPI(userRole);

  const [selectedIds, setSelectedIds] = useState([]);
  const [savedIds, setSavedIds] = useState([]);
  const [isSaving, setIsSaving] = useState(false);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoadError("");
      const result = await getLeagueTutorials(leagueId);
      if (cancelled) return;
      if (result.success) {
        setSelectedIds(result.tutorialIds);
        setSavedIds(result.tutorialIds);
      } else {
        setLoadError(result.error || `Failed to load ${T.league} ${T.tutorials}`);
      }
    };
    load();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [leagueId]);

  const hasChanges =
    [...selectedIds].sort().join(",") !== [...savedIds].sort().join(",");

  const handleSave = async () => {
    setIsSaving(true);
    const result = await updateLeagueTutorials(leagueId, selectedIds);
    if (result.success) {
      setSavedIds(result.tutorialIds);
      setSelectedIds(result.tutorialIds);
    }
    setIsSaving(false);
  };

  return (
    <div className="mb-6">
      <div className="flex justify-between items-center mb-2">
        <h3 className="text-lg font-medium text-ui-dark">{T.Tutorials}</h3>
        <button
          type="button"
          onClick={handleSave}
          disabled={!hasChanges || isSaving}
          className="px-3 py-1 text-sm bg-primary hover:bg-primary-hover text-white rounded disabled:bg-ui-light disabled:cursor-not-allowed"
        >
          {isSaving ? "Saving..." : `Save ${T.Tutorials}`}
        </button>
      </div>
      <p className="text-sm text-ui mb-2">
        {`${T.Teams} in this ${T.league} only see the ${T.tutorials} selected here.`}
      </p>
      {loadError ? (
        <p className="text-sm text-danger">{loadError}</p>
      ) : (
        <LeagueTutorialSelector
          selectedIds={selectedIds}
          onChange={setSelectedIds}
          disabled={isSaving}
        />
      )}
    </div>
  );
}

export default LeagueTutorials;
