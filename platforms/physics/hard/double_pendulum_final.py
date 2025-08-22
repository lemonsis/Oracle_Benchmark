
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

def blackbox(t: float):
    # Double pendulum parameters
    m1, m2 = 1.0, 1.0  # masses in kg
    L1, L2 = 1.0, 1.0  # lengths in m
    g = 10.0  # gravity in m/s^2
    
    # Initial conditions
    theta1_0 = math.radians(45)  # 45 degrees to radians
    theta2_0 = math.radians(45)  # 45 degrees to radians
    omega1_0 = 0.0  # initial angular velocity
    omega2_0 = 0.0  # initial angular velocity
    
    # Define the system of ODEs
    def double_pendulum_ode(t, y):
        theta1, omega1, theta2, omega2 = y
        
        # Calculate denominators and common terms
        delta = theta2 - theta1
        den1 = (m1 + m2) * L1 - m2 * L1 * math.cos(delta) * math.cos(delta)
        den2 = (L2 / L1) * den1

        # Calculate numerators
        num1 = (-m2 * L1 * omega1**2 * math.sin(delta) * math.cos(delta) +
                m2 * g * math.sin(theta2) * math.cos(delta) +
                m2 * L2 * omega2**2 * math.sin(delta) -
                (m1 + m2) * g * math.sin(theta1))
        
        num2 = (-m2 * L2 * omega2**2 * math.sin(delta) * math.cos(delta) +
                (m1 + m2) * g * math.sin(theta1) * math.cos(delta) +
                (m1 + m2) * L1 * omega1**2 * math.sin(delta) -
                (m1 + m2) * g * math.sin(theta2))
        
        # Calculate angular accelerations
        alpha1 = num1 / den1
        alpha2 = num2 / den2
        
        return [omega1, alpha1, omega2, alpha2]
    
    # Solve the ODE up to time t
    if t == 0:
        theta1, theta2 = theta1_0, theta2_0
    else:
        y0 = [theta1_0, omega1_0, theta2_0, omega2_0]
        sol = solve_ivp(double_pendulum_ode, [0, t], y0, dense_output=True, rtol=1e-8)
        theta1, omega1, theta2, omega2 = sol.sol(t)
    
    # Calculate positions
    x1 = L1 * math.sin(theta1)
    y1 = -L1 * math.cos(theta1)
    z1 = 0.0
    
    x2 = L1 * math.sin(theta1) + L2 * math.sin(theta2)
    y2 = -L1 * math.cos(theta1) - L2 * math.cos(theta2)
    z2 = 0.0
    
    # Round to two decimal places
    object_coordinate = {
        "object1": (round(x1, 2), round(y1, 2), round(z1, 2)),
        "object2": (round(x2, 2), round(y2, 2), round(z2, 2))
    }
    
    return object_coordinate

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    # Instantiate ReasoningLLM
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    
    # Initialize blackbox output
    blackbox_output = f'You have {max_turns} interaction turns to understand the black-box. Now the interaction starts. Only output the value and DO NOT contain any unrelated text.'
    
    # Interaction loop
    for i in range(max_turns + 1):
        if i == max_turns:
            player_output = player.normal_output(blackbox_output)
            continue
        
        player_output = player.normal_output(blackbox_output)
        try:
            t_value = float(player_output.strip())
            blackbox_result = blackbox(t_value)
        except (ValueError, TypeError):
            blackbox_result = "Error: Invalid input. Please provide a numeric value."
        blackbox_output = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> {blackbox_result}'
    
    # Evaluate and save history
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
