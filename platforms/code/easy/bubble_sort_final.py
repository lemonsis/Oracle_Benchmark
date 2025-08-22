
import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from ckpt import get_local_variables, check_query_validity, get_ckpt_numbers, get_function_params, capture_print
from eva_models import ReasoningLLM
import re

def blackbox(arr: list, idx=0, iter=0):
    get_local_variables.counters = {}
    get_local_variables.max_visits = {}
    
    n = len(arr)
    get_local_variables(1)
    
    for i in range(n):
        for j in range(0, n-i-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
            get_local_variables(2)
    
    get_local_variables(3)
    check_query_validity(idx, iter)

vars = {}

@capture_print
def platform(player_output, max_turns=None):
    global vars
    
    # Condition 1: Empty input, return function parameters and checkpoint info
    if player_output == '':
        params = get_function_params(blackbox)
        num_ckpt = get_ckpt_numbers(blackbox, get_local_variables)
        print(f'The black-box takes {params} as input variables, and has {num_ckpt} checkpoints.')
        return
    
    # Condition 2: Variable assignments
    if '=' in player_output:
        if ';' in player_output:
            assignments = player_output.split(';')
        else:
            assignments = [player_output]
        params_info = get_function_params(blackbox)
        param_names = [param['name'] for param in params_info]
        
        for assignment in assignments:
            if not assignment.strip():
                continue
                
            try:
                var_name, var_value = assignment.split('=', 1)
                var_name = var_name.strip()
                var_value = var_value.strip()
                
                if var_name not in param_names:
                    print(f'Error: The variable name {var_name} is not in the function parameters')
                    return
                
                # Find the expected type for this variable
                expected_type = next(param['type'] for param in params_info if param['name'] == var_name)
                
                # Convert string to the appropriate type
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
                print(f'Error parsing assignment: {assignment}. {str(e)}')
                return
                
        print(f'Set {vars}.')
        return
    
    # Condition 3: Execute blackbox with checkpoint indices
    match = re.match(r'\(\s*(\d+)\s*,\s*(\d+)\s*\)', player_output)
    if match:
        try:
            idx = int(match.group(1))
            iter = int(match.group(2))
            blackbox(**vars, idx=idx, iter=iter)
        except Exception as e:
            print(f'Error executing blackbox: {str(e)}')
        return
    
    # If none of the conditions match
    print('Invalid input format. Please use one of the following formats:')
    print('1. Empty string to get function parameters and checkpoint info')
    print('2. "variable_name_1 = value_1; variable_name_2 = value_2; ..." to set variables')
    print('3. "(idx, iter)" to execute the blackbox with checkpoint indices')

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