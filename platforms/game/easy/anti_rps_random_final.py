
import os
import sys
import random

current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM

def blackbox(last_result=None, history=None, total_turns=None, current_turn=None):
    """
    Adversarial player for Anti Rock, Paper, Scissors.
    Chooses 'rock' or 'scissors' with equal probability.
    Args:
        last_result: (optional) result of last turn, can be ignored.
        history: (optional) list of previous actions/results, can be ignored.
        total_turns: (optional) total number of turns in the game.
        current_turn: (optional) current turn number (1-based).
    Returns:
        action: str, one of 'rock', 'paper', 'scissors'
    """
    return random.choice(['rock', 'scissors'])

def platform(settings, player):
    """
    Game platform (judger) for Anti Rock, Paper, Scissors.
    Args:
        settings: dict, must contain 'total_turns' (int)
        player: an object with method normal_output(str) -> str
    Returns:
        player_score: float, total score of the player
    """
    # Extract settings
    total_turns = settings.get('total_turns')
    if not isinstance(total_turns, int) or total_turns <= 0:
        raise ValueError("settings['total_turns'] must be a positive integer.")

    # Only 'total_turns' is public and should be sent to both players
    public_settings = {'total_turns': total_turns}

    # Game state
    history = []  # Each element: (turn, player_action, blackbox_action, result)
    player_score = 0.0

    # For each turn
    last_result = None
    for turn in range(1, total_turns + 1):
        # Prepare info for blackbox
        blackbox_input = {
            'last_result': last_result,
            'history': history.copy(),
            'total_turns': total_turns,
            'current_turn': turn
        }
        blackbox_action = blackbox(**blackbox_input)

        # Prepare info for player in natural language
        if last_result is None:
            last_result_str = "This is the first turn."
        else:
            last_result_str = (
                f"Last turn, you played '{history[-1][1]}', your opponent played '{history[-1][2]}'. "
                f"Result: {last_result}."
            )
        state_str = (
            f"{last_result_str} "
            f"This is turn {turn} out of {total_turns} in the game. "
            "Each turn, both players choose one of 'rock', 'paper', or 'scissors'. "
        )

        # Get player action, check validity
        valid_actions = {'rock', 'paper', 'scissors'}
        for _ in range(3):  # Allow up to 3 attempts
            player_action = player.normal_output(state_str).strip().lower()
            if player_action in valid_actions:
                break
            else:
                state_str = (
                    f"Your previous action '{player_action}' was invalid. "
                    "Please reply with ONLY one of: 'rock', 'paper', or 'scissors' (all lowercase, no punctuation)."
                )
        else:
            # If still invalid after 3 tries, default to 'rock'
            player_action = 'rock'

        # Determine result
        # Anti RPS rules: scissors beat rock, paper beats scissors, rock beats paper
        # Returns: 'win', 'lose', 'tie' (from player's perspective)
        def anti_rps_result(p1, p2):
            if p1 == p2:
                return 'tie'
            if (p1, p2) in [('scissors', 'rock'), ('paper', 'scissors'), ('rock', 'paper')]:
                return 'win'
            else:
                return 'lose'

        result = anti_rps_result(player_action, blackbox_action)
        if result == 'win':
            player_score += 1.0
        elif result == 'tie':
            player_score += 0
        else:
            player_score -= 1.0
        # else: lose, 0 point

        # Update history and last_result
        history.append((turn, player_action, blackbox_action, result))
        last_result = result

    return player_score

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    player.evaluate(failure_num, version, max_turns)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
