
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
    # Parameters
    m = 1.0  # mass in kg
    k = 100.0  # spring constant in N/m
    mu = 0.1  # friction coefficient
    g = 10  # gravity
    x0 = 1.0  # initial displacement (contracted state)
    v0 = 0.0  # initial velocity
    
    # Define the system of ODEs
    def system(t, y):
        x, v = y
        # Friction force depends on velocity direction
        if abs(v) < 1e-10:  # Nearly at rest
            friction = 0
        else:
            friction = -mu * m * g * np.sign(v)
        
        # Equation of motion: ma = -kx + friction
        a = (-k * x + friction) / m
        return [v, a]
    
    # Time span for integration
    t_span = (0, min(t, 100))
    t_eval = np.linspace(0, min(t, 100), int(min(t, 100) * 10) + 1)
    
    # Initial conditions [position, velocity]
    y0 = [x0, v0]
    
    # Solve the ODE
    try:
        sol = solve_ivp(system, t_span, y0, t_eval=t_eval, method='RK45', rtol=1e-8)
        
        # Find the closest time point
        if t <= 100:
            idx = min(range(len(sol.t)), key=lambda i: abs(sol.t[i] - t))
            x_val = sol.y[0][idx]
        else:
            # For t > 100, assume system has settled
            x_val = 0.0
            
    except:
        # Fallback to analytical approximation if numerical fails
        omega = math.sqrt(k/m)
        x_val = x0 * math.cos(omega * t) * math.exp(-mu * g * t / 2)
    
    # Round to 2 decimal places and return 3D coordinates
    x_coord = round(float(x_val), 2)
    y_coord = 0.0  # System is horizontal
    z_coord = 0.0  # System is horizontal
    
    object_coordinate = {"object1": (x_coord, y_coord, z_coord)}
    return object_coordinate

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    # Instantiate ReasoningLLM
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    
    # Initialize blackbox_output for first interaction
    blackbox_output = f'You have {max_turns} interaction turns to understand the black-box. Now the interaction starts. Only output the value and DO NOT contain any unrelated text.'
    
    # Interaction loop
    for i in range(max_turns + 1):
        if i == max_turns:
            # Last iteration
            player_output = player.normal_output(blackbox_output)
            continue
        else:
            # Regular iterations
            player_output = player.normal_output(blackbox_output)
            
            # Get blackbox response
            try:
                t_value = float(player_output.strip())
                blackbox_result = blackbox(t_value)
                blackbox_output = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> {blackbox_result}'
            except:
                blackbox_output = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> Invalid input. Please provide a numeric value for time t.'
    
    # Evaluate and save history
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
    # main('gpt', 'gpt-4.1', 'physics', 'normal', 1, 'hard', 'harmonic_friction', 1, 'logs', 5, 3, 'generate', False)