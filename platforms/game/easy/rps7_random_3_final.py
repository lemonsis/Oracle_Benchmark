
import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM
import random

# --- Blackbox adversarial player ---
def blackbox(last_result=None, turn=None, total_turns=None, valid_actions=None):
    """
    Fixed adversarial strategy: chooses randomly among 'rock', 'paper', 'air' with equal probability.
    Args:
        last_result: dict or None, info about last turn (can be ignored for this strategy)
        turn: int, current turn number (1-based)
        total_turns: int, total number of turns in the game
        valid_actions: list of str, valid actions in the game
    Returns:
        action: str, one of 'rock', 'paper', 'air'
    """
    choices = ['rock', 'paper', 'air']
    return random.choice(choices)

# --- Platform (game judger) ---
def platform(settings, player):
    """
    Simulates a game of rock, paper, scissors, fire, water, air, sponge between blackbox and player.
    Args:
        settings: dict, must contain 'total_turns' (int)
        player: an object with a .normal_output(str) method
    Returns:
        player_score: float, total score of the player
    """
    # Game rules
    valid_actions = ['rock', 'paper', 'scissors', 'fire', 'water', 'air', 'sponge']
    # Who beats whom (each action: set of actions it beats)
    beats = {
        'rock':     {'scissors', 'sponge', 'fire'},
        'paper':    {'rock', 'water', 'air'},
        'scissors': {'paper', 'sponge', 'fire'},
        'fire':     {'scissors', 'paper', 'sponge'},
        'water':    {'rock', 'fire', 'scissors'},
        'air':      {'fire', 'rock', 'water'},
        'sponge':   {'water', 'paper', 'air'},
    }
    total_turns = settings.get('total_turns', 10)
    player_score = 0.0
    last_result = None

    for turn in range(1, total_turns + 1):
        # Prepare info for both players
        public_settings = {
            'total_turns': total_turns,
            'valid_actions': valid_actions
        }
        # Info for blackbox (can be any format)
        blackbox_action = blackbox(
            last_result=last_result,
            turn=turn,
            total_turns=total_turns,
            valid_actions=valid_actions
        )

        # Info for player (natural language string)
        if last_result is None:
            last_result_str = "This is the first turn."
        else:
            last_result_str = (
                f"Last turn: You played '{last_result['player_action']}', "
                f"opponent played '{last_result['blackbox_action']}'. "
                f"Result: {last_result['result_str']}."
            )
        state_str = (
            f"{last_result_str}\n"
            f"Turn {turn} of {total_turns}.\n"
            f"Valid actions: {', '.join(valid_actions)}.\n"
        )
        player_action = player.normal_output(state_str)

        # Validate player action
        while True:
            if not isinstance(player_action, str):
                warn = (
                    f"Your action was not a string. Please reply with a single word, "
                    f"exactly one of: {', '.join(valid_actions)}."
                )
                player_action = player.normal_output(warn)
                continue
            action = player_action.strip().lower()
            if action not in valid_actions:
                warn = (
                    f"**DO NOT output any extra text or symbols** "
                    f"Only contain the action"
                )
                player_action = player.normal_output(warn)
                continue
            break
        player_action = action

        # Determine result
        if player_action == blackbox_action:
            player_point = 0
            result_str = "Tie"
        elif blackbox_action in beats[player_action]:
            player_point = 1.0
            result_str = "You win"
        elif player_action in beats[blackbox_action]:
            player_point = -1.0
            result_str = "You lose"
        else:
            # Should not happen, but fallback to tie
            player_point = 0
            result_str = "Tie"
        player_score += player_point

        # Prepare last_result for next turn
        last_result = {
            'player_action': player_action,
            'blackbox_action': blackbox_action,
            'result_str': result_str,
            'player_point': player_point,
            'turn': turn
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
