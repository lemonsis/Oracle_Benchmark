
import os
import sys
import math

# Add the oracle path to the system path
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)

# Import necessary modules
from eva_models import ReasoningLLM
from scipy.integrate import solve_ivp
import numpy as np

def blackbox(t_str: str) -> dict:
    """
    Simulates the motion of a boat in a river with a parabolic current profile.
    The boat travels towards the opposite bank, has a malfunction, and returns.

    The motion is divided into three phases based on time `t`:
    1.  Outward journey (0 <= t <= 2.5s): The boat moves from y=0 to y=5.
    2.  Return journey (2.5s < t <= 7.5s): The boat moves from y=5 back to y=0.
    3.  Stationary (t > 7.5s): The boat is at the bank (y=0) where the current is zero, so it stops.

    Args:
        t_str (str): A string representing the time 't' in seconds.

    Returns:
        str: A string representation of a dictionary containing the boat's
             3D coordinates `(x, y, z)` rounded to two decimal places.
             Returns an error message if the input is invalid.
    """
    # Validate the input from the player
    try:
        t = float(t_str)
    except (ValueError, TypeError):
        return "Error: Input must be a single floating-point number representing time 't'."

    # River velocity profile: v_x(y) = 0.1 * y * (20 - y)
    # Boat's velocity relative to water in y-direction: v_y

    # Phase 1: Outward journey (0 <= t <= 2.5s)
    # v_y = 2 m/s. y(t) = 2t.
    # dx/dt = 0.1 * (2t) * (20 - 2t) = 4t - 0.4t^2
    # x(t) = integral(4t - 0.4t^2) dt = 2t^2 - (0.4/3)t^3
    if 0 <= t <= 2.5:
        x = t**2 
        y = 2 * t
        z = 0.0
    # Phase 2: Return journey (2.5s < t <= 7.5s)
    # v_y = -1 m/s. y(t) = 5 - 1*(t - 2.5) = 7.5 - t
    # dx/dt = 0.1 * (7.5-t) * (20 - (7.5-t)) = 0.1 * (7.5-t) * (12.5+t)
    # dx/dt = 9.375 - 0.5t - 0.1t^2
    # x(t) = x(2.5) + integral[2.5, t](9.375 - 0.5τ - 0.1τ^2) dτ
    # x(t) = 10.4167 + [9.375τ - 0.25τ^2 - (0.1/3)τ^3] from 2.5 to t
    # After solving the definite integral and simplifying:
    # x(t) = 9.375*t - 0.25*t^2 - (0.1/3)*t^3 - 10.9375
    elif 2.5 < t <= 7.5:
        x = -0.5 * t**2 + 7.5*t -9.375
        y = 7.5 - t
        z = 0.0
    # Phase 3: Stationary (t > 7.5s)
    # The boat reaches y=0 at t=7.5s. At y=0, river velocity is 0.
    # Final position at t=7.5s: x(7.5) = 31.25, y(7.5) = 0
    elif t > 7.5:
        x = 18.75
        y = 0.0
        z = 0.0
    # Handle negative time (initial position)
    else: # t < 0
        x = 0.0
        y = 0.0
        z = 0.0

    # Format the output dictionary
    object_coordinate = {
        "object1": (round(x, 2), round(y, 2), round(z, 2))
    }

    return object_coordinate

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    """
    Main function to run the player-blackbox interaction loop.

    Args:
        model_family (str): The family of the language model.
        model_name (str): The specific name of the language model.
        task (str): The task identifier.
        eva_mode (str): The evaluation mode.
        n_runs (int): The number of runs.
        difficulty (str): The difficulty level of the task.
        task_id (str): The specific ID of the task.
        failure_num (int): Number of failures.
        output_dir (str): Directory to save the output.
        max_turns (int): Maximum number of interaction turns.
        version (int): The version of the evaluation.
        mode (str): The interaction mode.
        thinking_mode (bool): Flag for enabling thinking mode.
    """
    # Instantiate the player model
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)

    # Set the initial prompt for the player
    blackbox_output = f'You have {max_turns} interaction turns to understand the black-box. Now the interaction starts. Only output the value and DO NOT contain any unrelated text.'

    # Interaction loop
    for i in range(max_turns + 1):
        # Player generates an output based on the blackbox's last message
        player_output = player.normal_output(blackbox_output)

        # On the last turn, the player provides the final answer, and we exit the loop
        if i == max_turns:
            continue

        # Get the result from the blackbox based on the player's input
        blackbox_result_str = blackbox(player_output)

        # Prepare the blackbox output for the next turn, including turn information
        blackbox_output = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> {blackbox_result_str}'

    # Evaluate the player's performance and save the history
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    # Parse command-line arguments
    args = sys.argv[1:]
    # Call the main function with the provided arguments, ensuring correct types
    main(
        args[0],                      # model_family
        args[1],                      # model_name
        args[2],                      # task
        args[3],                      # eva_mode
        int(args[4]),                 # n_runs
        args[5],                      # difficulty
        args[6],                      # task_id
        int(args[7]),                 # failure_num
        args[8],                      # output_dir
        int(args[9]),                 # max_turns
        int(args[10]),                # version
        args[11],                     # mode
        bool(eval(args[12]))          # thinking_mode
    )
