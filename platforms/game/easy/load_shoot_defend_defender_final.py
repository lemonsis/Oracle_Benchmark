import os
import sys

# Set up the path to import the ReasoningLLM class.
# This is based on a specific directory structure provided in the requirements.
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM

def blackbox(turn_number: int) -> str:
    """
    Implements the fixed strategy for the adversarial player in Load Shoot Defend Scout.
    The blackbox's strategy is to cycle through a predefined sequence of actions:
    'load', 'load', 'defend 2', 'load', 'defend 1'.

    Args:
        turn_number (int): The current turn number of the game, starting from 1.

    Returns:
        str: The action chosen by the blackbox for the current turn.
    """
    # The fixed sequence of actions for the blackbox player.
    strategy = ["load", "load", "defend 2", "load", "defend 1"]
    # Determine the action for the current turn using the modulo operator.
    action_index = (turn_number - 1) % len(strategy)
    return strategy[action_index]


def _parse_action(action_str: str):
    """
    A helper function to parse a player's action string into a type and a value.
    
    Args:
        action_str (str): The raw action string from the player.
        
    Returns:
        tuple[str, int] or tuple[None, None]: A tuple containing the action type 
                                              and its associated value. Returns (None, None)
                                              if the format is invalid.
    """
    # Sanitize and split the input string.
    parts = action_str.strip().lower().split()
    if not parts:
        return None, None
        
    action_type = parts[0]
    value = 0
    
    # For 'shoot' and 'defend', a numeric value is expected.
    if action_type in ["shoot", "defend"]:
        if len(parts) > 1 and parts[1].isdigit():
            value = int(parts[1])
        else:
            # The format is incorrect if a number is missing or invalid.
            return None, None
            
    return action_type, value

def platform(settings: dict, player: 'ReasoningLLM') -> int:
    """
    Implements the game platform (judger) for Load Shoot Defend Scout.
    It manages the game flow, interacts with the player and the blackbox,
    validates actions, and calculates scores.

    Args:
        settings (dict): A dictionary containing game settings, like 'total_turns'.
        player (ReasoningLLM): An instance of the player model to interact with.

    Returns:
        int: The final score of the player.
    """
    # Extract game settings.
    total_turns = settings.get('total_turns', 20)
    max_bullets = 8

    # Initialize game state variables.
    player_score = 0
    player_bullets = 0
    blackbox_bullets = 0
    
    # Variables to store the results of the last turn for reporting.
    last_player_action_full = "None"
    last_blackbox_action_full = "None"
    last_player_point = 0
    
    # The initial prompt explains the game rules to the player.
    initial_prompt = f"""Welcome to Load Shoot Defend Scout!
This is a game of strategy and resource management over {total_turns} turns.
Each turn, you can choose one of four actions:
- `load`: Gain one bullet.
- `scout`: See how many bullets the opponent has.
- `shoot x`: Spend `x` bullets to attack. `x` must be a positive integer.
- `defend y`: Spend `y` bullets to defend. `y` must be a positive integer.

Rules:
- You start with 0 bullets and can hold a maximum of {max_bullets}.
- `shoot x` vs `defend y`: If x > y, the shooter wins 1 point. If y > x, the defender wins 1 point. If x = y, no points.
- `shoot` vs `load` or `scout`: The shooter wins 1 point.
- `shoot x` vs `shoot z`: The player who shot with more bullets wins 1 point. If equal, no points.
- All other action combinations result in 0 points for both players.
- The values 'x' and 'y' are hidden from the opponent.

Let's begin.
"""
    
    # Main game loop runs for the total number of turns.
    for turn in range(1, total_turns + 1):
        # --- Player's Turn ---
        
        # Construct the prompt for the player based on the game state.
        if turn == 1:
            prompt = initial_prompt
        else:
            # For subsequent turns, provide a summary of the last turn.
            prompt = f"Last turn, you played '{last_player_action_full}' and the opponent played '{last_blackbox_action_full}'.\nYou gained {last_player_point} point(s).\n"

        prompt += f"\n--- Turn {turn}/{total_turns} ---\n"
        prompt += f"Your status: Score: {player_score}.\n"
        prompt += f"What is your action?"

        # Loop to get and validate the player's action.
        while True:
            player_action_str = player.normal_output(prompt)
            p_action, p_val = _parse_action(player_action_str)
            # Validate the parsed action.
            if p_action not in ["load", "scout", "shoot", "defend"]:
                prompt = f"Invalid action type in '{player_action_str}'. Your action must be one of 'load', 'scout', 'shoot', 'defend'. DO NOT Include other symbol\n"
            elif p_action == "load" and player_bullets >= max_bullets:
                prompt = f"Invalid action: '{player_action_str}'. You cannot load as you are at the maximum bullet capacity ({max_bullets}). DO NOT Include other text\n"
            elif p_action in ["shoot", "defend"]:
                if p_val is None:
                     prompt = f"Invalid format: '{player_action_str}'. Action 'shoot' or 'defend' must be followed by a number (e.g., 'shoot 2'). DO NOT Include other text\n"
                elif p_val <= 0:
                    prompt = f"Invalid action: '{player_action_str}'. The number of bullets for shooting or defending must be positive. DO NOT Include other text\n"
                elif p_val > player_bullets:
                    prompt = f"Invalid action: '{player_action_str}'. You only have {player_bullets} bullet(s). DO NOT Include other text\n"
                else:
                    break # Action is valid.
            else:
                break # 'load' or 'scout' action is valid.

            # If action is invalid, construct a new prompt with a warning.
            prompt += f"\n--- Turn {turn}/{total_turns} ---\n"
            prompt += f"Your status: Score: {player_score}, Bullets: {player_bullets}.\n"
            prompt += f"Please provide a valid action. (e.g., 'load', 'scout', 'shoot 2', 'defend 1')"

        # --- Blackbox's Turn ---
        blackbox_action_str = blackbox(turn)
        b_action, b_val = _parse_action(blackbox_action_str)

        # --- Judgement Phase ---
        player_point = 0
        
        # Store the opponent's bullet count at the start of the turn for scout reporting.
        blackbox_bullets_at_turn_start = blackbox_bullets

        # Resolve actions based on game rules to determine player's points.
        # Case 1: Player shoots
        if p_action == 'shoot':
            if b_action == 'shoot':
                # Player wins if they shoot with more bullets.
                if p_val > b_val:
                    player_point = 1
                elif p_val < b_val:
                    player_point = -1
            elif b_action == 'defend':
                # Player wins if their attack value is greater than the defense value.
                if p_val > b_val:
                    player_point = 1
                elif p_val <= b_val:
                    player_point = -1
            else:  # b_action is 'load' or 'scout'
                # Shooting always wins against loading or scouting.
                player_point = 1
                
        # Case 2: Player defends
        elif p_action == 'defend':
            if b_action == 'shoot':
                # Player wins if their defense value is greater than the attack value.
                if p_val >= b_val:
                    player_point = 1
                elif p_val < b_val:
                    player_point = -1
        
        # In all other cases (e.g., player loads, scouts, or actions result in a tie),
        # the player does not score a point, so player_point remains 0.

        # --- Update State ---
        
        # Update scores.
        player_score += player_point
        
        # Update bullet counts based on actions taken.
        if p_action == 'load': player_bullets += 1
        elif p_action == 'shoot': player_bullets -= p_val
        elif p_action == 'defend': player_bullets -= p_val
        
        if b_action == 'load': blackbox_bullets += 1
        elif b_action == 'shoot': blackbox_bullets -= b_val
        elif b_action == 'defend': blackbox_bullets -= b_val
            
        # Ensure bullet counts do not exceed the maximum.
        player_bullets = min(player_bullets, max_bullets)
        blackbox_bullets = min(blackbox_bullets, max_bullets)

        # Store action history for the next turn's prompt.
        last_player_action_full = player_action_str
        
        # Sanitize blackbox action for reporting to the player, hiding the value.
        if b_action in ["shoot", "defend"]:
            last_blackbox_action_full = b_action
        else:
            last_blackbox_action_full = blackbox_action_str
            
        last_player_point = player_point
        
        # If the player's scout was successful, add the result to the action summary.
        if p_action == 'scout' and b_action != 'shoot':
            last_player_action_full += f" (Scout successful: Opponent had {blackbox_bullets_at_turn_start} bullet(s))"

    return player_score

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    """
    The main function to set up and run the evaluation process.
    It instantiates the player model and calls its evaluation and saving methods.
    """
    # Instantiate the ReasoningLLM class with the provided arguments.
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    
    # The `evaluate` method is expected to handle the game execution loop.
    # It will likely call the `platform` function internally, passing itself
    # and the necessary settings.
    player.evaluate(failure_num, version, max_turns)
    
    # After evaluation, save the history of interactions to a file.
    player.save_history(output_dir, version)

if __name__ == "__main__":
    # This block executes when the script is run directly.
    # It parses command-line arguments and calls the main function.
    args = sys.argv[1:]
    
    if len(args) < 13:
        print("Usage: python your_script.py model_family model_name task eva_mode n_runs difficulty task_id failure_num output_dir max_turns version mode thinking_mode")
        sys.exit(1)
        
    # Call the main function, converting arguments to their expected types.
    main(
        model_family=args[0],
        model_name=args[1],
        task=args[2],
        eva_mode=args[3],
        n_runs=int(args[4]),
        difficulty=args[5],
        task_id=args[6],
        failure_num=int(args[7]),
        output_dir=args[8],
        max_turns=int(args[9]),
        version=int(args[10]),
        mode=args[11],
        thinking_mode=bool(eval(args[12]))
    )