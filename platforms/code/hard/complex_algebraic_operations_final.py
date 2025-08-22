
import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from ckpt import get_local_variables, check_query_validity, get_ckpt_numbers, get_function_params, capture_print
from eva_models import ReasoningLLM
import re

def blackbox(a: int, b: int, c: int, d: int, idx=0, iter=0):
    get_local_variables.counters = {}
    get_local_variables.max_visits = {}
    
    e = a * b + c * d
    get_local_variables(1)
    
    if e > 50:
        e = e - 10
    else:
        e = e + 10
    get_local_variables(2)
    
    f = e**2 - a - b - c - d
    get_local_variables(3)
    
    if f % 2 == 1:  # f is odd
        f = (f - 1) // 2
    else:
        f = f // 2
    get_local_variables(4)
    
    g = f - a
    get_local_variables(5)
    
    check_query_validity(idx, iter)

vars = {}

@capture_print
def platform(player_output):
    global vars
    
    if player_output == '':
        params = get_function_params(blackbox)
        num_ckpt = get_ckpt_numbers(blackbox, get_local_variables)
        print(f'The black-box takes {params} as input variables, and has {num_ckpt} checkpoints.')
    elif re.match(r'^(\w+\s*=\s*[^;]+;\s*)*(\w+\s*=\s*[^;]+)$', player_output):
        # Format: "variable_name_1 = value_1; variable_name_2 = value_2; ..."
        assignments = re.split(r';\s*', player_output)
        params_info = get_function_params(blackbox)
        param_names = [param['name'] for param in params_info]
        
        updated_vars = {}
        for assignment in assignments:
            var_name, value_str = assignment.split('=', 1)
            var_name = var_name.strip()
            value_str = value_str.strip()
            
            if var_name not in param_names:
                print('Error: The variable name is not in the function parameters')
                return
            
            # Find the expected type for this variable
            var_type = next(param['type'] for param in params_info if param['name'] == var_name)
            
            try:
                # Convert the string value to the appropriate type
                if var_type == int:
                    value = int(value_str)
                elif var_type == float:
                    value = float(value_str)
                elif var_type == list:
                    value = eval(value_str)
                elif var_type == str:
                    value = value_str.strip('"\'')
                else:
                    value = eval(value_str)
                
                updated_vars[var_name] = value
            except Exception as e:
                print(f'Error: Failed to convert value for {var_name}: {e}')
                return
        
        # Update the global vars dictionary
        vars.update(updated_vars)
        print(f'Set {vars}.')
    elif re.match(r'^\(\s*\d+\s*,\s*\d+\s*\)$', player_output):
        # Format: "(idx, iter)"
        try:
            idx_iter = eval(player_output)
            if len(idx_iter) != 2:
                print('Error: Expected format is (idx, iter)')
                return
            
            idx, iter = idx_iter
            if not all(isinstance(x, int) for x in [idx, iter]):
                print('Error: idx and iter must be integers')
                return
            
            if not vars:
                print('Error: No variables have been set yet')
                return
            
            blackbox(**vars, idx=idx, iter=iter)
        except Exception as e:
            print(f'Error: {e}')
    else:
        print('Error: Invalid input format. Use one of the following formats:')
        print('1. Empty string to get function parameters and checkpoint count')
        print('2. "var1 = value1; var2 = value2; ..." to set variable values')
        print('3. "(idx, iter)" to query the blackbox at a specific checkpoint and iteration')

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    
    player_output = ''
    for i in range(max_turns):
        blackbox_output = platform(player_output)
        blackbox_output = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> {blackbox_output}'
        player_output = player.normal_output(blackbox_output)
    
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
