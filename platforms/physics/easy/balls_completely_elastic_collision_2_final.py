
import os
import sys
import math
import numpy as np
from scipy.integrate import solve_ivp

current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM

def blackbox(t: float):
    """
    Implements two balls completely elastic collision in a 2D plane.
    Ball A: mass = 4 kg, starts at origin, moves along x-axis at 3 m/s
    Ball B: mass = 2 kg, starts at x = 12 m, moves towards A at 5 m/s
    
    Args:
        t: time in seconds
        
    Returns:
        object_coordinate: dictionary containing 3D coordinates of both balls
    """
    # Initial conditions
    m_A = 4.0  # kg
    m_B = 2.0  # kg
    v_A_initial = 3.0  # m/s
    v_B_initial = -5.0  # m/s (negative because moving towards A)
    x_A_initial = 0.0  # m
    x_B_initial = 12.0  # m
    
    # Calculate time of collision
    # Solving x_A_initial + v_A_initial * t_collision = x_B_initial + v_B_initial * t_collision
    # (v_A_initial - v_B_initial) * t_collision = x_B_initial - x_A_initial
    t_collision = (x_B_initial - x_A_initial) / (v_A_initial - v_B_initial)
    
    # Calculate velocities after collision using conservation of momentum and energy
    # For 1D elastic collision:
    # v_A_final = ((m_A - m_B) * v_A_initial + 2 * m_B * v_B_initial) / (m_A + m_B)
    # v_B_final = ((m_B - m_A) * v_B_initial + 2 * m_A * v_A_initial) / (m_A + m_B)
    v_A_final = ((m_A - m_B) * v_A_initial + 2 * m_B * v_B_initial) / (m_A + m_B)
    v_B_final = ((m_B - m_A) * v_B_initial + 2 * m_A * v_A_initial) / (m_A + m_B)
    
    # Calculate positions
    if t < t_collision:
        # Before collision
        x_A = x_A_initial + v_A_initial * t
        x_B = x_B_initial + v_B_initial * t
    else:
        # After collision
        # Position at collision
        x_A_collision = x_A_initial + v_A_initial * t_collision
        x_B_collision = x_B_initial + v_B_initial * t_collision
        
        # Position after collision
        x_A = x_A_collision + v_A_final * (t - t_collision)
        x_B = x_B_collision + v_B_final * (t - t_collision)
    
    # Round to two decimal places
    x_A = round(x_A, 2)
    x_B = round(x_B, 2)
    
    # Return 3D coordinates (with y and z as 0)
    object_coordinate = {
        "object1": (x_A, 0.00, 0.00),
        "object2": (x_B, 0.00, 0.00)
    }
    
    return object_coordinate

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    # Instantiate ReasoningLLM class
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    
    # Iterative interaction between player and blackbox
    for i in range(max_turns + 1):
        if i == 0:
            # First interaction
            blackbox_output = f'You have {max_turns} interaction turns to understand the black-box. Now the interaction starts. Only output the value and DO NOT contain any unrelated text.'
        else:
            # Process player's input through the blackbox
            try:
                t = float(player_output)
                result = blackbox(t)
                blackbox_output = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> {result}'
            except:
                blackbox_output = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> Invalid input. ONLY provide the valid time value (float).'
        
        # Get player's response
        player_output = player.normal_output(blackbox_output)
        
        # In the last iteration, exit the loop
        if i == max_turns:
            continue
    
    # Evaluate player's performance and save history
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
