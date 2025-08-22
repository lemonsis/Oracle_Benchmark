
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
    Simulates a simple harmonic oscillator system and returns the object's coordinate at time t.

    The system details:
    - Mass (m): 1 kg
    - Spring constant (k): 100 N/m
    - Initial displacement from equilibrium: 0.2 m (contracted state)
    - Gravity (g): 10 m/s^2 (vertical system)
    - Released from rest.
    - No air resistance.
    - Coordinate origin: Set at the initial position of the oscillator.

    The motion is simple harmonic. The equation of motion for displacement 'y_eq' from equilibrium is:
    m * d^2(y_eq)/dt^2 = -k * y_eq
    The angular frequency omega = sqrt(k/m).
    Given m=1, k=100, omega = sqrt(100/1) = 10 rad/s.

    Initial conditions relative to equilibrium:
    y_eq(0) = -0.2 m (contracted, so 0.2m above equilibrium)
    dy_eq/dt(0) = 0 m/s (released from rest)

    The analytical solution for y_eq(t) is:
    y_eq(t) = A * cos(omega*t) + B * sin(omega*t)
    From y_eq(0) = -0.2 => A = -0.2
    From dy_eq/dt(0) = 0 => -A*omega*sin(0) + B*omega*cos(0) = 0 => B*omega = 0 => B = 0
    So, y_eq(t) = -0.2 * cos(10*t)

    The coordinate origin is set at the initial position of the oscillator.
    The initial position is y_eq(0) = -0.2 m relative to equilibrium.
    Let Y(t) be the coordinate relative to the origin.
    Y(t) = y_eq(t) - y_eq(0)
    Y(t) = -0.2 * cos(10*t) - (-0.2)
    Y(t) = 0.2 * (1 - cos(10*t))

    The system is vertical, so we assume motion along the y-axis.
    x(t) = 0
    z(t) = 0
    y(t) = 0.2 * (1 - math.cos(10 * t))
    """

    # Constants
    m = 1.0  # kg
    k = 100.0  # N/m
    # g = 10.0 # m/s^2 (not directly used in SHM equation once equilibrium is established as reference)

    # Calculate angular frequency
    omega = math.sqrt(k / m) # 10 rad/s

    # Calculate y(t) relative to the initial position (origin)
    # y(t) = 0.2 * (1 - cos(omega * t))
    y_coord = 0.3 * (1 - math.cos(omega * t))

    # x and z coordinates are 0 as motion is purely vertical
    x_coord = 0.0
    z_coord = 0.0

    # Approximate coordinates to two decimal places
    x_coord_rounded = round(x_coord, 2)
    y_coord_rounded = round(y_coord, 2)
    z_coord_rounded = round(z_coord, 2)

    object_coordinate = {
        "object1": (x_coord_rounded, y_coord_rounded, z_coord_rounded)
    }

    return object_coordinate

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    """
    Main function to handle the interaction between the player (ReasoningLLM) and the blackbox.
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
    args = sys.argv[1:]
    # Ensure correct type conversion for arguments
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
