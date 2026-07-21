"""Classroom-scoped progress queries backing the classroom workspace.

Scoping model: a classroom's students are the teams whose *current* league is
the classroom (Team.league_id). Per-student stats are team-lifetime — the same
semantics as the Team Progress page and the submissions viewer
(get_all_submissions_for_league is lifetime too). SubmissionMetadata.league_id
is nullable, so filtering on it would silently diverge from the Submissions
tab. Exercise attempted/passed counts are restricted to exercises of tutorials
attached to the classroom; last-active is not (any activity is activity).
"""

import logging

from sqlalchemy import case
from sqlmodel import Session, func, select

from backend.database.db_models import (Exercise, ExerciseSubmission,
                                        ExerciseSubmissionMetadata, League,
                                        LeagueTutorial, Submission,
                                        SubmissionMetadata, Team, Tutorial)
from backend.routes.institution.institution_db import InstitutionAccessError, TeamNotFoundError

logger = logging.getLogger(__name__)

# Payload bound for per-team ranking history. Enough for a trend line; the
# full history stays in the DB if a longer view is ever needed.
RANKING_HISTORY_LIMIT = 50


def get_team_by_id(
    session: Session, team_id: int, institution_id: int, is_admin: bool = False
) -> Team:
    """Get a team by ID, ensuring it belongs to the institution (admin bypasses)."""
    team = session.get(Team, team_id)
    if not team:
        raise TeamNotFoundError(f"Team with ID {team_id} not found")
    if not is_admin and team.institution_id != institution_id:
        raise InstitutionAccessError(
            "You don't have permission to access this team"
        )
    return team


def _agent_attempt_stats(session: Session, team_ids: list) -> tuple:
    """Per-team lifetime agent stats: {team_id: (attempts, hints, latest_ts)}
    and {team_id: validated_count}."""
    if not team_ids:
        return {}, {}
    attempt_stats = {
        team_id: (attempts, hints, latest)
        for team_id, attempts, hints, latest in session.exec(
            select(
                SubmissionMetadata.team_id,
                func.count(SubmissionMetadata.id),
                func.sum(
                    case((SubmissionMetadata.hint_included == True, 1), else_=0)  # noqa: E712
                ),
                func.max(SubmissionMetadata.timestamp),
            )
            .where(SubmissionMetadata.team_id.in_(team_ids))
            .group_by(SubmissionMetadata.team_id)
        ).all()
    }
    validated_counts = dict(
        session.exec(
            select(SubmissionMetadata.team_id, func.count(Submission.id))
            .join(Submission, Submission.metadata_id == SubmissionMetadata.id)
            .where(SubmissionMetadata.team_id.in_(team_ids))
            .group_by(SubmissionMetadata.team_id)
        ).all()
    )
    return attempt_stats, validated_counts


def _ranking_histories(session: Session, team_ids: list) -> tuple:
    """One newest-first scan of ranked submissions gives both the capped
    per-team history and the ever-hit-first flag (which must see full
    history, not just the window). Pre-ranking submissions have NULL and are
    skipped. Histories come back oldest -> newest so they read as trends."""
    histories: dict = {}
    achieved_first: set = set()
    if not team_ids:
        return histories, achieved_first
    ranked_rows = session.exec(
        select(
            SubmissionMetadata.team_id, Submission.ranking, Submission.timestamp
        )
        .join(Submission, Submission.metadata_id == SubmissionMetadata.id)
        .where(SubmissionMetadata.team_id.in_(team_ids))
        .where(Submission.ranking.is_not(None))
        .order_by(Submission.timestamp.desc(), Submission.id.desc())
    ).all()
    for team_id, ranking, timestamp in ranked_rows:
        history = histories.setdefault(team_id, [])
        if len(history) < RANKING_HISTORY_LIMIT:
            history.append(
                {"ranking": ranking, "timestamp": timestamp.isoformat()}
            )
        if ranking == 1:
            achieved_first.add(team_id)
    for history in histories.values():
        history.reverse()
    return histories, achieved_first


def _league_exercise_cells(
    session: Session, league_id: int, team_ids: list
) -> tuple:
    """Per (team, exercise) attempt stats restricted to exercises of tutorials
    attached to the league: {(team_id, exercise_id): (attempts, last_ts)} and
    the set of (team_id, exercise_id) pairs with a passed run."""
    if not team_ids:
        return {}, set()
    attempts = {
        (team_id, exercise_id): (count, last_ts)
        for team_id, exercise_id, count, last_ts in session.exec(
            select(
                ExerciseSubmissionMetadata.team_id,
                ExerciseSubmissionMetadata.exercise_id,
                func.count(ExerciseSubmissionMetadata.id),
                func.max(ExerciseSubmissionMetadata.timestamp),
            )
            .join(
                Exercise,
                Exercise.id == ExerciseSubmissionMetadata.exercise_id,
            )
            .join(
                LeagueTutorial,
                LeagueTutorial.tutorial_id == Exercise.tutorial_id,
            )
            .where(LeagueTutorial.league_id == league_id)
            .where(ExerciseSubmissionMetadata.team_id.in_(team_ids))
            .group_by(
                ExerciseSubmissionMetadata.team_id,
                ExerciseSubmissionMetadata.exercise_id,
            )
        ).all()
    }
    passed_pairs = set(
        session.exec(
            select(
                ExerciseSubmissionMetadata.team_id,
                ExerciseSubmissionMetadata.exercise_id,
            )
            .join(
                ExerciseSubmission,
                ExerciseSubmission.metadata_id == ExerciseSubmissionMetadata.id,
            )
            .join(
                Exercise,
                Exercise.id == ExerciseSubmissionMetadata.exercise_id,
            )
            .join(
                LeagueTutorial,
                LeagueTutorial.tutorial_id == Exercise.tutorial_id,
            )
            .where(LeagueTutorial.league_id == league_id)
            .where(ExerciseSubmissionMetadata.team_id.in_(team_ids))
            .where(ExerciseSubmission.passed == True)  # noqa: E712
            .distinct()
        ).all()
    )
    return attempts, passed_pairs


def _latest_exercise_activity(session: Session, team_ids: list) -> dict:
    """{team_id: latest exercise attempt timestamp} across ALL exercises."""
    if not team_ids:
        return {}
    return dict(
        session.exec(
            select(
                ExerciseSubmissionMetadata.team_id,
                func.max(ExerciseSubmissionMetadata.timestamp),
            )
            .where(ExerciseSubmissionMetadata.team_id.in_(team_ids))
            .group_by(ExerciseSubmissionMetadata.team_id)
        ).all()
    )


def _league_tutorials(session: Session, league_id: int) -> list:
    """Tutorials attached to a league, in tutorial-id order."""
    return session.exec(
        select(Tutorial)
        .join(LeagueTutorial, LeagueTutorial.tutorial_id == Tutorial.id)
        .where(LeagueTutorial.league_id == league_id)
        .order_by(Tutorial.id)
    ).all()


def get_classroom_progress(session: Session, league: League) -> dict:
    """Per-student roster stats for one classroom: lifetime agent submission
    stats, ranking trend, and exercise completion against the classroom's
    attached tutorials."""
    teams = session.exec(
        select(Team).where(Team.league_id == league.id).order_by(Team.name)
    ).all()
    team_ids = [team.id for team in teams]

    attempt_stats, validated_counts = _agent_attempt_stats(session, team_ids)
    histories, achieved_first = _ranking_histories(session, team_ids)
    exercise_activity = _latest_exercise_activity(session, team_ids)
    cell_attempts, passed_pairs = _league_exercise_cells(
        session, league.id, team_ids
    )

    exercises_total = session.exec(
        select(func.count(Exercise.id))
        .join(LeagueTutorial, LeagueTutorial.tutorial_id == Exercise.tutorial_id)
        .where(LeagueTutorial.league_id == league.id)
    ).one()

    attempted_by_team: dict = {}
    for team_id, _exercise_id in cell_attempts:
        attempted_by_team[team_id] = attempted_by_team.get(team_id, 0) + 1
    passed_by_team: dict = {}
    for team_id, _exercise_id in passed_pairs:
        passed_by_team[team_id] = passed_by_team.get(team_id, 0) + 1

    team_rows = []
    for team in teams:
        attempts, hints, latest_agent = attempt_stats.get(team.id, (0, 0, None))
        latest_exercise = exercise_activity.get(team.id)
        candidates = [ts for ts in (latest_agent, latest_exercise) if ts]
        last_active = max(candidates) if candidates else None
        team_rows.append(
            {
                "id": team.id,
                "name": team.name,
                "school": team.school_name,
                "total_attempts": attempts,
                "validated_submissions": validated_counts.get(team.id, 0),
                "hints_used": hints,
                "latest_agent_submission": (
                    latest_agent.isoformat() if latest_agent else None
                ),
                "latest_exercise_activity": (
                    latest_exercise.isoformat() if latest_exercise else None
                ),
                "last_active": last_active.isoformat() if last_active else None,
                "ranking_history": histories.get(team.id, []),
                "achieved_first": team.id in achieved_first,
                "exercises_attempted": attempted_by_team.get(team.id, 0),
                "exercises_passed": passed_by_team.get(team.id, 0),
                "exercises_total": exercises_total,
            }
        )

    return {
        "league": {
            "id": league.id,
            "name": league.name,
            "game": league.game,
            "expiry_date": (
                league.expiry_date.isoformat() if league.expiry_date else None
            ),
            "signup_link": league.signup_link,
        },
        "teams": team_rows,
    }


def get_classroom_tutorial_matrix(session: Session, league: League) -> dict:
    """Student x exercise grid per tutorial attached to the classroom.

    Untouched cells are omitted; the client renders absence as untouched.
    """
    teams = session.exec(
        select(Team).where(Team.league_id == league.id).order_by(Team.name)
    ).all()
    team_ids = [team.id for team in teams]
    cell_attempts, passed_pairs = _league_exercise_cells(
        session, league.id, team_ids
    )

    tutorials = []
    for tutorial in _league_tutorials(session, league.id):
        cells = []
        for exercise in tutorial.exercises:
            for team_id in team_ids:
                key = (team_id, exercise.id)
                if key not in cell_attempts:
                    continue
                count, last_ts = cell_attempts[key]
                cells.append(
                    {
                        "team_id": team_id,
                        "exercise_id": exercise.id,
                        "status": (
                            "passed" if key in passed_pairs else "attempted"
                        ),
                        "attempts": count,
                        "last_attempt_at": (
                            last_ts.isoformat() if last_ts else None
                        ),
                    }
                )
        tutorials.append(
            {
                "id": tutorial.id,
                "title": tutorial.title,
                "exercises": [
                    {
                        "id": exercise.id,
                        "title": exercise.title,
                        "order_index": exercise.order_index,
                    }
                    for exercise in tutorial.exercises
                ],
                "cells": cells,
            }
        )

    return {
        "league": {"id": league.id, "name": league.name},
        "teams": [{"id": team.id, "name": team.name} for team in teams],
        "tutorials": tutorials,
    }


def get_student_summary(session: Session, team: Team) -> dict:
    """Drill-down header data for one student: identity, lifetime agent stats
    with ranking trend, and per-exercise tutorial status for the tutorials
    attached to the student's current classroom (untouched exercises
    included, unlike the matrix)."""
    attempt_stats, validated_counts = _agent_attempt_stats(session, [team.id])
    histories, achieved_first = _ranking_histories(session, [team.id])
    attempts, hints, latest_agent = attempt_stats.get(team.id, (0, 0, None))
    latest_exercise = _latest_exercise_activity(session, [team.id]).get(team.id)
    candidates = [ts for ts in (latest_agent, latest_exercise) if ts]
    last_active = max(candidates) if candidates else None

    tutorials = []
    if team.league_id:
        cell_attempts, passed_pairs = _league_exercise_cells(
            session, team.league_id, [team.id]
        )
        for tutorial in _league_tutorials(session, team.league_id):
            exercises = []
            for exercise in tutorial.exercises:
                key = (team.id, exercise.id)
                count, last_ts = cell_attempts.get(key, (0, None))
                if key in passed_pairs:
                    status = "passed"
                elif count:
                    status = "attempted"
                else:
                    status = "untouched"
                exercises.append(
                    {
                        "id": exercise.id,
                        "title": exercise.title,
                        "order_index": exercise.order_index,
                        "status": status,
                        "attempts": count,
                        "last_attempt_at": (
                            last_ts.isoformat() if last_ts else None
                        ),
                    }
                )
            tutorials.append(
                {
                    "id": tutorial.id,
                    "title": tutorial.title,
                    "exercises": exercises,
                }
            )

    return {
        "team": {
            "id": team.id,
            "name": team.name,
            "school": team.school_name,
            "league_id": team.league_id,
            "league_name": team.league.name if team.league else None,
            "created_at": (
                team.created_at.isoformat() if team.created_at else None
            ),
        },
        "agent": {
            "total_attempts": attempts,
            "validated_submissions": validated_counts.get(team.id, 0),
            "hints_used": hints,
            "latest_submission": (
                latest_agent.isoformat() if latest_agent else None
            ),
            "ranking_history": histories.get(team.id, []),
            "achieved_first": team.id in achieved_first,
        },
        "last_active": last_active.isoformat() if last_active else None,
        "tutorials": tutorials,
    }


def get_student_agent_submissions(session: Session, team: Team) -> dict:
    """One student's full validated agent submission history, oldest first
    (matching the submission viewer's prev/next indexing)."""
    rows = session.exec(
        select(Submission, SubmissionMetadata)
        .join(SubmissionMetadata, Submission.metadata_id == SubmissionMetadata.id)
        .where(SubmissionMetadata.team_id == team.id)
        .order_by(Submission.timestamp.asc(), Submission.id.asc())
    ).all()

    return {
        "team": {"id": team.id, "name": team.name},
        "submissions": [
            {
                "id": sub.id,
                "code": sub.code,
                "timestamp": sub.timestamp.isoformat(),
                "duration_ms": meta.duration_ms,
                "ranking": sub.ranking,
                "league_id": meta.league_id,
            }
            for sub, meta in rows
        ],
    }
