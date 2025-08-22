
import os
import sys
import math

# Add the parent directory of the project to the Python path
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)

from eva_models import ReasoningLLM
from scipy.integrate import solve_ivp
import numpy as np

# --- Blackbox Function ---

# Define constants for the physical model based on the problem description
# Mass of the ball (m) = 2 kg
# Initial upward velocity (v0) = 15 m/s
# Air resistance force (f) = 0.1 * v^2
# Acceleration due to gravity (g) = 10 m/s^2
M = 2.0
G = 10.0
K = 0.1
V0 = 15.0
Y0 = 0.0

# A cache to store results of previous computations to avoid re-calculating for the same time `t`.
solution_cache = {}

def _ode_system(t, S):
    """
    Defines the system of ordinary differential equations for the ball's motion.
    This function is intended for use with `solve_ivp`.

    Args:
        t (float): Current time (not used in this specific autonomous system, but required by solve_ivp).
        S (list or np.array): State vector [y, v], where y is position and v is velocity.

    Returns:
        list: The derivatives [dy/dt, dv/dt].
    """
    _y, v = S
    
    # Equation for velocity: dy/dt = v
    dydt = v
    
    # Equation for acceleration: dv/dt = F_net / m
    # The net force F_net is the sum of gravity and air resistance.
    # Gravity force is -m*g (always downward).
    # Air resistance is -sign(v)*k*v^2 (always opposing velocity).
    dvdt = -G - (K / M) * np.sign(v) * v**2
    
    return [dydt, dvdt]

def blackbox(t: float) -> dict:
    """
    Implements the blackbox function for the ball_air_resistance problem.
    It calculates the 3D coordinates of a ball at a given time `t`. The ball is thrown
    vertically upward with air resistance. The motion is simulated along the y-axis.

    Args:
        t (float): The time in seconds.

    Returns:
        dict: A dictionary containing the 3D coordinates of the ball, formatted as
              {"object1": (x, y, z)}. Returns initial state for t < 0.
    """
    # Handle non-physical negative time by returning the initial state.
    if t == 0:
        return {"object1": (0.00, 0.00, 0.00)}

    # Return cached result if available
    if t in solution_cache:
        return solution_cache[t]

    # Initial state vector: [initial_position, initial_velocity]
    S0 = [Y0, V0]

    # If t=0, the position is the initial position.
    if t == 0:
        result = {"object1": (0.00, round(Y0, 2), 0.00)}
        solution_cache[t] = result
        return result

    # Define the time span for the solver.
    t_span = [0, t]
    
    # Use `solve_ivp` to get a numerical solution to the ODE system.
    # We request the solution only at the specific time `t`.
    sol = solve_ivp(_ode_system, t_span, S0, t_eval=[t], dense_output=True, method='RK45')

    # The solution `sol.y` contains position and velocity. We need the position at time `t`.
    # `sol.y[0]` is the array of positions, `sol.y[0, -1]` is the last (and only) position value.
    y_t = sol.y[0, -1]

    # The motion is purely vertical (y-axis), so x and z coordinates are always 0.
    x_t = 0.0
    z_t = 0.0

    # Format the final coordinates, rounded to two decimal places.
    object_coordinate = {
        "object1": (round(x_t, 2), round(y_t, 2), round(z_t, 2))
    }
    
    # Cache the result before returning.
    solution_cache[t] = object_coordinate
    
    return object_coordinate


# --- Main Interaction Function ---

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    """
    The main function to orchestrate the interaction between the player (LLM) and the blackbox.
    """
    # Instantiate the player model from the evaluation framework.
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)

    # Set the initial prompt for the player.
    blackbox_output = f'You have {max_turns} interaction turns to understand the black-box. Now the interaction starts. Only output the value and DO NOT contain any unrelated text.'

    # Loop for the specified number of interaction turns.
    for i in range(max_turns + 1):
        # Get the player's next action/query based on the current state.
        player_output = player.normal_output(blackbox_output)

        # In the last turn, the player provides their final answer. We don't need to query the blackbox anymore.
        if i == max_turns:
            continue

        # Try to process the player's query and call the blackbox.
        try:
            # The player is expected to provide a time `t` as a number.
            t_input = float(player_output)
            # Call the blackbox to get the object's coordinates at time `t`.
            result_dict = blackbox(t_input)
            # Convert the result to a string for the next prompt.
            next_blackbox_input = str(result_dict)
        except (ValueError, TypeError):
            # If the player's output is not a valid number, provide an error message.
            next_blackbox_input = "Error: Invalid input. Please provide a single number for the time t."

        # Format the prompt for the next turn, including turn information.
        blackbox_output = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> {next_blackbox_input}'

    # After the interaction loop, evaluate the player's final answer.
    player.evaluate(failure_num, version)
    # Save the entire interaction history to a file.
    player.save_history(output_dir, version)


# --- Script Entry Point ---

if __name__ == "__main__":
    # Parse command-line arguments.
    args = sys.argv[1:]
    
    # Call the main function with the parsed arguments, ensuring correct data types.
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
