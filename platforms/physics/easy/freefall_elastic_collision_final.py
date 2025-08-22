
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
    # Physical parameters
    mass = 5  # kg
    initial_height = 10  # m
    g = 10  # m/s²
    
    # Calculate time to fall to ground
    t_fall = math.sqrt(2 * initial_height / g)  # Time to fall from initial height
    period = 2 * t_fall  # Period of complete bounce cycle
    
    # Reduce time to within one period
    t_mod = t % period
    
    # Determine position based on phase of motion
    if t_mod <= t_fall:
        # Falling phase
        y = initial_height - 0.5 * g * t_mod**2
    else:
        # Rising phase after bounce
        t_rise = t_mod - t_fall
        # Initial velocity after bounce (upward)
        v0 = math.sqrt(2 * g * initial_height)
        y = v0 * t_rise - 0.5 * g * t_rise**2
    
    # Round to two decimal places
    x = round(0.0, 2)  # No horizontal motion
    y = round(y, 2)
    z = round(0.0, 2)  # No motion in z direction
    
    object_coordinate = {"object1": (x, y, z)}
    return object_coordinate

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    # Instantiate ReasoningLLM
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    
    # Initialize blackbox_output for first iteration
    blackbox_output = f'You have {max_turns} interaction turns to understand the black-box. Now the interaction starts. Only output the value and DO NOT contain any unrelated text.'
    
    # Interaction loop
    for i in range(max_turns + 1):
        player_output = player.normal_output(blackbox_output)
        
        if i == max_turns:
            continue
        
        # Call blackbox with player output (assuming it's a time value)
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
