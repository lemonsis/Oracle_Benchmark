
import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from ckpt import get_local_variables, check_query_validity, get_ckpt_numbers, get_function_params, capture_print
from eva_models import ReasoningLLM
import re

def blackbox(a: int, b: int, idx=0, iter=0):
    get_local_variables.counters = {}
    get_local_variables.max_visits = {}
    
    # Check if divisor is zero
    if b == 0:
        print("Error: Division by zero")
        check_query_validity(idx, iter)
        return
    
    # Handle negative numbers
    neg = False
    if (a < 0 and b > 0) or (a > 0 and b < 0):
        neg = True
    
    a, b = abs(a), abs(b)
    
    # Integer part
    q = a // b
    r = a % b
    
    get_local_variables(1)
    
    # Calculate decimal part
    d = []
    for i in range(4):  # Keep 4 decimal places
        r *= 10
        d.append(r // b)
        r = r % b
    
    get_local_variables(2)
    
    # Round the last digit
    if r * 10 // b >= 5:
        # Handle rounding
        d[3] += 1
        for j in range(3, -1, -1):
            if d[j] == 10:
                d[j] = 0
                if j > 0:
                    d[j-1] += 1
                else:
                    q += 1
    
    get_local_variables(3)
    
    # Format the result
    s = str(q)
    if any(d):
        s += "."
        for digit in d:
            s += str(digit)
    
    # Apply sign
    if neg:
        s = "-" + s
    
    check_query_validity(idx, iter)

# Global dictionary to store variables
vars = {}

@capture_print
def platform(player_output):
    global vars
    
    # Condition 1: Empty input, return function parameters and checkpoint info
    if player_output == '':
        params = get_function_params(blackbox)
        num_ckpt = get_ckpt_numbers(blackbox, get_local_variables)
        print(f'The black-box takes {params} as input variables, and has {num_ckpt} checkpoints.')
        return
    
    # Condition 2: Variable assignments
    if '=' in player_output and ';' in player_output:
        try:
            assignments = player_output.split(';')
            params_info = get_function_params(blackbox)
            param_names = [param['name'] for param in params_info]
            
            for assignment in assignments:
                if not assignment.strip():
                    continue
                
                var_name, var_value = assignment.split('=', 1)
                var_name = var_name.strip()
                var_value = var_value.strip()
                
                if var_name not in param_names:
                    print(f'Error: The variable name {var_name} is not in the function parameters')
                    return
                
                # Find the expected type for this variable
                expected_type = next(param['type'] for param in params_info if param['name'] == var_name)
                
                # Convert string to the appropriate type
                try:
                    if expected_type == int:
                        vars[var_name] = int(var_value)
                    elif expected_type == float:
                        vars[var_name] = float(var_value)
                    elif expected_type == list:
                        vars[var_name] = eval(var_value)
                    elif expected_type == str:
                        vars[var_name] = var_value.strip('"\'')
                    else:
                        vars[var_name] = eval(var_value)
                except Exception as e:
                    print(f'Error: Failed to convert {var_value} to {expected_type.__name__}: {str(e)}')
                    return
            
            print(f'Set {vars}.')
            return
        except Exception as e:
            print(f'Error in parsing variable assignments: {str(e)}')
            print('Format should be: variable_name_1 = value_1; variable_name_2 = value_2; ...')
            return
    
    # Condition 3: Checkpoint query
    match = re.match(r'\((\d+),\s*(\d+)\)', player_output.strip())
    if match:
        try:
            idx = int(match.group(1))
            iter = int(match.group(2))
            blackbox(**vars, idx=idx, iter=iter)
            return
        except Exception as e:
            print(f'Error in executing checkpoint query: {str(e)}')
            return
    
    # If none of the conditions match
    print('Invalid input format. Please use one of the following:')
    print('1. Empty string to get function parameters and checkpoint info')
    print('2. "variable_name_1 = value_1; variable_name_2 = value_2; ..." to set variables')
    print('3. "(idx, iter)" to query a checkpoint')

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    # Initialize the player
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    
    # Start with an empty player output to get function info
    player_output = ''
    
    # Interaction loop
    for i in range(max_turns):
        # Get blackbox response
        blackbox_output = platform(player_output)
        
        # Add turn information
        blackbox_output = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> {blackbox_output}'
        # Get player's next move
        player_output = player.normal_output(blackbox_output)
    
    # Evaluate and save results
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
