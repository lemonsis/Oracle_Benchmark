
import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM

def blackbox(truth, query):
    # Check if query is in the correct format: "Number X" where X is an integer in [0, 100]
    if not isinstance(query, str):
        return "Query should be a string in the format 'Number X', where X is an integer between 0 and 100."
    parts = query.strip().split()
    if len(parts) != 2 or parts[0] != "Number":
        return "Query format incorrect. Please use the format 'Number X', where X is an integer between 0 and 100."
    try:
        guess = int(parts[1])
    except ValueError:
        return "Query format incorrect. X should be an integer between 0 and 100."
    if not (0 <= guess <= 100):
        return "Query out of range. X should be an integer between 0 and 100."
    try:
        truth_num = int(truth.strip().split()[1])
    except Exception:
        return "Internal error: truth format incorrect."
    diff = abs(guess - truth_num)
    if diff > 15:
        return "Far"
    else:
        return "Close"

def check_answer_format(answer):
    # Check if answer is in the format "Number X" where X is an integer in [0, 100]
    if not isinstance(answer, str):
        return False
    parts = answer.strip().split()
    if len(parts) != 2 or parts[0] != "Number":
        return False
    try:
        x = int(parts[1])
    except ValueError:
        return False
    if not (0 <= x <= 100):
        return False
    return True

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    player.evaluate(failure_num, version, max_turns)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
