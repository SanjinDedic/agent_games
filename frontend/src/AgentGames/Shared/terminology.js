import { useSelector } from "react-redux";
import { selectIsTeacher } from "../../slices/authSlice";

// Teacher accounts (institution JWTs with is_teacher, and their students'
// tokens) see classroom/student wording; everyone else — normal institutions,
// admins, logged-out visitors — sees the default league/team wording. Only
// user-visible copy goes through these terms: API paths, JSON keys, and Redux
// identifiers always keep the league/team names.
const DEFAULT_TERMS = {
  league: "league", League: "League", leagues: "leagues", Leagues: "Leagues",
  team: "team", Team: "Team", teams: "teams", Teams: "Teams",
};

const TEACHER_TERMS = {
  league: "classroom", League: "Classroom", leagues: "classrooms", Leagues: "Classrooms",
  team: "student", Team: "Student", teams: "students", Teams: "Students",
};

export const getTerms = (isTeacher) => (isTeacher ? TEACHER_TERMS : DEFAULT_TERMS);

export function useTerms() {
  return getTerms(useSelector(selectIsTeacher));
}
