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
    Implements two balls completely elastic collision.
    Ball A: mass 5 kg, starts at origin, moves along x-axis at 4 m/s
    Ball B: mass 2 kg, starts at (10, 0, 0), initially at rest
    
    Args:
        t: time in seconds
    
    Returns:
        object_coordinate: dictionary containing 3D coordinates of both balls
    """
    # Initial conditions
    m_A = 5.0  # kg
    m_B = 2.0  # kg
    v_A_initial = 4.0  # m/s
    v_B_initial = 0.0  # m/s
    x_A_initial = 0.0  # m
    x_B_initial = 10.0  # m
    
    # Calculate time of collision
    t_collision = (x_B_initial - x_A_initial) / v_A_initial  # = 2.5 seconds
    
    # Calculate velocities after collision using conservation of momentum and energy
    v_A_final = ((m_A - m_B) * v_A_initial + 2 * m_B * v_B_initial) / (m_A + m_B)
    v_B_final = ((m_B - m_A) * v_B_initial + 2 * m_A * v_A_initial) / (m_A + m_B)
    
    # Calculate positions based on time
    if t < t_collision:
        # Before collision
        x_A = x_A_initial + v_A_initial * t
        x_B = x_B_initial + v_B_initial * t
    else:
        # After collision
        x_A = x_A_initial + v_A_initial * t_collision + v_A_final * (t - t_collision)
        x_B = x_B_initial + v_B_initial * t_collision + v_B_final * (t - t_collision)
    
    # Create the result dictionary with 3D coordinates (y and z are 0)
    object_coordinate = {
        "object1": (round(x_A, 2), 0.00, 0.00),
        "object2": (round(x_B, 2), 0.00, 0.00)
    }
    
    return object_coordinate

def black(player_output):
    """
    Process player's input and return blackbox output
    
    Args:
        player_output: player's input, expected to be a time value
    
    Returns:
        blackbox output for the given time
    """
    try:
        # Try to convert player's input to a float (time)
        t = float(player_output.strip())
        result = blackbox(t)
        return f"At time t={t} seconds, the coordinates are: {result}"
    except ValueError:
        return "Invalid input. Please provide a valid time value (a number)."

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    """
    Main function to handle the interaction between player and blackbox
    
    Args:
        Various parameters for the ReasoningLLM class and interaction control
    """
    # Instantiate the ReasoningLLM class
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    
    # Initial blackbox output
    blackbox_output = f'You have {max_turns} interaction turns to understand the black-box. Now the interaction starts. Only output the value and DO NOT contain any unrelated text.'
    
    # Interaction loop
    for i in range(max_turns + 1):
        # Get player's output based on blackbox output
        player_output = player.normal_output(blackbox_output)
        
        # Last iteration - exit the loop
        if i == max_turns:
            continue
        
        # Process player's output and get new blackbox output
        try:
            t = float(player_output)
            result = blackbox(t)
            blackbox_output = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> {result}'
        except:
            blackbox_output = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> Invalid input. ONLY provide the valid time value (float).'
    
    # Evaluate player's performance and save history
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))