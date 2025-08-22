import os
import sys
import math
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM
from scipy.integrate import solve_ivp
import numpy as np

def blackbox(t: float) -> dict:
    x = 0.0
    y = t * 4.0
    z = 0.0

    x_rounded = round(x, 2)
    y_rounded = round(y, 2)
    z_rounded = round(z, 2)

    object_coordinate = {"object1": (x_rounded, y_rounded, z_rounded)}
    return object_coordinate

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    """
    Main function to handle the interaction between the player (ReasoningLLM) and the blackbox.
    """
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)

    # Initial blackbox_output for the first turn
    blackbox_output_for_player = f'You have {max_turns} interaction turns to understand the black-box. Now the interaction starts. Only output the value and DO NOT contain any unrelated text.'

    for i in range(max_turns + 1):
        # Call player to get their output (which should be a time 't')
        player_output_str = player.normal_output(blackbox_output_for_player)

        # In the last iteration, just call normal_output and then exit
        if i == max_turns:
            continue # Exit the loop after the last interaction

        # Parse player_output_str to get 't'
        t_value = 0.0 # Default value if parsing fails
        try:
            t_value = float(player_output_str)
            # Ensure t is non-negative, as time cannot go backward
            if t_value < 0:
                t_value = 0.0
        except ValueError:
            # If player_output_str is not a valid float, use default t_value (0.0)
            # A more sophisticated error handling might send a specific error message back to the LLM
            pass # Silently use default 0.0 for invalid input

        # Call the blackbox with the parsed 't'
        blackbox_coordinate_dict = blackbox(t_value)

        # Format blackbox output for the next player turn
        blackbox_output_for_player = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> '
        blackbox_output_for_player += str(blackbox_coordinate_dict)

    # After the loop, evaluate and save history
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    # Ensure all arguments are provided and correctly typed
    if len(args) != 13:
        print("Usage: python your_script_name.py <model_family> <model_name> <task> <eva_mode> <n_runs> <difficulty> <task_id> <failure_num> <output_dir> <max_turns> <version> <mode> <thinking_mode>")
        sys.exit(1)

    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
