import json
import logging
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Union

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, func, select

from backend.database.db_models import (
    UNASSIGNED_LEAGUE_NAME,
    AgentAPIKey,
    League,
    LeagueType,
    SimulationResult,
    SimulationResultItem,
    Team,
    TeamType,
)
from backend.database.submission_helpers import delete_submissions_for_teams
from backend.errors import (
    AgentTeamError,
    LeagueExistsError,
    LeagueNotFoundError,
    ProtectedLeagueError,
    SchoolsConfigError,
    SimulationResultNotFoundError,
    TeamError,
    TeamExistsError,
    TeamNotFoundError,
)
from backend.games.game_factory import GameFactory
from backend.routes.admin.admin_models import LeagueSignUp
from backend.schools.config import GoogleSheetsSchoolsConfig, StaticSchoolsConfig
from backend.schools.providers import (
    GoogleSheetsSchoolsProvider,
    SchoolsProviderError,
)
from backend.time_utils import ensure_utc, utc_now
from backend.utils import process_simulation_results

logger = logging.getLogger(__name__)


def get_unassigned_league(session: Session) -> League:
    """The single 'unassigned' holding pen, seeded by init_db.

    Raises rather than creating one on demand: League.name is unique, so a
    missing row means the database was never initialized, and silently creating a
    second definition of a load-bearing singleton would hide that.
    """
    league = session.exec(
        select(League).where(League.name == UNASSIGNED_LEAGUE_NAME)
    ).one_or_none()
    if not league:
        raise LeagueNotFoundError(
            f"The '{UNASSIGNED_LEAGUE_NAME}' league is missing — "
            "run python -m backend.database.init_db"
        )
    return league


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


def create_league(session: Session, league_data: LeagueSignUp) -> Dict:
    """Create a new league."""
    existing_league = session.exec(
        select(League).where(League.name == league_data.name)
    ).first()

    if existing_league:
        raise LeagueExistsError(
            f"League with name '{league_data.name}' already exists"
        )

    # Validate game name
    GameFactory.get_game_class(league_data.game)

    schools_config_model = _build_schools_config(league_data)
    schools_config = (
        schools_config_model.model_dump() if schools_config_model else None
    )

    signup_token = secrets.token_urlsafe(16)

    # A new league runs for 24 hours unless its expiry is extended later.
    default_expiry = utc_now() + timedelta(hours=24)

    league = League(
        name=league_data.name,
        created_date=utc_now(),
        expiry_date=default_expiry,
        game=league_data.game,
        league_type=LeagueType.STUDENT,
        signup_link=signup_token,
        school_league=league_data.school_league,
        schools_config=schools_config,
    )

    session.add(league)
    session.commit()
    return {
        "league_id": league.id,
        "name": league.name,
        "signup_token": signup_token,
        "school_league": league_data.school_league,
    }


def create_team(session: Session, team_data) -> Dict:
    """Create a new team, parked in the 'unassigned' league."""
    try:
        existing_team = session.exec(
            select(Team).where(Team.name == team_data.name)
        ).first()

        if existing_team:
            raise TeamExistsError(
                f"Team with name '{team_data.name}' already exists"
            )

        team = Team(
            name=team_data.name,
            school_name=team_data.school_name,
            score=team_data.score,
            color=team_data.color,
            league_id=get_unassigned_league(session).id,
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


def delete_team(session: Session, team_id: int) -> str:
    """Delete a team. Its submissions, API key and result rows go with it via
    ON DELETE CASCADE."""
    team = session.get(Team, team_id)

    if not team:
        raise TeamNotFoundError(f"Team with ID {team_id} not found")

    name = team.name
    session.delete(team)
    session.commit()

    return f"Team {name} deleted successfully"


def get_all_teams(session: Session) -> Dict:
    """Every team in this deployment."""
    teams = session.exec(select(Team)).all()
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


def get_classroom_summaries(session: Session) -> list:
    """League/classroom cards for the admin home page: every non-deleted league
    except the 'unassigned' holding pen, with its team count and shareable
    signup link."""
    leagues = session.exec(
        select(League)
        .where(
            League.deleted_date == None,  # noqa: E711
            League.name != UNASSIGNED_LEAGUE_NAME,
        )
        .order_by(League.created_date.desc())
    ).all()
    league_ids = [league.id for league in leagues]

    team_counts: dict = {}
    if league_ids:
        team_counts = dict(
            session.exec(
                select(Team.league_id, func.count(Team.id))
                .where(Team.league_id.in_(league_ids))
                .group_by(Team.league_id)
            ).all()
        )

    now = utc_now()
    return [
        {
            "id": league.id,
            "name": league.name,
            "game": league.game,
            "team_count": team_counts.get(league.id, 0),
            "signup_link": league.signup_link,
            "created_date": league.created_date,
            "expiry_date": league.expiry_date,
            "is_active": ensure_utc(league.expiry_date) >= now,
        }
        for league in leagues
    ]


def get_league_by_id(session: Session, league_id: int) -> League:
    """Get a league by ID."""
    league = session.get(League, league_id)

    if not league:
        raise LeagueNotFoundError(f"League with ID {league_id} not found")

    return league


def save_simulation_results(
    session: Session,
    league_id: int,
    results: Dict,
    rewards=None,
    feedback_str=None,
    feedback_json=None,
) -> SimulationResult:
    """Save simulation results for a league"""
    get_league_by_id(session, league_id)

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
        # Scoped by league_id as well as name: a simulation's results belong to
        # this one league, so a team that has since moved elsewhere must not pick
        # up a row here.
        team = session.exec(
            select(Team)
            .where(Team.name == team_name)
            .where(Team.league_id == league_id)
        ).one_or_none()
        if team:
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


def get_all_league_results(session: Session, league_id: int) -> Dict:
    """Get all simulation results for a league"""
    league = get_league_by_id(session, league_id)

    results = [
        process_simulation_results(sim, league.name)
        for sim in league.simulation_results
    ]

    return {"results": sorted(results, key=lambda x: x["id"], reverse=True)}


def publish_sim_results(
    session: Session,
    league_id: int,
    sim_id: int,
    feedback: Union[str, Dict, None] = None,
) -> Tuple[str, Dict]:
    """Publish simulation results"""
    league = get_league_by_id(session, league_id)

    simulation = session.get(SimulationResult, sim_id)
    if not simulation:
        raise SimulationResultNotFoundError(
            f"Simulation result with ID {sim_id} not found"
        )

    if simulation.league_id != league.id:
        raise SimulationResultNotFoundError(
            f"Simulation result with ID {sim_id} does not belong to league "
            f"'{league.name}'"
        )

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
    session: Session, league_id: int, expiry_date: datetime
) -> str:
    """Update league expiry date."""
    league = get_league_by_id(session, league_id)

    league.expiry_date = expiry_date
    session.add(league)
    session.commit()

    return f"Expiry date updated successfully for league '{league.name}'"


def update_league_info(session: Session, league_id: int, info_markdown: str) -> str:
    """Update the per-league markdown info block."""
    league = get_league_by_id(session, league_id)

    league.info_markdown = info_markdown or ""
    session.add(league)
    session.commit()
    return f"League info updated successfully for league '{league.name}'"


def assign_team_to_league(session: Session, team_id: int, league_id: int) -> str:
    """Assign a team to a league"""
    team = session.get(Team, team_id)
    if not team:
        raise TeamNotFoundError(f"Team with ID {team_id} not found")

    league = get_league_by_id(session, league_id)

    team.league_id = league.id
    session.add(team)
    session.commit()
    return f"Team '{team.name}' assigned to league '{league.name}'"


def unassign_team(session: Session, team_id: int) -> str:
    """Move a team back to the 'unassigned' league."""
    team = session.get(Team, team_id)
    if not team:
        raise TeamNotFoundError(f"Team with ID {team_id} not found")

    team.league_id = get_unassigned_league(session).id
    session.add(team)
    session.commit()
    return f"Team '{team.name}' moved to '{UNASSIGNED_LEAGUE_NAME}'"


def generate_signup_link(session: Session, league_id: int) -> Dict:
    """Generate a new signup link for a league"""
    league = get_league_by_id(session, league_id)

    signup_token = secrets.token_urlsafe(16)
    league.signup_link = signup_token
    session.add(league)
    session.commit()

    return {"signup_token": signup_token, "league_name": league.name}


# How long a password-reset link stays usable. Generous on purpose: a teacher
# may generate links in the evening for a class that runs the next day.
PASSWORD_RESET_LINK_HOURS = 48


def generate_team_password_reset(session: Session, team_id: int) -> Dict:
    """Create a one-time password-reset token for a team.

    Regenerating replaces any previous token, so a mis-shared link can be
    invalidated by generating a fresh one.
    """
    team = session.get(Team, team_id)
    if not team:
        raise TeamNotFoundError(f"Team with ID {team_id} not found")

    reset_token = secrets.token_urlsafe(16)
    team.password_reset_token = reset_token
    team.password_reset_expiry = utc_now() + timedelta(
        hours=PASSWORD_RESET_LINK_HOURS
    )
    session.add(team)
    session.commit()

    return {"reset_token": reset_token, "team_name": team.name}


def delete_league(session: Session, league_id: int) -> str:
    """Delete a league, moving its teams to the 'unassigned' league.

    The teams are reassigned *before* the delete, which is what keeps them: any
    row still pointing at the league when it goes is removed by ON DELETE
    CASCADE. Their submissions are deleted explicitly, because a submission's
    feedback is only meaningful next to the league it was scored in.
    """
    league = get_league_by_id(session, league_id)

    league_name = league.name
    if league_name == UNASSIGNED_LEAGUE_NAME:
        raise ProtectedLeagueError(
            f"Cannot delete the '{UNASSIGNED_LEAGUE_NAME}' league"
        )

    unassigned_league = get_unassigned_league(session)

    teams = session.exec(select(Team).where(Team.league_id == league.id)).all()
    team_count = len(teams)

    delete_submissions_for_teams(session, [team.id for team in teams])
    for team in teams:
        team.league_id = unassigned_league.id
        session.add(team)
    session.flush()

    # Simulation results and their items cascade with the league.
    session.delete(league)
    session.commit()

    return (
        f"League '{league_name}' deleted and {team_count} teams moved to the "
        "unassigned league"
    )


# --- agent teams -----------------------------------------------------------
# Teams driven over the /agent router with an API key instead of a password.


def create_agent_team(session: Session, team_data) -> Dict:
    """Create a new agent team in an agent-type league."""
    league = session.get(League, team_data.league_id)
    if not league:
        raise AgentTeamError(f"League with ID {team_data.league_id} not found")
    if league.league_type != LeagueType.AGENT:
        raise AgentTeamError("Can only create agent teams in agent leagues")

    team = Team(
        name=team_data.name,
        school_name="AI Agent",
        team_type=TeamType.AGENT,
        league_id=team_data.league_id,
    )
    session.add(team)
    session.commit()
    session.refresh(team)

    return {"team_id": team.id, "name": team.name, "league": league.name}


def create_api_key(session: Session, team_id: int) -> Dict:
    """Create a new API key for an agent team."""
    team = session.get(Team, team_id)
    if not team:
        raise AgentTeamError(f"Team with ID {team_id} not found")
    if team.team_type != TeamType.AGENT:
        raise AgentTeamError("Can only create API keys for agent teams")

    api_key = secrets.token_urlsafe(32)

    key_record = AgentAPIKey(key=api_key, team_id=team_id)
    session.add(key_record)
    session.commit()

    return {"team_id": team_id, "api_key": api_key}
