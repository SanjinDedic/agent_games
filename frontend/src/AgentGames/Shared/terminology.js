import { useSelector } from "react-redux";
import { selectIsClassroom } from "../../slices/settingsSlice";

// One deployment serves one audience, set by SITE_MODE and served over
// GET /config: a classroom (teacher/classroom/student wording) or a competition
// (organizer/league/team wording). Only user-visible copy goes through these
// terms — API paths, JSON keys and Redux identifiers always keep the
// league/team names.
const COMPETITION_TERMS = {
  league: "league", League: "League", leagues: "leagues", Leagues: "Leagues",
  team: "team", Team: "Team", teams: "teams", Teams: "Teams",
};

const CLASSROOM_TERMS = {
  league: "classroom", League: "Classroom", leagues: "classrooms", Leagues: "Classrooms",
  team: "student", Team: "Student", teams: "students", Teams: "Students",
};

const getTerms = (isClassroom) =>
  isClassroom ? CLASSROOM_TERMS : COMPETITION_TERMS;

export function useTerms() {
  return getTerms(useSelector(selectIsClassroom));
}
