
import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM

# --- Blackbox adversarial player ---
def blackbox(history, turn, total_turns, valid_actions):
    """
    Fixed adversarial strategy:
    - 1st turn: 'fire'
    - 2nd turn: 'air'
    - 3rd+ turn: imitate opponent's action from turn-2 (the time before last)
    Args:
        history: list of dicts, each with keys: 'blackbox_action', 'player_action', 'result'
        turn: int, current turn (1-based)
        total_turns: int, total number of turns in the game
        valid_actions: list of str, all valid actions
    Returns:
        action: str, one of valid_actions
    """
    if turn == 1:
        return 'fire'
    elif turn == 2:
        return 'air'
    else:
        # Imitate opponent's action from turn-2 (the time before last)
        if len(history) >= 2:
            prev_action = history[-2]['player_action']
            if prev_action in valid_actions:
                return prev_action
            else:
                # fallback to a valid action if somehow not valid
                return valid_actions[0]
        else:
            # fallback to a valid action
            return valid_actions[0]

# --- Platform (judger) ---
def platform(settings, player):
    """
    Simulate a game of rock, paper, scissors, fire, water, air, sponge.
    Args:
        settings: dict, must contain at least 'total_turns'
        player: an object with .normal_output(str) method
    Returns:
        player_score: float
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
    # Only total_turns is public
    public_settings = {'total_turns': total_turns}
    # Game state history
    history = []
    player_score = 0.0

    for turn in range(1, total_turns + 1):
        # Prepare info for blackbox
        blackbox_info = (history, turn, total_turns, valid_actions)
        # Prepare info for player (natural language)
        if turn == 1:
            player_prompt = (
                f"This is turn {turn} of {total_turns} in the game. "
                f"Valid actions are: {', '.join(valid_actions)}. "
                "There is no previous turn. Please reply with your action (one of the valid actions) only."
            )
        else:
            last = history[-1]
            player_prompt = (
                f"This is turn {turn} of {total_turns} in the game rock, paper, scissors, fire, water, air, sponge. "
                f"Valid actions are: {', '.join(valid_actions)}. "
                f"Last turn, you played '{last['player_action']}', your opponent played '{last['blackbox_action']}'. "
                f"Result: {last['result']}. "
            )
        # Get actions
        blackbox_action = blackbox(*blackbox_info)
        player_action = player.normal_output(player_prompt)
        # Validate player_action
        while True:
            if not isinstance(player_action, str):
                player_action = player.normal_output(
                    f"Your action was not a string. Please reply with a single valid action (one of: {', '.join(valid_actions)})."
                )
                continue
            action = player_action.strip().lower()
            if action not in valid_actions:
                player_action = player.normal_output(
                    f"Your action '{player_action}' is invalid. Please reply with a single valid action (one of: {', '.join(valid_actions)})."
                )
                continue
            player_action = action
            break
        # Determine result
        if blackbox_action == player_action:
            result = 'tie'
            player_score += 0.0
        elif player_action in beats and blackbox_action in beats:
            if blackbox_action in beats[player_action]:
                result = 'win'
                player_score += 1.0
            elif player_action in beats[blackbox_action]:
                result = 'lose'
                player_score += -1.0
            else:
                # Should not happen, treat as tie
                result = 'tie'
                player_score += 0.0
        else:
            # Should not happen, treat as tie
            result = 'tie'
            player_score += 0.0
        # Record history
        history.append({
            'turn': turn,
            'blackbox_action': blackbox_action,
            'player_action': player_action,
            'result': result
        })
    return player_score

# --- Main function ---
def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    player.evaluate(failure_num, version, max_turns)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
