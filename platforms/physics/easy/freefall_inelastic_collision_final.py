
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
    # Parameters
    mass = 5  # kg
    initial_height = 20  # m
    g = 10  # m/s²
    coeff_restitution = 0.6
    
    # Calculate bouncing motion
    current_time = t
    current_height = initial_height
    current_velocity = 0
    
    # Time to first impact
    first_impact_time = math.sqrt(2 * initial_height / g)
    
    if t <= first_impact_time:
        # Before first impact - free fall
        y = initial_height - 0.5 * g * t**2
    else:
        # After first impact - handle bounces
        remaining_time = t - first_impact_time
        
        # Velocity just before first impact
        impact_velocity = math.sqrt(2 * g * initial_height)
        
        # Velocity after first bounce
        bounce_velocity = coeff_restitution * impact_velocity
        current_height = (bounce_velocity**2) / (2 * g)
        current_velocity = bounce_velocity
        
        while remaining_time > 0:
            # Time for current bounce cycle (up and down)
            bounce_cycle_time = 2 * current_velocity / g
            
            if remaining_time <= bounce_cycle_time:
                # Within current bounce cycle
                y = current_velocity * remaining_time - 0.5 * g * remaining_time**2
                break
            else:
                # Complete this bounce cycle and move to next
                remaining_time -= bounce_cycle_time
                
                # New bounce parameters
                current_velocity = coeff_restitution * current_velocity
                current_height = (current_velocity**2) / (2 * g)
                
                if current_height < 0.01:  # Stop bouncing when height is negligible
                    y = 0.0
                    break
        else:
            y = 0.0
    
    # Ensure y is not negative
    y = max(0.0, y)
    
    # Round to two decimal places and ensure 3D coordinates
    x, y, z = 0.0, round(y, 2), 0.0
    
    object_coordinate = {"object1": (x, y, z)}
    return object_coordinate

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    # Instantiate ReasoningLLM
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    
    # Initial blackbox output
    blackbox_output = f'You have {max_turns} interaction turns to understand the black-box. Now the interaction starts. Only output the value and DO NOT contain any unrelated text.'
    
    # Interaction loop
    for i in range(max_turns + 1):
        # Get player output
        player_output = player.normal_output(blackbox_output)
        
        # Exit in last iteration
        if i == max_turns:
            continue
        
        # Get blackbox output
        try:
            t_value = float(player_output.strip())
            blackbox_result = blackbox(t_value)
            blackbox_output = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> ' + str(blackbox_result)
        except:
            blackbox_output = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> Invalid input. ONLY provide the valid time value (float).'
    
    # Evaluate and save
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
