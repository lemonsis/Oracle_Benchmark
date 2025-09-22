
import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM

# --- Blackbox adversarial player ---
def blackbox(last_opponent_action=None, turn_id=None, total_turns=None, valid_actions=None):
    """
    Implements the fixed adversarial strategy:
    - First turn: always play 'rock'
    - Subsequent turns: play an action that beats the opponent's last action
    """
    # Define the win map: for each action, which actions it beats
    win_map = {
        "rock":     ["scissors", "sponge", "fire"],
        "paper":    ["rock", "water", "air"],
        "scissors": ["paper", "sponge", "fire"],
        "fire":     ["scissors", "paper", "sponge"],
        "water":    ["rock", "fire", "scissors"],
        "air":      ["fire", "rock", "water"],
        "sponge":   ["water", "paper", "air"]
    }
    # First turn: play 'rock'
    if turn_id == 0 or last_opponent_action is None:
        return "rock"
    # Otherwise: pick an action that beats opponent's last action
    for action, beats in win_map.items():
        if last_opponent_action in beats:
            return action
    # Fallback (should not happen): play 'rock'
    return "rock"

# --- Platform (game judger) ---
def platform(settings, player):
    """
    Simulates the game and returns the score of the player.
    """
    # Game settings
    total_turns = settings.get("total_turns")
    valid_actions = ["rock", "paper", "scissors", "fire", "water", "air", "sponge"]
    win_map = {
        "rock":     ["scissors", "sponge", "fire"],
        "paper":    ["rock", "water", "air"],
        "scissors": ["paper", "sponge", "fire"],
        "fire":     ["scissors", "paper", "sponge"],
        "water":    ["rock", "fire", "scissors"],
        "air":      ["fire", "rock", "water"],
        "sponge":   ["water", "paper", "air"]
    }
    # Only public settings are sent to players
    public_settings = {
        "total_turns": total_turns,
        "valid_actions": valid_actions
    }
    # Game state
    player_score = 0.0
    blackbox_score = 0.0
    last_player_action = None
    last_blackbox_action = None
    last_result = None

    for turn_id in range(total_turns):
        # --- Prepare info for both players ---
        # Info for blackbox (as arguments)
        blackbox_input = {
            "last_opponent_action": last_player_action,
            "turn_id": turn_id,
            "total_turns": total_turns,
            "valid_actions": valid_actions
        }
        # Info for player (as a string)
        player_info = f"Turn {turn_id+1} of {total_turns}.\n"
        if turn_id == 0:
            player_info += "This is the first turn. No previous actions.\n"
        else:
            player_info += f"Last turn, you played '{last_player_action}', your opponent played '{last_blackbox_action}'.\n"
            if last_result == 0:
                player_info += "It was a tie.\n"
            elif last_result == 1.0:
                player_info += "You won last turn.\n"
            else:
                player_info += "You lost last turn.\n"
        player_info += f"Valid actions: {', '.join(valid_actions)}.\n"

        # --- Get actions ---
        # Blackbox action
        blackbox_action = blackbox(**blackbox_input)
        # Player action (with validation loop)
        while True:
            player_action = player.normal_output(player_info)
            # Validate format: must be a string, in valid_actions, lowercase, no extra text
            if not isinstance(player_action, str):
                player_info = ("Invalid format. ONLY output the action without any extra text and symbols. "
                               f"Valid actions: {', '.join(valid_actions)}.")
                continue
            player_action = player_action.strip().lower()

            if player_action not in valid_actions:
                player_info = (f"Invalid action: '{player_action}'. Your action must be one of: {', '.join(valid_actions)}. "
                               "ONLY output the action without any extra text and symbols. ")
                continue
            break

        # --- Judge the result ---
        if player_action == blackbox_action:
            player_score += 0
            blackbox_score += 0
            last_result = 0
        elif blackbox_action in win_map[player_action]:
            player_score += 1.0
            blackbox_score -= 1.0
            last_result = 1.0
        elif player_action in win_map[blackbox_action]:
            blackbox_score += 1.0
            player_score -= 1.0
            last_result = -1.0
        else:
            # Should not happen, but treat as tie
            player_score += 0
            blackbox_score += 0
            last_result = 0

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
