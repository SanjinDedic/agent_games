import random

from backend.games.breakthrough.player import Player


def _step_toward(delta_x, delta_y):
    """Direction that closes the larger axis gap."""
    if abs(delta_x) >= abs(delta_y) and delta_x != 0:
        return "E" if delta_x > 0 else "W"
    if delta_y != 0:
        return "N" if delta_y > 0 else "S"
    return "STAY"


def _dodge(my_y, grid_size, turn):
    """Alternating N/S feint that stays off the top and bottom edges."""
    direction = "N" if (turn // 3) % 2 == 0 else "S"
    if my_y >= grid_size - 2:
        direction = "S"
    elif my_y <= 1:
        direction = "N"
    return direction


def _last_delta(trace):
    """The opponent's most recent move, read from their trail."""
    if len(trace) < 2:
        return (0, 0)
    (x0, y0), (x1, y1) = trace[-2], trace[-1]
    return (x1 - x0, y1 - y0)


def _keeper_defend(game_state):
    """WallKeeper's defender line: wall three columns ahead, mirror the row,
    chase hard if the attacker slips past."""
    my_x, my_y = game_state["my_pos"]
    opp_x, opp_y = game_state["opp_pos"]
    boosts = game_state["my_boosts"]
    grid_size = game_state["grid_size"]

    if opp_x > my_x:
        direction = _step_toward(opp_x - my_x, opp_y - my_y)
        return {"direction": direction, "boost": boosts > 0 and direction != "STAY"}
    dy = opp_y - my_y
    if dy != 0:
        direction = "N" if dy > 0 else "S"
        return {"direction": direction, "boost": boosts > 2 and abs(dy) >= 3}
    target_x = min(opp_x + 3, grid_size - 2)
    if my_x != target_x:
        return "E" if target_x > my_x else "W"
    return "STAY"


def _keeper_attack(game_state):
    """WallKeeper's attacker line: zigzag the defender off their line, then
    burst through."""
    my_x, my_y = game_state["my_pos"]
    opp_x, opp_y = game_state["opp_pos"]
    boosts = game_state["my_boosts"]
    grid_size = game_state["grid_size"]

    if opp_y == my_y and 0 < opp_x - my_x <= 2:
        if boosts > 0 and opp_x - my_x == 1:
            return {"direction": "E", "boost": True}
        return _dodge(my_y, grid_size, game_state["turn"])
    if abs(opp_y - my_y) >= 2 or opp_x <= my_x:
        return "E"
    return _dodge(my_y, grid_size, game_state["turn"])


class RandomWanderer(Player):
    strategy = (
        "Moves in a random direction every turn and occasionally burns a boost. "
        "The chaos baseline — beat this before anything else."
    )

    def make_decision(self, game_state):
        direction = random.choice(["N", "S", "E", "W"])
        boost = game_state["my_boosts"] > 0 and random.random() < 0.05
        return {"direction": direction, "boost": boost}


class Rusher(Player):
    strategy = (
        "As attacker: sprints straight for the right edge and boost-jumps over the "
        "defender when blocked. As defender: runs directly at the attacker, boosting "
        "to close big gaps."
    )

    def make_decision(self, game_state):
        my_x, my_y = game_state["my_pos"]
        opp_x, opp_y = game_state["opp_pos"]
        boosts = game_state["my_boosts"]

        if game_state["role"] == "attacker":
            if opp_y == my_y and 0 < opp_x - my_x <= 2:
                if boosts > 0 and opp_x - my_x == 1:
                    self.add_feedback(f"Turn {game_state['turn']}: jumping the defender")
                    return {"direction": "E", "boost": True}
                return _dodge(my_y, game_state["grid_size"], game_state["turn"])
            return "E"

        dx, dy = opp_x - my_x, opp_y - my_y
        direction = _step_toward(dx, dy)
        gap = abs(dx) if direction in ("E", "W") else abs(dy)
        boost = boosts > 0 and direction != "STAY" and gap >= 4
        return {"direction": direction, "boost": boost}


class WallKeeper(Player):
    strategy = (
        "As defender: holds a wall three columns ahead of the attacker and mirrors "
        "their row, boosting to recover if they slip past. As attacker: zigzags to "
        "pull the defender off their line, then bursts through."
    )

    def make_decision(self, game_state):
        if game_state["role"] == "defender":
            return _keeper_defend(game_state)
        return _keeper_attack(game_state)


class Juker(Player):
    strategy = (
        "As attacker: reads the defender's last move from their trail and jukes the "
        "opposite way before bursting through. As defender: shadows the attacker "
        "tightly, copying their row moves and saving boosts to re-catch after a jump."
    )

    def make_decision(self, game_state):
        my_x, my_y = game_state["my_pos"]
        opp_x, opp_y = game_state["opp_pos"]
        boosts = game_state["my_boosts"]
        grid_size = game_state["grid_size"]
        _, opp_dy = _last_delta(game_state["opp_trace"])

        if game_state["role"] == "attacker":
            if opp_x - my_x > 3 or opp_x < my_x:
                return "E"
            if abs(opp_y - my_y) >= 2:
                # Defender is off my row — burst through the gap
                if boosts > 0 and 0 < opp_x - my_x <= 2:
                    return {"direction": "E", "boost": True}
                return "E"
            # Defender is close and on/near my row: juke against their last move
            if opp_dy > 0 and my_y > 1:
                return "S"
            if opp_dy < 0 and my_y < grid_size - 2:
                return "N"
            return _dodge(my_y, grid_size, game_state["turn"])

        # Defender: shadow the attacker's row from two columns ahead
        if opp_x > my_x:
            direction = _step_toward(opp_x - my_x, opp_y - my_y)
            return {"direction": direction, "boost": boosts > 0 and direction != "STAY"}
        dy = opp_y - my_y
        if dy != 0:
            direction = "N" if dy > 0 else "S"
            return {"direction": direction, "boost": boosts > 4 and abs(dy) >= 3}
        target_x = min(opp_x + 2, grid_size - 2)
        if my_x != target_x:
            return "E" if target_x > my_x else "W"
        return "STAY"


_MOVE_DELTAS = {"N": (0, 1), "S": (0, -1), "E": (1, 0), "W": (-1, 0), "STAY": (0, 0)}


def _landing(pos, direction, boost, grid_size):
    """Where a move ends up, mirroring the engine (off-grid = stay put)."""
    dx, dy = _MOVE_DELTAS[direction]
    step = 2 if boost else 1
    nx, ny = pos[0] + dx * step, pos[1] + dy * step
    if not (0 <= nx < grid_size and 0 <= ny < grid_size):
        return tuple(pos)
    return (nx, ny)


def _parse_move(move):
    """(direction, boost) from a move in either return format."""
    if isinstance(move, dict):
        return move.get("direction", "STAY"), bool(move.get("boost", False))
    return move, False


class MineTrapper(Player):
    strategy = (
        "Plays WallKeeper's game, with one trick: as attacker, the moment the "
        "defender closes in for the catch it mines its own cell and dodges — the "
        "chaser lunges onto the mine and is out of the match."
    )

    def make_decision(self, game_state):
        if game_state["role"] == "defender":
            return _keeper_defend(game_state)

        if game_state["opp_frozen"]:
            return "E"  # defender is blown up — stroll to the goal

        move = _keeper_attack(game_state)
        my_x, my_y = game_state["my_pos"]
        opp_x, opp_y = game_state["opp_pos"]
        about_to_be_caught = abs(opp_x - my_x) + abs(opp_y - my_y) <= 2
        if about_to_be_caught and game_state["my_mines"] > 0:
            if isinstance(move, str):
                move = {"direction": move}
            move["mine"] = True
            self.add_feedback(
                f"Turn {game_state['turn']}: mining my cell — come and get me"
            )
        return move


class MineAvoider(Player):
    strategy = (
        "Plays WallKeeper's game but refuses to die to a mine: once the opponent's "
        "mine is laid it never ends a move on any cell of their trace (the only "
        "places a mine can be), and it won't lunge onto the cell of an opponent "
        "still holding one."
    )

    def _risky(self, cell, game_state):
        if game_state["opp_mines"] == 0:
            # Their mine is armed somewhere along their trail
            if cell in {tuple(c) for c in game_state["opp_trace"]}:
                return True
        elif cell == tuple(game_state["opp_pos"]):
            # They may mine the cell they stand on this very turn
            return True
        return False

    def make_decision(self, game_state):
        role = game_state["role"]
        move = _keeper_defend(game_state) if role == "defender" else _keeper_attack(game_state)

        my_pos = tuple(game_state["my_pos"])
        opp_x, opp_y = game_state["opp_pos"]
        grid_size = game_state["grid_size"]
        direction, boost = _parse_move(move)
        if not self._risky(_landing(my_pos, direction, boost, grid_size), game_state):
            return move

        # Planned move ends on a possible mine — take the best safe step instead
        if role == "attacker":
            target = (grid_size - 1, my_pos[1])
        else:
            ldx, ldy = _last_delta(game_state["opp_trace"])
            target = (opp_x + ldx, opp_y + ldy)  # cut off where they're heading

        def closeness(d):
            lx, ly = _landing(my_pos, d, False, grid_size)
            return abs(target[0] - lx) + abs(target[1] - ly)

        for alt in sorted(["N", "S", "E", "W"], key=closeness):
            if not self._risky(_landing(my_pos, alt, False, grid_size), game_state):
                self.add_feedback(
                    f"Turn {game_state['turn']}: dodging a possible mine, going {alt}"
                )
                return alt
        return "STAY"  # the cell we stand on is always mine-free


players = [
    RandomWanderer(),
    Rusher(),
    WallKeeper(),
    Juker(),
    MineTrapper(),
    MineAvoider(),
]
