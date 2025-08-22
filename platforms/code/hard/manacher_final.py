
import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from ckpt import get_local_variables, check_query_validity, get_ckpt_numbers, get_function_params, capture_print
from eva_models import ReasoningLLM
import re

# ------------------ Blackbox Function ------------------

def blackbox(s: str, idx=0, iter=0) -> None:
    get_local_variables.counters = {}
    get_local_variables.max_visits = {}
    # Manacher's algorithm with meaningless variable names
    a = '#' + '#'.join(s) + '#'
    t = [0] * len(a)
    num = 0
    r = 0
    for i in range(len(a)):
        if i < r:
            t[i] = min(r - i, t[2 * num - i])
        get_local_variables(1)
        while i - t[i] - 1 >= 0 and i + t[i] + 1 < len(a) and a[i - t[i] - 1] == a[i + t[i] + 1]:
            t[i] += 1
            get_local_variables(2)
        if i + t[i] > r:
            num = i
            r = i + t[i]
        get_local_variables(3)
    # Find the max value in t
    ll = 0
    center = 0
    for i in range(len(t)):
        if t[i] > ll:
            ll = t[i]
            center = i
        get_local_variables(4)
    # The longest palindromic substring is s[(center - ll)//2 : (center + ll)//2]
    check_query_validity(idx, iter)

# ------------------ Platform Function ------------------

vars = {}

@capture_print
def platform(player_output, max_turns=None):
    global vars
    try:
        if player_output == '':
            params = get_function_params(blackbox)
            num_ckpt = get_ckpt_numbers(blackbox, get_local_variables)
            print(f'The black-box takes {params} as input variables, and has {num_ckpt} checkpoints.')
        elif re.match(r'^\s*[\w_]+\s*=', player_output):
            # Parse variable assignments
            assignments = [x.strip() for x in player_output.split(';') if x.strip()]
            params_info = get_function_params(blackbox)
            param_names = {p['name']: p['type'] for p in params_info}
            for assign in assignments:
                if '=' not in assign:
                    print('Error: Invalid assignment format.')
                    return
                var, val = assign.split('=', 1)
                var = var.strip()
                val = val.strip()
                if var not in param_names:
                    print('Error: The variable name is not in the function parameters')
                    return
                # Convert val to correct type
                try:
                    if param_names[var] == str:
                        if val.startswith('"') and val.endswith('"'):
                            val = val[1:-1]
                        elif val.startswith("'") and val.endswith("'"):
                            val = val[1:-1]
                        else:
                            val = val
                    else:
                        val = eval(val)
                except Exception as e:
                    print(f'Error: Cannot convert value for {var}: {e}')
                    return
                vars[var] = val
            print(f'Set {vars}.')
        elif re.match(r'^\(\s*\d+\s*,\s*\d+\s*\)\s*$', player_output):
            # Parse (idx, iter)
            m = re.match(r'^\(\s*(\d+)\s*,\s*(\d+)\s*\)\s*$', player_output)
            idx = int(m.group(1))
            iter_ = int(m.group(2))
            params_info = get_function_params(blackbox)
            param_names = [p['name'] for p in params_info]
            missing = [p for p in param_names if p not in vars]
            if missing:
                print(f'Error: Missing variables {missing}.')
                return
            try:
                blackbox(**vars, idx=idx, iter=iter_)
            except Exception as e:
                print(f'Error: {e}')
        else:
            print("Invalid input format. Please use one of the following formats:\n"
                  "1. '' (empty string) to query function signature and checkpoints.\n"
                  "2. 'var1 = value1; var2 = value2; ...' to set input variables.\n"
                  "3. '(idx, iter)' to run the blackbox at checkpoint idx and iteration iter.")
    except Exception as e:
        print(f'Error: {e}')

# ------------------ Main Function ------------------

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    player_output = ''
    for i in range(max_turns):
        blackbox_output = platform(player_output)
        blackbox_output = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> ' + blackbox_output
        player_output = player.normal_output(blackbox_output)
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
