
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

def blackbox(t):
    # Physical constants
    G = 6.7e-11  # N m²/kg²
    M_star = 8e29  # kg
    M_planet = 9e24  # kg
    periapsis = 6e10  # m
    apoapsis = 9e10  # m
    
    # Orbital parameters
    a = (periapsis + apoapsis) / 2  # semi-major axis
    e = (apoapsis - periapsis) / (apoapsis + periapsis)  # eccentricity
    
    # Initial conditions at periapsis
    # Position: at periapsis distance on x-axis
    x0 = periapsis
    y0 = 0
    
    # Velocity: perpendicular to position, calculated from vis-viva equation
    v_periapsis = math.sqrt(G * M_star * (2/periapsis - 1/a))
    vx0 = 0
    vy0 = v_periapsis
    
    # Define the system of ODEs
    def orbital_dynamics(t, y):
        x, y_pos, vx, vy = y
        r = math.sqrt(x**2 + y_pos**2)
        
        # Gravitational acceleration
        ax = -G * M_star * x / (r**3)
        ay = -G * M_star * y_pos / (r**3)
        
        return [vx, vy, ax, ay]
    
    # Initial state vector [x, y, vx, vy]
    y0_vec = [x0, y0, vx0, vy0]
    
    # Solve the ODE system
    if t == 0:
        x, y = x0, y0
    else:
        sol = solve_ivp(orbital_dynamics, [0, t], y0_vec, dense_output=True, rtol=1e-8, atol=1e-10)
        state = sol.sol(t)
        x, y = state[0], state[1]
    
    # Round to two decimal places and return 3D coordinates (z=0 for 2D orbit)
    object_coordinate = {
        "object1": (round(float(x), 2), round(float(y), 2), 0.00)
    }
    
    return object_coordinate

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    # Instantiate ReasoningLLM
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    
    # Initialize blackbox_output
    blackbox_output = f'You have {max_turns} interaction turns to understand the black-box. Now the interaction starts. Only output the value and DO NOT contain any unrelated text.'
    
    # Interaction loop
    for i in range(max_turns + 1):
        # Get player output
        player_output = player.normal_output(blackbox_output)
        
        # Exit in the last iteration
        if i == max_turns:
            continue
        
        # Get blackbox output
        try:
            t_value = float(player_output.strip())
            blackbox_result = blackbox(t_value)
            blackbox_output = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> {blackbox_result}'
        except:
            blackbox_output = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> Invalid input. ONLY provide the valid time value (float).'
    
    # Evaluate and save
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
