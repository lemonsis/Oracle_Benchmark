
import os
import sys
import math
import numpy as np
from scipy.integrate import solve_ivp

# Set up path for custom modules
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)

from eva_models import ReasoningLLM

# Constants for the pendulum simulation
G = 10.0  # Acceleration due to gravity (m/s^2)
L = 2.0   # Length of the pendulum (m)
THETA0_DEG = 60.0  # Initial angle in degrees
THETA0_RAD = np.deg2rad(THETA0_DEG)  # Initial angle in radians
OMEGA0 = 0.0  # Initial angular velocity (rad/s), released from rest

def pendulum_ode(t, y):
    """
    Defines the system of first-order differential equations for a simple pendulum.
    y[0] = theta (angle)
    y[1] = omega (angular velocity)
    """
    theta, omega = y
    dtheta_dt = omega
    domega_dt = -(G / L) * np.sin(theta)
    return [dtheta_dt, domega_dt]

def blackbox(t: float) -> dict:
    """
    Simulates a simple pendulum system.

    The pendulum has a length of 2m and is released from rest at an angle of 60 degrees.
    The pivot point is at the origin (0, 0, 0). The motion is in the x-y plane.

    Args:
        t (float): The time in seconds at which to calculate the pendulum's position.

    Returns:
        dict: A dictionary containing the 3D coordinates of the pendulum bob,
              formatted as {"object1": (x, y, z)}. Coordinates are rounded to two decimal places.
              Returns an error message in the dictionary if the input is invalid.
    """
    # Input validation
    if not isinstance(t, (int, float)) or t < 0:
        return {"error": "Invalid input. Time 't' must be a non-negative number."}
    if t == 0:
        return {
        "object1": (round(1.732, 2), round(-1, 2), round(0.0, 2))
    }
    # Initial conditions: [theta_0, omega_0]
    y0 = [THETA0_RAD, OMEGA0]

    # Time span for the solver
    t_span = [0, t]

    # Use solve_ivp to find the numerical solution for theta(t)
    # t_eval=[t] ensures we only get the solution at the specified time t
    sol = solve_ivp(pendulum_ode, t_span, y0, t_eval=[t], method='RK45')

    # Extract the angle theta at time t
    # sol.y is a 2D array, [theta_values, omega_values]. We need the last (and only) theta value.
    theta_t = sol.y[0, -1]

    # Convert polar coordinates (L, theta) to Cartesian coordinates (x, y)
    # The pivot is at (0,0). The pendulum hangs downwards in the -y direction.
    # theta is measured from the vertical downward axis.
    # To match the standard math angle definition (from +x axis), we adjust.
    # Let's define theta from the negative y-axis.
    # x = L * sin(theta)
    # y = -L * cos(theta)
    x = L * np.sin(theta_t)
    y = -L * np.cos(theta_t)
    z = 0.0  # Motion is restricted to the x-y plane

    # Format the output
    
    object_coordinate = {
        "object1": (round(x, 2), round(y, 2), round(z, 2))
    }

    return object_coordinate

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    """
    Main function to run the player-blackbox interaction.
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
    # Parse command-line arguments
    args = sys.argv[1:]
    
    # Check if the correct number of arguments is provided
    if len(args) != 13:
        print("Usage: python script.py <model_family> <model_name> <task> <eva_mode> <n_runs> <difficulty> <task_id> <failure_num> <output_dir> <max_turns> <version> <mode> <thinking_mode>")
        sys.exit(1)

    # Call the main function with parsed arguments, converting types as necessary
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
