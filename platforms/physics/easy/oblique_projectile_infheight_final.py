
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
    # Oblique projectile motion from infinite height
    # Initial conditions:
    # - Initial horizontal velocity: 10 m/s
    # - Initial vertical velocity: 10 m/s
    # - Gravity: 10 m/s²
    # - No air resistance
    # - Coordinate origin at initial position
    
    # For oblique projectile motion:
    # x(t) = v0x * t
    # y(t) = v0y * t - (1/2) * g * t²
    # z(t) = 0 (2D motion in x-y plane)
    
    v0x = 10  # initial horizontal velocity
    v0y = 10  # initial vertical velocity
    g = 10    # gravity
    
    x = v0x * t
    y = v0y * t - 0.5 * g * t * t
    z = 0.0
    
    # Round to two decimal places
    x = round(x, 2)
    y = round(y, 2)
    z = round(z, 2)
    
    object_coordinate = {"object1": (x, y, z)}
    return object_coordinate

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    # Instantiate ReasoningLLM
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    
    # Initial blackbox output for first interaction
    blackbox_output = f'You have {max_turns} interaction turns to understand the black-box. Now the interaction starts. Only output the value and DO NOT contain any unrelated text.'
    
    # Interaction loop
    for i in range(max_turns + 1):
        # Get player output
        player_output = player.normal_output(blackbox_output)
        
        # Exit on last iteration
        if i == max_turns:
            continue
            
        # Get blackbox output
        try:
            t = float(player_output)
            blackbox_result = blackbox(t)
            blackbox_output = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> {blackbox_result}'
        except:
            blackbox_output = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> Invalid input. ONLY provide the valid time value (float).'
    
    # Evaluate and save
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
