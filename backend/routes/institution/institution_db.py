import json
import logging
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Union

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, delete, func, select

from backend.database.db_models import (Institution, League, LeagueType,
                                        LeagueTutorial, SimulationResult,
                                        SimulationResultItem, Team, TeamType,
                                        Tutorial)
from backend.database.submission_helpers import (delete_submissions_for_teams,
                                                 delete_team_children)
from backend.games.game_factory import GameFactory
from backend.routes.institution.institution_models import LeagueSignUp
from backend.schools.config import (GoogleSheetsSchoolsConfig,
                                    StaticSchoolsConfig)
from backend.routes.tutorial.tutorial_db import (set_league_tutorials,
                                                 validate_tutorial_ids)
from backend.schools.providers import (GoogleSheetsSchoolsProvider,
                                       SchoolsProviderError)
from backend.team_capacity import assert_team_capacity
from backend.utils import process_simulation_results
from backend.time_utils import ensure_utc, to_sydney, utc_now

logger = logging.getLogger(__name__)


class LeagueExistsError(Exception):
    """Raised when attempting to create a league that already exists (maps to HTTP 409)."""
    pass


class LeagueNotFoundError(Exception):
    """Raised when a league is not found or is not visible to the caller (maps to HTTP 404)."""
    pass


class ProtectedLeagueError(Exception):
    """Raised when an operation targets a league that may not be modified,
    e.g. deleting the auto-created 'unassigned' league (maps to HTTP 400)."""
    pass


class SimulationResultNotFoundError(Exception):
    """Raised when a referenced simulation result does not exist (maps to HTTP 404)."""
    pass


class TeamError(Exception):
    """Base exception for all team-related errors."""
    pass


class TeamNotFoundError(TeamError):
    """Raised when the target team does not exist (maps to HTTP 404)."""
    pass


class TeamExistsError(TeamError):
    """Raised when a team name collides within the institution (maps to HTTP 409)."""
    pass


class SchoolsConfigError(Exception):
    """Raised when a school league's schools_config is invalid or unreachable (maps to HTTP 400)."""
    pass


def _build_schools_config(
    league_data: LeagueSignUp,
) -> Optional[Union[StaticSchoolsConfig, GoogleSheetsSchoolsConfig]]:
    """Translate the validated LeagueSignUp into a typed schools_config.

    Sheet-backed configs are validated upfront (one fetch) so configuration
    errors surface at create time, not at student-signup time.
    """
    if not league_data.school_league:
        return None
    if league_data.sheet_url:
        try:
            schools = GoogleSheetsSchoolsProvider(league_data.sheet_url).list_schools()
        except SchoolsProviderError as e:
            raise SchoolsConfigError(f"Could not read the Google Sheet: {e}")
        if not schools:
            raise SchoolsConfigError(
                "The Google Sheet returned an empty list. Ensure sharing "
                "is set to 'Anyone with the link - Viewer' and that column "
                "A contains school names below a header row."
            )
        return GoogleSheetsSchoolsConfig(sheet_url=league_data.sheet_url)
    return StaticSchoolsConfig(schools=list(league_data.schools))


def _membership_expiry(session: Session, institution_id: int) -> Optional[datetime]:
    """The institution's subscription end date, or None when it has no
    subscription record. A league may not outlive it."""
    institution = session.get(Institution, institution_id)
    subscription = institution.subscription if institution else None
    if subscription is None or subscription.subscription_expiry is None:
        return None
    return ensure_utc(subscription.subscription_expiry)


def create_league(
    session: Session, league_data: LeagueSignUp, institution_id: int
) -> Dict:
    """Create a new league for an institution"""
    # Check if the institution has a league with this name already
    existing_league = session.exec(
        select(League)
        .where(League.name == league_data.name)
        .where(League.institution_id == institution_id)
    ).first()

    if existing_league:
        raise LeagueExistsError(
            f"League with name '{league_data.name}' already exists for this institution"
        )

    # Validate game name
    GameFactory.get_game_class(league_data.game)

    # Validate tutorial ids up front (404) so nothing is created on failure.
    validate_tutorial_ids(session, league_data.tutorial_ids)

    schools_config_model = _build_schools_config(league_data)
    schools_config = (
        schools_config_model.model_dump() if schools_config_model else None
    )

    # Generate unique signup token
    signup_token = secrets.token_urlsafe(16)

    # A new league runs until the institution's membership ends; without a
    # subscription record on file it falls back to a 24 hour trial window.
    membership_expiry = _membership_expiry(session, institution_id)
    default_expiry = membership_expiry or (utc_now() + timedelta(hours=24))

    # Create the league
    league = League(
        name=league_data.name,
        created_date=utc_now(),
        expiry_date=default_expiry,
        game=league_data.game,
        institution_id=institution_id,
        league_type=LeagueType.INSTITUTION,
        signup_link=signup_token,
        school_league=league_data.school_league,
        schools_config=schools_config,
    )

    session.add(league)
    session.flush()
    # Attach the selected tutorials in the same transaction: an unknown
    # tutorial id raises (404) and rolls the league creation back with it.
    set_league_tutorials(
        session, league.id, league_data.tutorial_ids, commit=False
    )
    session.commit()
    return {
        "league_id": league.id,
        "name": league.name,
        "signup_token": signup_token,
        "school_league": league_data.school_league,
        "tutorial_ids": league_data.tutorial_ids,
    }


def create_team(session: Session, team_data, institution_id: int) -> Dict:
    """Create a new team for an institution"""
    assert_team_capacity(session, institution_id)
    try:
        # Check for existing team within this institution
        existing_team = session.exec(
            select(Team)
            .where(Team.name == team_data.name)
            .where(Team.institution_id == institution_id)
        ).first()

        if existing_team:
            raise TeamExistsError(f"Team with name '{team_data.name}' already exists in this institution")

        unassigned_league = get_unassigned_league(session, institution_id)

        team = Team(
            name=team_data.name,
            school_name=team_data.school_name,
            score=team_data.score,
            color=team_data.color,
            league_id=unassigned_league.id,
            institution_id=institution_id,
            team_type=TeamType.STUDENT,
        )
        team.set_password(team_data.password)

        session.add(team)
        session.commit()

        return {"team_id": team.id, "name": team.name, "school": team.school_name}

    except TeamError:
        session.rollback()
        raise
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Database integrity error creating team: {e}")
        raise TeamExistsError("Unable to create team due to data constraints")


def delete_team(session: Session, team_id: int, institution_id: int) -> str:
    """Delete a team and its associated data"""
    team = get_team_by_id(session, team_id, institution_id)

    # Clear everything that references the team first
    delete_team_children(session, [team.id])

    session.delete(team)
    session.commit()

    return f"Team {team.name} deleted successfully"


def get_all_teams(session: Session, institution_id: int) -> Dict:
    """Get all teams for an institution"""
    teams = session.exec(
        select(Team).where(Team.institution_id == institution_id)
    ).all()
    return {
        "teams": [
            {
                "id": team.id,
                "name": team.name,
                "school": team.school_name,
                "league": team.league.name if team.league else None,
            }
            for team in teams
        ]
    }


def get_classroom_summaries(session: Session, institution_id: int) -> list:
    """League/classroom cards for the institution home page: every non-deleted
    league except the 'unassigned' holding pen, with its team count, attached
    tutorial titles, and shareable signup link."""
    leagues = session.exec(
        select(League)
        .where(
            League.institution_id == institution_id,
            League.deleted_date == None,  # noqa: E711
            League.name != "unassigned",
        )
        .order_by(League.created_date.desc())
    ).all()
    league_ids = [league.id for league in leagues]

    team_counts: dict = {}
    tutorial_titles: dict = {}
    if league_ids:
        team_counts = dict(
            session.exec(
                select(Team.league_id, func.count(Team.id))
                .where(Team.league_id.in_(league_ids))
                .group_by(Team.league_id)
            ).all()
        )
        for league_id, tutorial_id, title in session.exec(
            select(LeagueTutorial.league_id, Tutorial.id, Tutorial.title)
            .join(Tutorial, Tutorial.id == LeagueTutorial.tutorial_id)
            .where(LeagueTutorial.league_id.in_(league_ids))
            .order_by(LeagueTutorial.tutorial_id)
        ).all():
            tutorial_titles.setdefault(league_id, []).append(
                {"id": tutorial_id, "title": title}
            )

    now = utc_now()
    return [
        {
            "id": league.id,
            "name": league.name,
            "game": league.game,
            "team_count": team_counts.get(league.id, 0),
            "tutorials": tutorial_titles.get(league.id, []),
            "signup_link": league.signup_link,
            "created_date": league.created_date,
            "expiry_date": league.expiry_date,
            "is_active": ensure_utc(league.expiry_date) >= now,
        }
        for league in leagues
    ]


def get_league_by_id(session: Session, league_id: int, institution_id: int, is_admin: bool = False) -> League:
    """Get a league by ID, ensuring it belongs to the institution (admin bypasses ownership check).

    A foreign league raises the same 404 as a missing one, so a response never
    confirms that another institution's league id exists."""
    league = session.get(League, league_id)
    if not league or (not is_admin and league.institution_id != institution_id):
        raise LeagueNotFoundError(f"League with ID {league_id} not found")
    return league


def get_team_by_id(
    session: Session, team_id: int, institution_id: int, is_admin: bool = False
) -> Team:
    """Get a team by ID, ensuring it belongs to the institution (admin bypasses ownership check).

    A foreign team raises the same 404 as a missing one, so a response never
    confirms that another institution's team id exists."""
    team = session.get(Team, team_id)
    if not team or (not is_admin and team.institution_id != institution_id):
        raise TeamNotFoundError(f"Team with ID {team_id} not found")
    return team


def save_simulation_results(
    session: Session,
    league_id: int,
    institution_id: int,
    results: Dict,
    rewards=None,
    feedback_str=None,
    feedback_json=None,
    is_admin: bool = False,
) -> SimulationResult:
    """Save simulation results for a league"""
    # Verify the league belongs to this institution
    league = get_league_by_id(session, league_id, institution_id, is_admin=is_admin)
    
    timestamp = utc_now()
    rewards_str = rewards if rewards is not None else "[10, 0, 0, 0, 0, 0, 0]"
    if isinstance(rewards_str, list):
        rewards_str = json.dumps(rewards_str)

    simulation_result = SimulationResult(
        league_id=league_id,
        timestamp=timestamp,
        num_simulations=results["num_simulations"],
        custom_rewards=rewards_str,
        feedback_str=feedback_str,
        feedback_json=feedback_json,
    )
    session.add(simulation_result)
    session.flush()

    custom_value_names = list(results.get("table", {}).keys())[:3]

    for team_name, score in results["total_points"].items():
        # Scope by league_id: names are only unique per-league, and a simulation's
        # results belong to this one league. A bare name lookup could match a
        # same-named team in another league (or raise on duplicates).
        team = session.exec(
            select(Team)
            .where(Team.name == team_name)
            .where(Team.league_id == league_id)
        ).one_or_none()
        if team and (is_admin or team.institution_id == institution_id):  # Only include teams from this institution
            result_item = SimulationResultItem(
                simulation_result_id=simulation_result.id, team_id=team.id, score=score
            )

            for i, name in enumerate(custom_value_names, start=1):
                value = results["table"][name]
                if isinstance(value, dict):
                    setattr(result_item, f"custom_value{i}", value.get(team_name))
                else:
                    setattr(result_item, f"custom_value{i}", value)
                setattr(result_item, f"custom_value{i}_name", name)

            session.add(result_item)

    session.commit()
    return simulation_result


def get_all_league_results(session: Session, league_id: int, institution_id: int, is_admin: bool = False) -> Dict:
    """Get all simulation results for a league"""
    league = get_league_by_id(session, league_id, institution_id, is_admin=is_admin)

    results = []
    for sim in league.simulation_results:
        result = process_simulation_results(sim, league.name)
        results.append(result)

    return {"results": sorted(results, key=lambda x: x["id"], reverse=True)}


def publish_sim_results(
    session: Session,
    league_id: int,
    sim_id: int,
    institution_id: int,
    feedback: Union[str, Dict, None] = None,
    is_admin: bool = False,
) -> Tuple[str, Dict]:
    """Publish simulation results"""
    league = get_league_by_id(session, league_id, institution_id, is_admin=is_admin)

    # A sim belonging to a different league 404s like a missing one, so the
    # response never confirms a foreign simulation id exists.
    simulation = session.get(SimulationResult, sim_id)
    if not simulation or simulation.league_id != league.id:
        raise SimulationResultNotFoundError(f"Simulation result with ID {sim_id} not found")

    if not simulation.publish_link:
        simulation.publish_link = secrets.token_urlsafe(16)

    simulation.published = True

    if feedback is not None:
        if isinstance(feedback, str):
            simulation.feedback_str = feedback
            simulation.feedback_json = None
        else:
            simulation.feedback_str = None
            simulation.feedback_json = json.dumps(feedback)

    session.add(simulation)
    session.commit()

    return (
        f"Results published successfully for league '{league.name}'",
        {
            "sim_id": simulation.id,
            "league_name": league.name,
            "published": True,
            "publish_link": simulation.publish_link,
        },
    )


def update_expiry_date(
    session: Session, league_id: int, expiry_date: datetime, institution_id: int, is_admin: bool = False
) -> str:
    """Update league expiry date.

    A league may not outlive the owning institution's membership: a later date
    is capped at the subscription expiry and the message says so. Admins set
    dates freely.
    """
    league = get_league_by_id(session, league_id, institution_id, is_admin=is_admin)

    capped_at = None
    if not is_admin and league.institution_id is not None:
        membership_expiry = _membership_expiry(session, league.institution_id)
        if membership_expiry and ensure_utc(expiry_date) > membership_expiry:
            expiry_date = membership_expiry
            capped_at = membership_expiry

    league.expiry_date = expiry_date
    session.add(league)
    session.commit()

    if capped_at:
        return (
            f"Expiry capped at your membership end date "
            f"({to_sydney(capped_at).strftime('%d %B %Y')}) for league '{league.name}'"
        )
    return f"Expiry date updated successfully for league '{league.name}'"


def update_league_info(
    session: Session,
    league_id: int,
    info_markdown: str,
    institution_id: int,
    is_admin: bool = False,
) -> str:
    """Update the per-league markdown info block."""
    league = get_league_by_id(session, league_id, institution_id, is_admin=is_admin)

    league.info_markdown = info_markdown or ""
    session.add(league)
    session.commit()
    return f"League info updated successfully for league '{league.name}'"


def assign_team_to_league(session: Session, team_id: int, league_id: int, institution_id: int, is_admin: bool = False) -> str:
    """Assign a team to a league within the same institution"""
    team = get_team_by_id(session, team_id, institution_id, is_admin=is_admin)
    league = get_league_by_id(session, league_id, institution_id, is_admin=is_admin)

    team.league_id = league.id
    session.add(team)
    session.commit()
    return f"Team '{team.name}' assigned to league '{league.name}'"


def get_unassigned_league(session: Session, institution_id: int) -> League:
    """Fetch the 'unassigned' holding-pen league for an institution, creating
    it if absent.

    Creation must be lazy: students who join via a signup link go straight
    into their classroom, so an institution can reach unassign/delete-league
    without the holding pen ever having been created.
    """
    unassigned_league = session.exec(
        select(League)
        .where(League.name == "unassigned")
        .where(League.institution_id == institution_id)
    ).first()

    if not unassigned_league:
        unassigned_league = League(
            name="unassigned",
            created_date=utc_now(),
            expiry_date=utc_now() + timedelta(days=365),
            game="greedy_pig",  # Default game
            institution_id=institution_id,
            league_type=LeagueType.INSTITUTION,
        )
        session.add(unassigned_league)
        session.flush()  # callers need the ID before commit

    return unassigned_league


def unassign_team(session: Session, team_id: int, institution_id: int) -> str:
    """Move a team to the current institution's 'unassigned' league."""
    team = get_team_by_id(session, team_id, institution_id)

    unassigned_league = get_unassigned_league(session, institution_id)
    team.league_id = unassigned_league.id
    session.add(team)
    session.commit()
    return f"Team '{team.name}' moved to 'unassigned'"


def generate_signup_link(session: Session, league_id: int, institution_id: int, is_admin: bool = False) -> Dict:
    """Generate a new signup link for a league"""
    league = get_league_by_id(session, league_id, institution_id, is_admin=is_admin)

    # Generate a new signup token
    signup_token = secrets.token_urlsafe(16)
    league.signup_link = signup_token
    session.add(league)
    session.commit()

    return {"signup_token": signup_token, "league_name": league.name}


# How long a password-reset link stays usable. Generous on purpose: a teacher
# may generate links in the evening for a class that runs the next day.
PASSWORD_RESET_LINK_HOURS = 48


def generate_team_password_reset(
    session: Session, team_id: int, institution_id: int
) -> Dict:
    """Create a one-time password-reset token for a team the institution owns.

    Regenerating replaces any previous token, so a mis-shared link can be
    invalidated by generating a fresh one.
    """
    team = get_team_by_id(session, team_id, institution_id)

    reset_token = secrets.token_urlsafe(16)
    team.password_reset_token = reset_token
    team.password_reset_expiry = utc_now() + timedelta(
        hours=PASSWORD_RESET_LINK_HOURS
    )
    session.add(team)
    session.commit()

    return {"reset_token": reset_token, "team_name": team.name}


def delete_league(session: Session, league_id: int, institution_id: int, is_admin: bool = False) -> str:
    """Delete a league and move its teams to the unassigned league"""
    league = get_league_by_id(session, league_id, institution_id, is_admin=is_admin)

    league_name = league.name
    if league_name.lower() == "unassigned":
        raise ProtectedLeagueError("Cannot delete the 'unassigned' league")

    unassigned_league = get_unassigned_league(session, institution_id)

    # Get all teams in the league
    teams = session.exec(select(Team).where(Team.league_id == league.id)).all()
    team_count = len(teams)

    # Get simulation results for this league
    sim_results = session.exec(
        select(SimulationResult).where(SimulationResult.league_id == league.id)
    ).all()
    # Delete all simulation result items for simulation results in this league
    for sim_result in sim_results:
        session.exec(
            delete(SimulationResultItem).where(
                SimulationResultItem.simulation_result_id == sim_result.id
            )
        )

    session.exec(
        delete(SimulationResult).where(SimulationResult.league_id == league.id)
    )
    # Delete all submissions from teams in this league and move teams to unassigned league
    delete_submissions_for_teams(session, [team.id for team in teams])
    for team in teams:
        # Move team to unassigned league
        team.league_id = unassigned_league.id
        session.add(team)

    session.commit()
    # Delete the league (tutorial attachments first — they FK the league)
    session.exec(
        delete(LeagueTutorial).where(LeagueTutorial.league_id == league.id)
    )
    session.delete(league)
    session.commit()

    return f"League '{league_name}' deleted and {team_count} teams moved to the unassigned league"
