
import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM

# --- Blackbox adversarial player ---
def blackbox(last_result, game_state, public_settings):
    """
    Fixed strategy: cycles through ['rock', 'paper', 'scissors', 'fire', 'water', 'air', 'sponge'] in order.
    - last_result: dict or None, info about last turn (can be ignored for this strategy)
    - game_state: dict, must contain 'turn' (int, 0-based)
    - public_settings: dict, must contain 'total_turns'
    """
    moves = ['rock', 'paper', 'scissors', 'fire', 'water', 'air', 'sponge']
    turn = game_state.get('turn', 0)
    return moves[turn % 7]

# --- Judger/platform ---
def platform(settings, player):
    """
    settings: dict, must contain 'total_turns' (int)
    player: an object with .normal_output(str) -> str
    Returns: float, the total score of the player
    """
    # Game rules: who beats whom
    beats = {
        'rock':     ['scissors', 'sponge', 'fire'],
        'paper':    ['rock', 'water', 'air'],
        'scissors': ['paper', 'sponge', 'fire'],
        'fire':     ['scissors', 'paper', 'sponge'],
        'water':    ['rock', 'fire', 'scissors'],
        'air':      ['fire', 'rock', 'water'],
        'sponge':   ['water', 'paper', 'air'],
    }
    valid_moves = set(beats.keys())
    total_turns = settings['total_turns']
    player_score = 0.0

    last_result = None
    for turn in range(total_turns):
        # Prepare game state and public settings
        game_state = {'turn': turn}
        public_settings = {'total_turns': total_turns}

        # --- Get blackbox move ---
        blackbox_action = blackbox(last_result, game_state, public_settings)

        # --- Get player move ---
        # Compose info string for player
        info = f"You are playing Rock, Paper, Scissors, Fire, Water, Air, Sponge. Valid moves: rock, paper, scissors, fire, water, air, sponge.\n"
        info += f"This is turn {turn+1} out of {total_turns}.\n"
        if last_result is not None:
            info += f"Last turn: You played '{last_result['player_action']}', opponent played '{last_result['blackbox_action']}'. "
            if last_result['result'] == 0:
                info += "It was a tie.\n"
            elif last_result['result'] == 1.0:
                info += "You won last turn.\n"
            else:
                info += "You lost last turn.\n"
        else:
            info += "This is the first turn.\n"

        # Get and validate player action
        while True:
            player_action = player.normal_output(info)
            if not isinstance(player_action, str):
                info = "Invalid format: your reply must be a single word (e.g., 'rock'). Please try again."
                continue
            action = player_action.strip().lower()
            if action not in valid_moves:
                info = f"Invalid move: '{player_action}'. Valid moves are: rock, paper, scissors, fire, water, air, sponge. ONLY output the action without any extra text or symbols."
                continue
            break

        # --- Judging ---
        if action == blackbox_action:
            result = 0  # tie
        elif blackbox_action in beats[action]:
            result = 1.0  # player wins
        elif action in beats[blackbox_action]:
            result = -1.0  # player loses
        else:
            # Should not happen, but fallback to tie
            result = 0

        player_score += result

        # Prepare last_result for next turn
        last_result = {
            'player_action': action,
            'blackbox_action': blackbox_action,
            'result': result
        }

    return player_score

# --- Main function ---
def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    player.evaluate(failure_num, version, max_turns)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
