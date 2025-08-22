import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM

import re

def is_valid_equation(equation):
    """
    Checks if the string is a valid equation of length 15, with exactly one '=' sign,
    and both sides are valid arithmetic expressions and the equation holds true.
    """
    if len(equation) != 15:
        return False
    if equation.count('=') != 1:
        return False
    left, right = equation.split('=')
    # Both sides must be non-empty
    if not left or not right:
        return False
    # Only allow digits and + - * / in left, only digits in right
    if not re.fullmatch(r'[0-9+\-*/]+', left):
        return False
    if not re.fullmatch(r'[0-9]+', right):
        return False
    # No leading zeros in numbers (except for '0')
    if re.search(r'\b0[0-9]+', left) or re.search(r'\b0[0-9]+', right):
        return False
    # No consecutive operators
    if re.search(r'[\+\-\*/]{2,}', left):
        return False
    # Left side must not start or end with operator
    if left[0] in '+-*/' or left[-1] in '+-*/':
        return False
    # Evaluate left side
    try:
        # Prevent division by zero
        if '/0' in left:
            return False
        left_val = eval(left)
        right_val = int(right)
        # Only integer results allowed
        if not isinstance(left_val, int) and not (isinstance(left_val, float) and left_val.is_integer()):
            return False
        if int(left_val) != right_val:
            return False
    except Exception:
        return False
    return True

def blackbox(truth, query):
    """
    Implements the Nerdle blackbox.
    Returns feedback string or advice if query is invalid.
    """
    # Check format
    if len(query) != 15:
        return "Your query must be exactly 15 characters long."
    if query.count('=') != 1:
        return "Your query must contain exactly one '=' sign."
    if not is_valid_equation(query):
        return "Your query is not a valid equation. Please ensure both sides are valid and the equation is correct."
    # Feedback calculation
    feedback = ['X'] * 15
    truth_list = list(truth)
    query_list = list(query)
    used_truth = [False] * 15
    used_query = [False] * 15

    # First pass: correct position (A)
    for i in range(15):
        if query_list[i] == truth_list[i]:
            feedback[i] = 'A'
            used_truth[i] = True
            used_query[i] = True

    # Second pass: misplaced (M)
    for i in range(15):
        if feedback[i] == 'A':
            continue
        for j in range(15):
            if not used_truth[j] and query_list[i] == truth_list[j]:
                feedback[i] = 'M'
                used_truth[j] = True
                used_query[i] = True
                break
    # Remaining are 'X'
    return ''.join(feedback)

def check_answer_format(answer):
    """
    Checks if the answer is a valid 15-character equation as per Nerdle rules.
    """
    return is_valid_equation(answer)

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    player.evaluate(failure_num, version, max_turns)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))