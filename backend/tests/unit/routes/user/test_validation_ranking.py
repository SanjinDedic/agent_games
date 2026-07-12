"""_validation_ranking derives the team's rank against the validation bots
from a ValidationResponse dict (competition ranking: ties share a rank)."""

from backend.routes.user.user_router import _validation_ranking


def _response(total_points):
    return {"simulation_results": {"total_points": total_points}}


def test_top_of_the_table_is_rank_one():
    result = _response({"my_team": 30, "bot_a": 20, "bot_b": 10})
    assert _validation_ranking(result, "my_team") == 1


def test_rank_counts_only_strictly_higher_scores():
    result = _response({"bot_a": 30, "my_team": 20, "bot_b": 10})
    assert _validation_ranking(result, "my_team") == 2


def test_tied_scores_share_a_rank():
    result = _response({"bot_a": 30, "my_team": 20, "bot_b": 20, "bot_c": 10})
    assert _validation_ranking(result, "my_team") == 2


def test_missing_simulation_results_gives_none():
    assert _validation_ranking({"simulation_results": None}, "my_team") is None


def test_missing_total_points_gives_none():
    assert _validation_ranking({"simulation_results": {}}, "my_team") is None


def test_team_absent_from_points_gives_none():
    assert _validation_ranking(_response({"bot_a": 30}), "my_team") is None
