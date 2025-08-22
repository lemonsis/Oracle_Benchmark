
import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from ckpt import get_local_variables, check_query_validity, get_ckpt_numbers, get_function_params, capture_print
from eva_models import ReasoningLLM
import re

def blackbox(m: int, n: int, idx=0, iter=0):
    """
    A hundred coins for a hundred fowls problem solver.
    m: number of coins
    n: number of fowls to buy
    """
    get_local_variables.counters = {}
    get_local_variables.max_visits = {}
    
    a = 0  # roosters
    b = 0  # hens
    c = 0  # chicks
    
    get_local_variables(1)
    
    f = False  # flag for solution found
    
    for x in range(m // 5 + 1):  # max possible roosters
        for y in range(m // 3 + 1):  # max possible hens
            z = n - x - y  # remaining must be chicks
            
            if z < 0:
                continue
                
            t = 5 * x + 3 * y + z  # total cost
            get_local_variables(2)
            if t == m and x + y + z == n:
                a, b, c = x, y, z
                f = True
                break
                
        if f:
            break
    
        get_local_variables(3)
    
    check_query_validity(idx, iter)

@capture_print
def platform(player_output):
    global vars
    
    if player_output == '':
        params = get_function_params(blackbox)
        num_ckpt = get_ckpt_numbers(blackbox, get_local_variables)
        print(f'The black-box takes {params} as input variables, and has {num_ckpt} checkpoints.')
    
    elif re.match(r'^(\w+\s*=\s*[^;]+;\s*)*(\w+\s*=\s*[^;]+)$', player_output):
        try:
            params_info = get_function_params(blackbox)
            param_names = [param['name'] for param in params_info]
            
            # Initialize vars if not exists
            if 'vars' not in globals():
                globals()['vars'] = {}
            
            # Parse variable assignments
            assignments = re.findall(r'(\w+)\s*=\s*([^;]+)(?:;|$)', player_output)
            
            for var_name, var_value in assignments:
                if var_name not in param_names:
                    print(f'Error: The variable name {var_name} is not in the function parameters')
                    return
                
                # Find the expected type for this parameter
                expected_type = next(param['type'] for param in params_info if param['name'] == var_name)
                
                try:
                    # Convert string to actual value
                    if expected_type == int:
                        value = int(var_value.strip())
                    elif expected_type == float:
                        value = float(var_value.strip())
                    elif expected_type == list:
                        value = eval(var_value.strip())
                    elif expected_type == str:
                        value = var_value.strip()
                    else:
                        value = eval(var_value.strip())
                    
                    vars[var_name] = value
                except Exception as e:
                    print(f'Error: Failed to convert {var_value} to {expected_type}: {str(e)}')
                    return
            
            print(f'Set {vars}.')
        
        except Exception as e:
            print(f'Error: {str(e)}')
    
    elif re.match(r'^\(\s*\d+\s*,\s*\d+\s*\)$', player_output):
        try:
            if 'vars' not in globals():
                print('Error: No variables set. Please set variables first.')
                return
                
            match = re.match(r'^\(\s*(\d+)\s*,\s*(\d+)\s*\)$', player_output)
            idx, iter = int(match.group(1)), int(match.group(2))
            
            blackbox(**vars, idx=idx, iter=iter)
        except Exception as e:
            print(f'Error: {str(e)}')
    
    else:
        print("Invalid input format. Please use one of the following formats:")
        print("1. Empty string to get function information")
        print("2. 'variable_name = value; variable_name = value; ...' to set variables")
        print("3. '(idx, iter)' to run the blackbox with specific checkpoint and iteration")

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    # Initialize the player
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    
    # Initialize player output as empty string for the first turn
    player_output = ''
    
    # Interaction loop
    for i in range(max_turns):
        # Get blackbox output based on player's input
        blackbox_output = platform(player_output)
        
        # Add turn information to blackbox output
        blackbox_output_with_turn = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> {blackbox_output}'
        
        # Get player's response
        player_output = player.normal_output(blackbox_output_with_turn)
    
    # Evaluate player's performance
    player.evaluate(failure_num, version)
    
    # Save interaction history
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
