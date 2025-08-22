
import os
import sys
import math
from scipy.integrate import solve_ivp
import numpy as np

# Set up path to import custom modules
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM

# Define physical constants for the simulation
# Masses of the three balls (A, B, C) in kg
MASSES = np.array([4.0, 3.0, 2.0])
# Initial positions in meters
INITIAL_POS = np.array([0.0, 10.0, 20.0])
# Initial velocities in m/s
INITIAL_VEL = np.array([3.0, 3.0, -4.0])
# Boundaries of the plane
WALL_L = 0.0
WALL_R = 30.0

def blackbox(t_target: float) -> dict:
    """
    Simulates the 1D elastic collision of three balls on a plane with walls.

    The simulation uses `scipy.integrate.solve_ivp` to solve the ordinary
    differential equations of motion. Events are defined to handle collisions
    between balls and between balls and walls. The simulation proceeds in steps,
    from one collision event to the next, until the target time is reached.

    Args:
        t_target (float): The time `t` for which to calculate the positions.

    Returns:
        dict: A dictionary containing the 3D coordinates of the three objects
              at time `t`, with coordinates rounded to two decimal places.
              e.g., {"object1": (x, y, z), "object2": (x, y, z), ...}
    """
    # Input validation
    if not isinstance(t_target, (int, float)) or t_target < 0:
        # This case is handled in the main loop, but serves as a safeguard.
        raise ValueError("Time must be a non-negative number.")

    # Handle the t=0 edge case directly
    if t_target == 0:
        return {
            "object1": (round(INITIAL_POS[0], 2), 0.00, 0.00),
            "object2": (round(INITIAL_POS[1], 2), 0.00, 0.00),
            "object3": (round(INITIAL_POS[2], 2), 0.00, 0.00),
        }

    # Initial state vector: [x_A, x_B, x_C, v_A, v_B, v_C]
    y0 = np.concatenate([INITIAL_POS, INITIAL_VEL])
    t_current = 0.0
    y = y0.copy()

    # Define the system's dynamics (ODE). Between collisions, acceleration is zero.
    def system_dynamics(t, y):
        # y = [x0, x1, x2, v0, v1, v2]
        # returns dy/dt = [v0, v1, v2, 0, 0, 0]
        return np.array([y[3], y[4], y[5], 0, 0, 0])

    # --- Event Functions for Collision Detection ---
    # An event function's root (when it equals zero) triggers an event.
    # `terminal=True` stops the solver at the event.
    # `direction` specifies whether to trigger on increasing or decreasing zero-crossings.

    # Ball-ball collisions (e.g., x0 - x1 = 0)
    def collision_01(t, y): return y[0] - y[1]
    collision_01.terminal = True
    collision_01.direction = -1  # Trigger when approaching (distance decreasing)

    def collision_12(t, y): return y[1] - y[2]
    collision_12.terminal = True
    collision_12.direction = -1

    def collision_02(t, y): return y[0] - y[2]
    collision_02.terminal = True
    collision_02.direction = -1

    # Ball-wall collisions (e.g., x0 - WALL_L = 0)
    def wall_0_left(t, y): return y[0] - WALL_L
    wall_0_left.terminal = True
    wall_0_left.direction = -1

    def wall_0_right(t, y): return y[0] - WALL_R
    wall_0_right.terminal = True
    wall_0_right.direction = 1

    def wall_1_left(t, y): return y[1] - WALL_L
    wall_1_left.terminal = True
    wall_1_left.direction = -1

    def wall_1_right(t, y): return y[1] - WALL_R
    wall_1_right.terminal = True
    wall_1_right.direction = 1

    def wall_2_left(t, y): return y[2] - WALL_L
    wall_2_left.terminal = True
    wall_2_left.direction = -1

    def wall_2_right(t, y): return y[2] - WALL_R
    wall_2_right.terminal = True
    wall_2_right.direction = 1

    events = [collision_01, collision_12, collision_02,
              wall_0_left, wall_0_right, wall_1_left,
              wall_1_right, wall_2_left, wall_2_right]

    # Main simulation loop: integrate from one event to the next
    while t_current < t_target:
        t_span = [t_current, t_target]
        sol = solve_ivp(system_dynamics, t_span, y, events=events, dense_output=True)

        # Update state to the end of the integration step
        t_current = sol.t[-1]
        y = sol.y[:, -1]

        # If no event occurred, the simulation reached t_target
        if sol.status != 1:
            break

        # An event occurred. Update velocities based on collision type.
        # A set to prevent double-updating velocities in rare simultaneous collision cases.
        updated_velocities = set()
        
        # Check which event(s) triggered at the current time
        for event_idx, t_ev_list in enumerate(sol.t_events):
            if t_ev_list.size > 0 and np.isclose(t_ev_list[0], t_current):
                # Ball-ball collision events
                if event_idx == 0 and 0 not in updated_velocities and 1 not in updated_velocities:  # A-B
                    m1, m2 = MASSES[0], MASSES[1]
                    v1, v2 = y[3], y[4]
                    v1_new = ((m1 - m2) / (m1 + m2)) * v1 + (2 * m2 / (m1 + m2)) * v2
                    v2_new = (2 * m1 / (m1 + m2)) * v1 + ((m2 - m1) / (m1 + m2)) * v2
                    y[3], y[4] = v1_new, v2_new
                    updated_velocities.update([0, 1])
                elif event_idx == 1 and 1 not in updated_velocities and 2 not in updated_velocities:  # B-C
                    m1, m2 = MASSES[1], MASSES[2]
                    v1, v2 = y[4], y[5]
                    v1_new = ((m1 - m2) / (m1 + m2)) * v1 + (2 * m2 / (m1 + m2)) * v2
                    v2_new = (2 * m1 / (m1 + m2)) * v1 + ((m2 - m1) / (m1 + m2)) * v2
                    y[4], y[5] = v1_new, v2_new
                    updated_velocities.update([1, 2])
                elif event_idx == 2 and 0 not in updated_velocities and 2 not in updated_velocities:  # A-C
                    m1, m2 = MASSES[0], MASSES[2]
                    v1, v2 = y[3], y[5]
                    v1_new = ((m1 - m2) / (m1 + m2)) * v1 + (2 * m2 / (m1 + m2)) * v2
                    v2_new = (2 * m1 / (m1 + m2)) * v1 + ((m2 - m1) / (m1 + m2)) * v2
                    y[3], y[5] = v1_new, v2_new
                    updated_velocities.update([0, 2])
                # Wall collision events (velocity reverses)
                elif event_idx in [3, 4] and 0 not in updated_velocities:  # Ball A hits a wall
                    y[3] = -y[3]
                    updated_velocities.add(0)
                elif event_idx in [5, 6] and 1 not in updated_velocities:  # Ball B hits a wall
                    y[4] = -y[4]
                    updated_velocities.add(1)
                elif event_idx in [7, 8] and 2 not in updated_velocities:  # Ball C hits a wall
                    y[5] = -y[5]
                    updated_velocities.add(2)

    # Use the dense output to get the precise state at t_target
    final_state = sol.sol(t_target)

    # Format the output as a dictionary with 3D coordinates
    object_coordinate = {
        "object1": (round(final_state[0], 2), 0.00, 0.00),
        "object2": (round(final_state[1], 2), 0.00, 0.00),
        "object3": (round(final_state[2], 2), 0.00, 0.00),
    }
    return object_coordinate

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    """
    Main function to run the player-blackbox interaction loop.
    """
    # Instantiate the player model
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)

    # Initial message for the player
    blackbox_output_for_player = f'You have {max_turns} interaction turns to understand the black-box. Now the interaction starts. Only output the value and DO NOT contain any unrelated text.'

    # Interaction loop for `max_turns` queries + 1 final answer
    for i in range(max_turns + 1):
        # Get the player's query (a time `t` or the final answer)
        player_output_str = player.normal_output(blackbox_output_for_player)

        # The last iteration is for the player's final answer, so we don't query the blackbox.
        if i == max_turns:
            continue

        # Try to process the player's query and call the blackbox
        try:
            # Convert player's string output to a float for time
            t = float(player_output_str)
            if t < 0:
                # Physical time cannot be negative
                blackbox_result = "Invalid input: Time cannot be negative."
            else:
                blackbox_result = blackbox(t)
        except (ValueError, TypeError):
            # Handle cases where the player's output is not a valid number
            blackbox_result = f"Invalid input: '{player_output_str}'. Please provide a single float value for time t."

        # Prepare the feedback for the player for the next turn
        blackbox_output_for_player = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> {str(blackbox_result)}'

    # After the loop, evaluate the player's final answer and save the interaction history
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    # Parse command-line arguments
    args = sys.argv[1:]
    # Ensure the correct number of arguments are provided
    if len(args) != 13:
        print("Usage: python your_script.py model_family model_name task eva_mode n_runs difficulty task_id failure_num output_dir max_turns version mode thinking_mode")
        sys.exit(1)
    
    # Call the main function with parsed and type-casted arguments
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
