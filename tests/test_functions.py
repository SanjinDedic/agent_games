import pytest
from unittest.mock import patch, MagicMock, mock_open
from api import run_game
from api import Source_Data
from game_simulation import GameSimulation

def test_initialization():
    simulation = GameSimulation()
    assert simulation.folder_name == "test_classes"

def test_set_folder(mocker):
    mocker.patch('os.listdir', return_value=[])
    simulation = GameSimulation()
    simulation.set_folder("new_folder")
    assert simulation.folder_name == "new_folder"

def test_run_simulation_many_times(mocker):
    MockPlayerClass = MagicMock()
    mocker.patch.object(GameSimulation, 'get_all_player_classes_from_folder', return_value=[(MockPlayerClass, 'player.py')])
    mocker.patch('game.Game.play_game', return_value={'banked_money': {'player': 100}})
    simulation = GameSimulation()
    results = simulation.run_simulation_many_times(1)
    assert 'player' in results


def test_assign_points():
    simulation = GameSimulation()
    game_result = {'banked_money': {'Player1': 100, 'Player2': 50}}
    points = simulation.assign_points(game_result)
    assert points['Player1'] > points['Player2']



# Test for GameSimulation class
def test_get_all_player_classes_from_folder(mocker):
    mocker.patch('os.listdir', return_value=['player.py'])

    # Mocking os.path.exists to simulate the folder existence
    mocker.patch('os.path.exists', return_value=True)

    # Mocking importlib to simulate module import and no Player subclass
    mocked_module = MagicMock()
    mocked_module.Player = MagicMock()  # Simulating Player class
    with patch('importlib.util.spec_from_file_location') as mock_spec:
        with patch('importlib.util.module_from_spec') as mock_mod:
            mock_spec.return_value = MagicMock()
            mock_mod.return_value = mocked_module

            simulation = GameSimulation()
            players = simulation.get_all_player_classes_from_folder()
            print(players)
            assert players == []

@pytest.mark.asyncio
async def test_run_game_valid_data():
    source_data = Source_Data(
        team_name="TestTeam",
        password="TestPassword",
        code="print('Hello World')"
    )
    with patch('builtins.open', mock_open(read_data='{"teams": [{"name": "TestTeam", "password": "TestPassword"}]}')):
        response = await run_game(source_data)
        assert response == {"invalid": "Print statements are not allowed"}

@pytest.mark.asyncio
@pytest.mark.parametrize("code", ["print", "exec", "eval(", "open(", "import random\nimport os"])
async def test_run_game_invalid_data(code):
    data = MagicMock()
    data.code = code
    result = await run_game(data)
    assert 'invalid' in result

@pytest.mark.asyncio
async def test_run_game_team_not_found():
    data = MagicMock()
    data.team_name = "test_team"
    data.password = "test_password"
    with patch('json.load', return_value={'teams': [{'name': 'other_team', 'password': 'other_password'}]}):
        result = await run_game(data)
    assert 'Error' in result

@pytest.mark.asyncio
async def test_run_game_no_class_definition():
    data = MagicMock()
    data.code = "def test_function(): pass"
    data.team_name = "test_team"
    data.password = "test_password"
    with patch('json.load', return_value={'teams': [{'name': 'test_team', 'password': 'test_password'}]}):
        result = await run_game(data)
    assert 'Error' in result

@pytest.mark.asyncio
async def test_run_game_simulation_exception():
    data = MagicMock()
    data.code = "class TestClass(): pass"
    data.team_name = "test_team"
    data.password = "test_password"
    with patch('json.load', return_value={'teams': [{'name': 'test_team', 'password': 'test_password'}]}):
        with patch('api.GameSimulation.run_simulation_many_times', side_effect=Exception('Test exception')):
            result = await run_game(data)
    assert 'Error' in result


def test_run_simulation_many_times_different_runs(mocker):
    MockPlayerClass = MagicMock()
    mocker.patch.object(GameSimulation, 'get_all_player_classes_from_folder', return_value=[(MockPlayerClass, 'player.py')])
    mocker.patch('game.Game.play_game', return_value={'banked_money': {'player': 100}})
    simulation = GameSimulation()
    results = simulation.run_simulation_many_times(10)
    assert 'player' in results

def test_log_results():
    # Arrange
    simulation = GameSimulation()
    number = 10
    total_points = {'player1': 100, 'player2': 50}
    expected_output = "10 games were played\nplayer1 earned a total of 100 points\nplayer2 earned a total of 50 points"

    # Act
    with patch("builtins.open", mock_open()) as mock_file:
        simulation.log_results(number, total_points)

    # Assert
    mock_file().write.assert_called_with(expected_output)


def test_run_simulation_with_animation(mocker):
    mock_filename = 'TestPlayer.py'
    MockPlayerClass = MagicMock()
    MockPlayerClass.name = mock_filename[:-3]  # This should match the key used in total_points

    mocker.patch.object(
        GameSimulation, 
        'get_all_player_classes_from_folder', 
        return_value=[(MockPlayerClass, mock_filename)]
    )
    mocker.patch(
        'game.Game.play_game', 
        return_value={'banked_money': {MockPlayerClass.name: 100}}
    )

    simulation = GameSimulation()
    simulation.team_colors = ["red", "blue"]  # Example colors
    simulation.run_simulation_with_animation(10)
    assert True
