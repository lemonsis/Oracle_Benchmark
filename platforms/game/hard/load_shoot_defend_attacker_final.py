
import os
import sys
import re
# Annotations: Set up system paths to import the ReasoningLLM class.
# This is a standard procedure for modular Python projects where modules are located in different directories.
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM

# Annotations: Define the blackbox function which represents the adversarial player.
# This player follows a simple, predictable cyclic strategy.
def blackbox(turn_number: int) -> str:
    """
    Implements the fixed strategy for the adversarial player.
    The strategy cycles through a predefined sequence of actions.

    Args:
        turn_number (int): The current turn number (0-indexed).

    Returns:
        str: The action chosen by the blackbox player for the current turn.
    """
    # Annotations: The strategy is a cycle of 5 actions.
    # The modulo operator (%) is used to loop through the cycle.
    actions = ["load", "load", "shoot 2", "load", "shoot 1"]
    return actions[turn_number % len(actions)]

# Annotations: Define the platform function which acts as the game's judger.
# It manages the game flow, interacts with both players, validates actions,
# calculates scores, and maintains the game state.
def platform(settings: dict, player: 'ReasoningLLM') -> int:
    """
    Implements the game platform for Load Shoot Defend Scout.

    Args:
        settings (dict): A dictionary containing game settings, like 'total_turns'.
        player (ReasoningLLM): The player instance that will play against the blackbox.

    Returns:
        int: The final score of the player.
    """
    total_turns = settings.get('total_turns', 20)

    # Annotations: Initialize game state variables.
    player_bullets = 0
    blackbox_bullets = 0
    player_score = 0
    
    # Annotations: Information to be passed to the player at the start of each turn.
    last_turn_summary = "This is the first turn."
    scout_report = ""

    # Annotations: Helper function to parse action strings into a structured format.
    def parse_action(action_str: str) -> (str, int):
        """Parses a string action into a (type, value) tuple."""
        action_str = action_str.lower().strip()
        parts = action_str.split()
        try:
            action_type = parts[0]
        except IndexError:
            return "invalid", 0
        value = 0
        if action_type in ["shoot", "defend"] and len(parts) > 1:
            try:
                value = int(parts[1])
            except ValueError:
                # Invalid number format, will be caught by validation
                return "invalid", 0
        return action_type, value

    # Annotations: Main game loop that runs for the specified number of turns.
    for turn in range(total_turns):
        # Annotations: Get the blackbox's action for the current turn.
        blackbox_action_str = blackbox(turn)
        
        # Annotations: Construct the prompt for the player in natural language.
        # This prompt includes game rules, turn history, and current state.
        prompt_to_player = f"""
            Turn {turn + 1}/{total_turns}
            {last_turn_summary}
            You have {player_bullets} bullets.
            {scout_report}
            What is your action?
        """
        scout_report = "" # Reset scout report after displaying it once.

        # Annotations: Action validation loop for the player.
        # This ensures the player's action is valid before proceeding.
        while True:
            player_action_str = player.normal_output(prompt_to_player)
            action_type, value = parse_action(player_action_str)
            

            if action_type not in ["load", "scout", "shoot", "defend"]:
                prompt_to_player = f"Please **only** output load, scout, shoot x, or defend y. DO NOT contain any other symbol"
                continue
            
            if action_type in ["shoot", "defend"]:
                if value < 0:
                    prompt_to_player = f"Invalid action value. You cannot use a negative number of bullets. Your action was '{player_action_str}'. Please try again."
                    continue
                if value > player_bullets:
                    prompt_to_player = f"You don't have enough bullets. You tried to use {value} bullets but you only have {player_bullets}. Your action was '{player_action_str}'. Please try again."
                    continue
            
            # Annotations: If the action is valid, break the loop.
            break

        # Annotations: Parse actions for both players.
        player_action, player_value = parse_action(player_action_str)
        blackbox_action, blackbox_value = parse_action(blackbox_action_str)

        # Annotations: Store bullet counts before actions are resolved for the simultaneous shoot rule.
        pre_action_player_bullets = player_bullets
        pre_action_blackbox_bullets = blackbox_bullets

        # Annotations: Phase 1: Resolve 'load' actions.
        if player_action == "load":
            player_bullets = min(8, player_bullets + 1)
        if blackbox_action == "load":
            blackbox_bullets = min(8, blackbox_bullets + 1)

        # Annotations: Phase 2: Resolve 'scout' actions.
        if player_action == "scout":
            # The result is stored to be shown to the player in the next turn.
            scout_report = f"Your scout last turn revealed that the opponent had {blackbox_bullets} bullets before their action."

        # Annotations: Phase 3: Deduct bullets for 'shoot' and 'defend'.
        if player_action == "shoot" or player_action == "defend":
            player_bullets -= player_value
        if blackbox_action == "shoot" or blackbox_action == "defend":
            blackbox_bullets -= blackbox_value

        # Annotations: Phase 4: Determine the outcome and update scores.
        player_score_change = 0
        if player_action == "shoot" and blackbox_action == "defend":
            if player_value > blackbox_value:
                player_score_change = 1
            elif player_value <= blackbox_value:
                player_score_change = -1
        elif player_action == "defend" and blackbox_action == "shoot":
            if player_value >= blackbox_value:
                player_score_change = 1
            elif player_value < blackbox_value:
                player_score_change = -1
        elif player_action == "shoot" and blackbox_action in ["load", "scout"]:
            player_score_change = 1
        elif player_action == "shoot" and blackbox_action == "shoot":
            if player_value > blackbox_value:
                player_score_change = 1
            elif player_value < blackbox_value:
                player_score_change = -1
        elif player_action in ['load', 'scout'] and blackbox_action == "shoot":
            player_score_change = -1
        
        player_score += player_score_change

        # Annotations: Prepare the summary for the next turn.
        # Hide the opponent's specific shoot/defend values as per the rules.
        public_blackbox_action = blackbox_action
        if blackbox_action in ["shoot", "defend"]:
            public_blackbox_action = blackbox_action
        else:
            public_blackbox_action = blackbox_action_str

        last_turn_summary = (f"In the last turn, you chose '{player_action_str}' and the opponent chose '{public_blackbox_action}'. "
                             f"You gained {player_score_change} point(s).")

    return player_score

# Annotations: The main function to set up and run the evaluation.
def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    """
    Main function to instantiate the player and run the game evaluation.
    """
    # Annotations: Instantiate the ReasoningLLM class which represents the player.
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    
    # Annotations: Call the evaluate method, which will internally call the platform function.
    player.evaluate(failure_num, version, max_turns)
    
    # Annotations: Save the history of the interaction to a file.
    player.save_history(output_dir, version)

# Annotations: Standard Python entry point.
# This block parses command-line arguments and calls the main function.
if __name__ == "__main__":
    args = sys.argv[1:]
    # Annotations: Ensure correct data types are passed to the main function.
    main(
        args[0],                          # model_family
        args[1],                          # model_name
        args[2],                          # task
        args[3],                          # eva_mode
        int(args[4]),                     # n_runs
        args[5],                          # difficulty
        args[6],                          # task_id
        int(args[7]),                     # failure_num
        args[8],                          # output_dir
        int(args[9]),                     # max_turns
        int(args[10]),                    # version
        args[11],                         # mode
        bool(eval(args[12])) # thinking_mode
    )
