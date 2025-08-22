
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
    """
    Simulates a simple harmonic oscillator and returns the 3D coordinate of the object.

    A simple harmonic oscillator with mass m=1kg, spring constant k=100 N/m,
    initial displacement x0=0.2m (contracted), and released from rest (v0=0).
    The system is horizontal, frictionless, and without air resistance.
    The coordinate origin is at the equilibrium position.

    The analytical solution for displacement x(t) is A * cos(omega*t + phi).
    Given x(0) = 0.2 and v(0) = 0:
    Angular frequency: omega = sqrt(k/m) = sqrt(100/1) = 10 rad/s.
    From v(0) = -A * omega * sin(phi) = 0, we get phi = 0 (since A and omega are non-zero).
    From x(0) = A * cos(phi) = 0.2, with phi=0, we get A = 0.2.
    So, x(t) = 0.2 * cos(10*t).
    y(t) and z(t) remain 0 as the motion is 1-dimensional along the x-axis.

    Parameters:
    t (float): Time in seconds.

    Returns:
    dict: A dictionary containing the 3D coordinate of 'object1',
          formatted as {"object1": (x, y, z)}.
          Coordinates are approximated to two decimal places.
    """
    m = 1.0  # mass in kg
    k = 100.0  # spring constant in N/m
    x0 = 0.2  # initial displacement in m (amplitude)

    # Calculate angular frequency
    omega = math.sqrt(k / m) # 10 rad/s

    # Calculate x(t) using the analytical solution
    x_t = x0 * math.cos(omega * t)

    # y and z coordinates remain at equilibrium (0) for this 1D horizontal system
    y_t = 0.0
    z_t = 0.0

    # Approximate coordinates to two decimal places
    x_t_rounded = round(x_t, 2)
    y_t_rounded = round(y_t, 2)
    z_t_rounded = round(z_t, 2)

    object_coordinate = {"object1": (x_t_rounded, y_t_rounded, z_t_rounded)}
    return object_coordinate

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    """
    Main function to orchestrate the interaction between the player (ReasoningLLM) and the blackbox.

    Parameters:
    model_family (str): Family of the LLM model.
    model_name (str): Name of the specific LLM model.
    task (str): The task description for the LLM.
    eva_mode (str): Evaluation mode.
    n_runs (int): Number of runs.
    difficulty (str): Difficulty level of the task.
    task_id (str): Identifier for the task.
    failure_num (int): Number of failures.
    output_dir (str): Directory to save outputs.
    max_turns (int): Maximum number of interaction turns.
    version (int): Version of the interaction.
    mode (str): Mode of operation.
    thinking_mode (bool): Whether thinking mode is enabled.
    """
    # Instantiate the player model
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)

    # Initial message for the player
    blackbox_output = f'You have {max_turns} interaction turns to understand the black-box. Now the interaction starts. Only output the value and DO NOT contain any unrelated text.'

    # Interaction loop
    for i in range(max_turns + 1):
        # Player generates an input for the blackbox
        player_output = player.normal_output(blackbox_output)

        # On the last turn, the player provides the final answer, so we don't query the blackbox
        if i == max_turns:
            continue

        # Try to process player's input and query the blackbox
        try:
            # Convert player's output to a float for the time query
            time_query = float(player_output)
            # Get the blackbox output for the given time
            blackbox_output = blackbox(time_query)
        except (ValueError, TypeError):
            # Handle cases where the player's output is not a valid number
            blackbox_output = "Invalid input. Please provide a single number for the time 't'."

        # Format the blackbox output with turn information for the next iteration
        remaining_turns = max_turns - (i + 1)
        blackbox_output = f'<Current Turn: {i+1}, {remaining_turns} Turns Remaining> {blackbox_output}'

    # Evaluate the player's final answer
    player.evaluate(failure_num, version)
    # Save the interaction history
    player.save_history(output_dir, version)
    
if __name__ == "__main__":
    # Command-line arguments parsing
    args = sys.argv[1:]
    
    # Ensure the correct number of arguments are provided
    if len(args) != 13:
        print("Usage: python your_script_name.py <model_family> <model_name> <task> <eva_mode> <n_runs> <difficulty> <task_id> <failure_num> <output_dir> <max_turns> <version> <mode> <thinking_mode>")
        sys.exit(1)

    # Unpack arguments and cast to appropriate types
    model_family = args[0]
    model_name = args[1]
    task = args[2]
    eva_mode = args[3]
    n_runs = int(args[4])
    difficulty = args[5]
    task_id = args[6]
    failure_num = int(args[7])
    output_dir = args[8]
    max_turns = int(args[9])
    version = int(args[10])
    mode = args[11]
    thinking_mode = bool(eval(args[12])) # Using eval as specified, assumes safe input (True/False)

    # Call the main function with parsed arguments
    main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode)
