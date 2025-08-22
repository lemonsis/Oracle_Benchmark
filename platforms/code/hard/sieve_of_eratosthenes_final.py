
import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from ckpt import get_local_variables, check_query_validity, get_ckpt_numbers, get_function_params, capture_print
from eva_models import ReasoningLLM
import re

def blackbox(n: int, idx=0, iter=0):
    get_local_variables.counters = {}
    get_local_variables.max_visits = {}
    
    # Initialize array with all numbers marked as potential primes
    a = [True for _ in range(n+1)]
    a[0] = a[1] = False  # 0 and 1 are not prime
        
    # Apply Sieve of Eratosthenes
    p = 2
    while p * p <= n:
        if a[p]:
            # Mark all multiples of p as non-prime
            for i in range(p * p, n + 1, p):
                a[i] = False
            get_local_variables(1)
        p += 1
    
        get_local_variables(2)
    
    # Collect all prime numbers
    s = []
    for i in range(2, n + 1):
        if a[i]:
            s.append(i)
    
        get_local_variables(3)
    
    check_query_validity(idx, iter)

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
    if '=' in player_output:
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
    
    # Condition 3: Checkpoint query
    match = re.match(r'\((\d+),\s*(\d+)\)', player_output.strip())
    if match:
        try:
            idx = int(match.group(1))
            iter = int(match.group(2))
            blackbox(**vars, idx=idx, iter=iter)
        except Exception as e:
            print(f'Error executing blackbox: {str(e)}')
    else:
        print('Invalid input format. Please use one of the following formats:')
        print('1. Empty string to get function parameters and checkpoint info')
        print('2. "var1 = value1; var2 = value2; ..." to set variable values')
        print('3. "(idx, iter)" to query a specific checkpoint')

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    # Instantiate the ReasoningLLM class
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    
    # Initial empty query to get function info
    player_output = ''
    
    # Iterative interaction between player and blackbox
    for i in range(max_turns):
        blackbox_output = platform(player_output)
        blackbox_output_with_turn = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> {blackbox_output}'
        player_output = player.normal_output(blackbox_output_with_turn)
    
    # Evaluate and save results
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
