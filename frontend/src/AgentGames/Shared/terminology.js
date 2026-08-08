import { useSelector } from "react-redux";
import { selectIsTeacher } from "../../slices/authSlice";
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
  const isClassroom = useSelector(selectIsClassroom);
  // Transitional: institution and student JWTs still carry an is_teacher claim,
  // and a session that logged in before this deploy is still holding one. Honour
  // it so nobody's wording flips mid-session. Drops out when the claim does.
  const isTeacher = useSelector(selectIsTeacher);
  return getTerms(isClassroom || isTeacher);
}
