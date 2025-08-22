
import os
import sys
import math
# The following lines are for setting up the path to import custom modules.
# current_path is the absolute path of the current script.
current_path = os.path.abspath(__file__)
# oracle_path is the path to the directory containing the 'eva_models' module.
# It's assumed to be four levels up from the current script's directory.
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
# Add oracle_path to sys.path if it's not already there, to allow importing modules from it.
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)

# Import necessary modules and classes.
# ReasoningLLM is a custom class for the player model.
from eva_models import ReasoningLLM
# solve_ivp is for solving ordinary differential equations, though not used in this implementation.
from scipy.integrate import solve_ivp
# numpy is used for numerical operations.
import numpy as np

def blackbox(t: float) -> dict:
    """
    Simulates the 1D collision of two balls on a plane and returns their positions at a given time t.

    The simulation is event-driven, calculating the time to the next collision (either ball-ball or ball-wall)
    and updating the system state step-by-step until the target time t is reached.

    Args:
        t (float): The time at which to determine the positions of the balls. Must be non-negative.

    Returns:
        dict: A dictionary containing the 3D coordinates of the two balls, formatted as
              {"object1": (x1, y1, z1), "object2": (x2, y2, z2)}.
              The coordinates are rounded to two decimal places.
    """
    # --- Initial Conditions and Constants ---
    # Mass of ball A (object1) and ball B (object2)
    m_a, m_b = 5.0, 3.0
    # Initial positions
    x_a, x_b = 0.0, 20.0
    # Initial velocities
    v_a, v_b = 4.0, -6.0
    # Length of the plane
    L = 20.0
    # Coefficient of restitution for ball-ball collision
    e = 0.8
    # A small tolerance to handle floating point inaccuracies
    epsilon = 1e-9

    # Handle invalid time input
    if t < 0:
        t = 0.0

    current_time = 0.0

    # --- Event-Driven Simulation Loop ---
    while current_time < t:
        # Calculate time remaining in the simulation
        time_to_simulate = t - current_time
        
        # --- Calculate Time to Next Event ---
        times_to_event = []

        # Time to ball-ball collision
        if v_a > v_b:
            t_coll = (x_b - x_a) / (v_a - v_b)
            if t_coll > epsilon:
                times_to_event.append(t_coll)

        # Time for ball A to hit a wall
        if v_a > 0:
            t_wall_a = (L - x_a) / v_a
            if t_wall_a > epsilon:
                times_to_event.append(t_wall_a)
        elif v_a < 0:
            t_wall_a = -x_a / v_a
            if t_wall_a > epsilon:
                times_to_event.append(t_wall_a)

        # Time for ball B to hit a wall
        if v_b > 0:
            t_wall_b = (L - x_b) / v_b
            if t_wall_b > epsilon:
                times_to_event.append(t_wall_b)
        elif v_b < 0:
            t_wall_b = -x_b / v_b
            if t_wall_b > epsilon:
                times_to_event.append(t_wall_b)

        # --- Determine Next Step ---
        if not times_to_event:
            # No future events, advance to the end time
            dt = time_to_simulate
        else:
            # Find the earliest event time
            min_t_event = min(times_to_event)
            # Step forward by the smaller of the two: time to next event or remaining simulation time
            dt = min(min_t_event, time_to_simulate)

        # Advance positions
        x_a += v_a * dt
        x_b += v_b * dt
        current_time += dt

        # If the simulation time is reached, exit the loop
        if current_time >= t:
            break

        # --- Handle Event (Update Velocities) ---
        # Check if a ball-ball collision occurred (within tolerance)
        if abs(x_a - x_b) < epsilon:
            # Velocities after inelastic collision
            v_a_new = (v_a * (m_a - e * m_b) + v_b * m_b * (1 + e)) / (m_a + m_b)
            v_b_new = (v_a * m_a * (1 + e) + v_b * (m_b - e * m_a)) / (m_a + m_b)
            v_a, v_b = v_a_new, v_b_new
        # Check if ball A hit a wall
        elif abs(x_a - L) < epsilon or abs(x_a) < epsilon:
            v_a = -v_a  # Elastic collision with wall
        # Check if ball B hit a wall
        elif abs(x_b - L) < epsilon or abs(x_b) < epsilon:
            v_b = -v_b  # Elastic collision with wall

    # Format the output dictionary with 3D coordinates (y and z are 0)
    object_coordinate = {
        "object1": (round(x_a, 2), 0.00, 0.00),
        "object2": (round(x_b, 2), 0.00, 0.00)
    }
    return object_coordinate

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    """
    Main function to run the player-blackbox interaction loop.

    It initializes the player model, manages the interaction turns, calls the blackbox function,
    and finally evaluates and saves the results.
    """
    # Instantiate the player model
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)

    # Initial prompt for the player
    current_prompt = f'You have {max_turns} interaction turns to understand the black-box. Now the interaction starts. Only output the value and DO NOT contain any unrelated text.'

    # Interaction loop runs for max_turns queries + 1 final answer
    for i in range(max_turns + 1):
        # Get the player's output (a time 't' or a final answer)
        player_output = player.normal_output(current_prompt)

        # The last iteration is for the player's final answer, not for querying the blackbox.
        if i == max_turns:
            continue

        # Process the player's query
        try:
            # Attempt to convert the player's output to a float
            t = float(player_output)
            # Call the blackbox with the provided time
            blackbox_result = blackbox(t)
        except (ValueError, TypeError):
            # Handle cases where the output is not a valid number
            blackbox_result = "Invalid input. Please provide a single floating-point number for the time t."

        # Prepare the prompt for the next turn, including turn count and blackbox result
        current_prompt = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> {str(blackbox_result)}'

    # After the loop, evaluate the player's performance
    player.evaluate(failure_num, version)
    # Save the interaction history
    player.save_history(output_dir, version)

if __name__ == "__main__":
    # This block allows the script to be run from the command line.
    # It parses command-line arguments and passes them to the main function.
    args = sys.argv[1:]
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
