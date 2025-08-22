
import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM

# --- Blackbox adversarial player ---
def blackbox(last_opponent_action=None, total_turns=None, current_turn=None):
    """
    Fixed adversarial strategy for rock, paper, scissors, fire, water, air, sponge.
    last_opponent_action: str or None, the action the opponent played last turn.
    total_turns: int, total number of turns in the game.
    current_turn: int, current turn number (1-based).
    Returns: str, one of ['rock', 'paper', 'scissors', 'fire', 'water', 'air', 'sponge']
    """
    # Mapping from last opponent action to blackbox's action
    strategy = {
        'rock': 'fire',
        'paper': 'water',
        'scissors': 'air',
        'fire': 'sponge',
        'water': 'rock',
        'air': 'paper',
        'sponge': 'scissors'
    }
    # On first turn, pick a default action (e.g., 'rock')
    if last_opponent_action is None:
        return 'rock'
    return strategy.get(last_opponent_action, 'rock')

# --- Platform (judger) ---
def platform(settings, player):
    """
    settings: dict, must contain 'total_turns' (int)
    player: an object with method normal_output(str) -> str
    Returns: float, the total score of the player
    """
    # Game constants
    actions = ['rock', 'paper', 'scissors', 'fire', 'water', 'air', 'sponge']
    total_turns = settings.get('total_turns', 10)
    # Win map: for each action, the set of actions it beats
    win_map = {
        'rock':     {'scissors', 'sponge', 'fire'},
        'paper':    {'rock', 'water', 'air'},
        'scissors': {'paper', 'sponge', 'fire'},
        'fire':     {'scissors', 'paper', 'sponge'},
        'water':    {'rock', 'fire', 'scissors'},
        'air':      {'fire', 'rock', 'water'},
        'sponge':   {'water', 'paper', 'air'}
    }

    # Game state
    player_score = 0.0
    last_player_action = None
    last_blackbox_action = None
    last_result = None  # 'win', 'lose', 'tie'
    # For first turn, no last actions

    for turn in range(1, total_turns + 1):
        # --- Prepare info for both players ---
        # Info for blackbox (as arguments)
        blackbox_input = {
            'last_opponent_action': last_player_action,
            'total_turns': total_turns,
            'current_turn': turn
        }
        # Info for player (as a string)
        player_info = []
        if turn == 1:
            player_info.append(f"This is turn 1 of {total_turns}.")
            player_info.append("No previous actions yet.")
        else:
            player_info.append(f"Turn {turn} of {total_turns}.")
            player_info.append(f"Last turn, you played '{last_player_action}', your opponent played '{last_blackbox_action}'.")
            if last_result == 'win':
                player_info.append("You won last turn.")
            elif last_result == 'lose':
                player_info.append("You lost last turn.")
            else:
                player_info.append("Last turn was a tie.")
        player_info.append("Available actions: rock, paper, scissors, fire, water, air, sponge.")
        player_info_str = " ".join(player_info)

        # --- Get actions ---
        # Blackbox action
        blackbox_action = blackbox(
            last_opponent_action=last_player_action,
            total_turns=total_turns,
            current_turn=turn
        )
        # Player action, with validation loop
        while True:
            player_action = player.normal_output(player_info_str)
            # Validate: must be a string, one of actions (case-insensitive, allow whitespace)
            if isinstance(player_action, str):
                action_clean = player_action.strip().lower()
                if action_clean in actions:
                    player_action = action_clean
                    break
            # If invalid, re-ask with warning
            warn_info = (
                f"Your last response '{player_action}' is invalid. "
                f"Please reply with exactly one of these actions: {', '.join(actions)}. "
                "No extra text, case-insensitive, no punctuation, no explanation."
            )
            player_info_str = warn_info

        # --- Judge result ---
        if player_action == blackbox_action:
            player_score += 0
            last_result = 'tie'
        elif blackbox_action in win_map[player_action]:
            player_score += 1.0
            last_result = 'win'
        else:
            player_score -= 1.0
            last_result = 'lose'
        # Update last actions
        last_player_action = player_action
        last_blackbox_action = blackbox_action

    return player_score

# --- Main function ---
def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    player.evaluate(failure_num, version, max_turns)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
