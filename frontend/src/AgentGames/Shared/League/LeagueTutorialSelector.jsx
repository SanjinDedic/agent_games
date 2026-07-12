import React, { useEffect, useState } from "react";
import useTutorialAPI from "../hooks/useTutorialAPI";

/**
 * Checkbox list of every tutorial in the library, for attaching tutorials to
 * a league. Controlled: the parent owns `selectedIds` and receives the full
 * updated array via `onChange`. Admin/institution tokens see the whole
 * library from /tutorial/tutorials.
 */
function LeagueTutorialSelector({ selectedIds, onChange, disabled = false }) {
  const { getTutorials } = useTutorialAPI();
  const [tutorials, setTutorials] = useState(null); // null = still loading
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      const result = await getTutorials();
      if (cancelled) return;
      if (result.success) {
        setTutorials(result.tutorials);
      } else {
        setLoadError(result.error || "Failed to load tutorials");
        setTutorials([]);
      }
    };
    load();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const toggle = (tutorialId) => {
    if (selectedIds.includes(tutorialId)) {
      onChange(selectedIds.filter((id) => id !== tutorialId));
    } else {
      onChange([...selectedIds, tutorialId]);
    }
  };

  if (tutorials === null) {
    return <p className="text-sm text-ui">Loading tutorials...</p>;
  }
  if (loadError) {
    return <p className="text-sm text-danger">{loadError}</p>;
  }
  if (tutorials.length === 0) {
    return (
      <p className="text-sm text-ui">
        No tutorials exist yet. Admins can create them under Tutorials.
      </p>
    );
  }

  return (
    <div className="space-y-2 max-h-48 overflow-y-auto border border-ui-light rounded p-3">
      {tutorials.map((tutorial) => (
        <label
          key={tutorial.id}
          className="flex items-start gap-2 cursor-pointer"
        >
          <input
            type="checkbox"
            checked={selectedIds.includes(tutorial.id)}
            onChange={() => toggle(tutorial.id)}
            disabled={disabled}
            className="mt-1"
          />
          <span className="min-w-0">
            <span className="block text-ui-dark font-medium">
              {tutorial.title}
            </span>
            <span className="block text-sm text-ui">
              {tutorial.exercise_count}{" "}
              {tutorial.exercise_count === 1 ? "exercise" : "exercises"}
            </span>
          </span>
        </label>
      ))}
    </div>
  );
}

export default LeagueTutorialSelector;
