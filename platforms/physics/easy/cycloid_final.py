
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
    """
    Implements cycloid motion for a fixed point on a circle rolling along a straight line.
    Circle radius: 1 m, Circle speed: 1 m/s
    """
    # For a cycloid with radius r=1 and speed v=1 m/s:
    # Angular velocity ω = v/r = 1 rad/s
    # Parametric equations:
    # x(t) = r(ωt - sin(ωt)) = t - sin(t)
    # y(t) = r(1 - cos(ωt)) = 1 - cos(t)
    # z(t) = 0 (2D motion in 3D space)
    
    x = t - math.sin(t)
    y = 1 - math.cos(t)
    z = 0.0
    
    # Round to two decimal places
    x = round(x, 2)
    y = round(y, 2)
    z = round(z, 2)
    
    object_coordinate = {"object1": (x, y, z)}
    return object_coordinate

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    # Instantiate ReasoningLLM class
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    
    # Initialize blackbox_output for first call
    blackbox_output = f'You have {max_turns} interaction turns to understand the black-box. Now the interaction starts. Only output the value and DO NOT contain any unrelated text.'
    
    # Iterative interaction loop
    for i in range(max_turns + 1):
        player_output = player.normal_output(blackbox_output)
        
        if i == max_turns:
            continue
        
        # Call blackbox with player output
        try:
            blackbox_result = blackbox(float(player_output))
            blackbox_output = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> {blackbox_result}'
        except:
            blackbox_output = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> Invalid input. ONLY provide the valid time value (float).'

    
    # Evaluate and save results
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
