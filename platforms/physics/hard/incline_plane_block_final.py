
import os
import sys
import math
import numpy as np
from scipy.integrate import solve_ivp

# Ensure the path to eva_models is correct
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)

from eva_models import ReasoningLLM

def blackbox(t: float) -> dict:
    """
    Implements the physics simulation of a block sliding off an inclined plane.

    The system consists of a block (object1) and an inclined plane (object2).
    Phase 1: The block slides down the incline. Both the block and the plane accelerate.
    Phase 2: The block has left the incline and both objects move at constant velocities on the horizontal surface.

    Args:
        t (float): The time at which to calculate the objects' coordinates.

    Returns:
        dict: A dictionary containing the 3D coordinates of the block and the plane.
              Format: {"object1": (x, y, z), "object2": (x, y, z)}
    """
    # --- Constants based on the problem description ---
    m = 5.0   # mass of the block (kg)
    M = 10.0  # mass of the inclined plane (kg)
    g = 10.0  # acceleration due to gravity (m/s^2)
    h = 8.0   # initial perpendicular height of the block (m)
    theta = np.deg2rad(30) # angle of the incline (radians)

    # --- Pre-calculation of key physical quantities ---

    # Acceleration of the block along the incline (relative to the plane)
    # Derived from conservation of energy and momentum.
    # a_s = (g * sin(theta) * (m + M)) / (M + m * sin(theta)^2)
    a_s = (g * np.sin(theta) * (m + M)) / (M + m * np.sin(theta)**2)

    # Maximum distance the block travels along the incline before separating
    s_max = h / np.sin(theta)

    # Time of separation (when the block reaches the bottom of the incline)
    # s = 0.5 * a_s * t^2  => t = sqrt(2 * s / a_s)
    t_sep = np.sqrt(2 * s_max / a_s)

    # --- Determine the phase of motion based on time t ---

    if t <= t_sep:
        # --- Phase 1: Block is on the inclined plane (0 <= t <= t_sep) ---

        # Distance slid along the incline at time t
        s_t = 0.5 * a_s * t**2

        # Horizontal acceleration of the plane (derived from momentum conservation)
        a_px = - (m * np.cos(theta) / (m + M)) * a_s
        
        # Velocity of the block in the x-direction
        # v_bx = (M / (m + M)) * cos(theta) * v_s(t), where v_s(t) = a_s * t
        # Integrating v_bx gives x_b(t) = 0.5 * a_bx * t^2
        a_bx = (M / (m + M)) * np.cos(theta) * a_s

        # Position of the plane (object2) at time t
        # Starts at x=0, moves in the negative x direction.
        x_p = 0.5 * a_px * t**2
        y_p = 0.0
        z_p = 0.0

        # Position of the block (object1) at time t
        # Starts at x=0, z=h.
        x_b = 0.5 * a_bx * t**2
        y_b = 0.0
        z_b = h - s_t * np.sin(theta)

    else:
        # --- Phase 2: Block has separated and is on the horizontal surface (t > t_sep) ---

        # Calculate positions and velocities at the moment of separation (t = t_sep)
        
        # --- Plane (object2) at separation ---
        a_px_sep = - (m * np.cos(theta) / (m + M)) * a_s
        x_p_sep = 0.5 * a_px_sep * t_sep**2
        v_px_sep = a_px_sep * t_sep

        # --- Block (object1) at separation ---
        a_bx_sep = (M / (m + M)) * np.cos(theta) * a_s
        x_b_sep = 0.5 * a_bx_sep * t_sep**2
        v_bx_sep = a_bx_sep * t_sep
        # Vertical position z_b becomes 0.

        # Time elapsed since separation
        dt = t - t_sep

        # Position of the plane (object2) at time t (constant velocity motion)
        x_p = x_p_sep + v_px_sep * dt
        y_p = 0.0
        z_p = 0.0

        # Position of the block (object1) at time t (constant velocity motion)
        x_b = x_b_sep + v_bx_sep * dt
        y_b = 0.0
        z_b = 0.0

    # Format the output dictionary with coordinates rounded to two decimal places
    # and ensure consistent float data type.
    object_coordinate = {
        "object1": (float(round(x_b, 2)), float(round(y_b, 2)), float(round(z_b, 2))),
        "object2": (float(round(x_p, 2)), float(round(y_p, 2)), float(round(z_p, 2))),
    }
    return object_coordinate


def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    """
    Main function to run the player-blackbox interaction.
    """
    # Instantiate the player model
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)

    # Initial prompt for the player
    blackbox_output = f'You have {max_turns} interaction turns to understand the black-box. Now the interaction starts. Only output the value and DO NOT contain any unrelated text.'

    # Interaction loop
    for i in range(max_turns + 1):
        # Get the player's output (either a query for the blackbox or the final answer)
        player_output = player.normal_output(blackbox_output)

        # The last iteration is for the final answer, so we don't call the blackbox
        if i == max_turns:
            continue

        # Prepare the input for the next turn
        try:
            # Attempt to convert player's output to a float for the blackbox
            time_query = float(player_output)
            result = blackbox(time_query)
        except (ValueError, TypeError):
            # Handle cases where the player's output is not a valid number
            result = "Error: Input must be a single floating-point number representing time t."

        # Format the blackbox output for the next turn, including turn counters
        blackbox_output = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> {result}'

    # After the loop, evaluate the player's final answer
    player.evaluate(failure_num, version)
    # Save the interaction history
    player.save_history(output_dir, version)


if __name__ == "__main__":
    # Parse command-line arguments
    args = sys.argv[1:]
    # Call the main function with the provided arguments
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
