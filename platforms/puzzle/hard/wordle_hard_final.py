
import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM

def blackbox(truth, query):
    """
    Implements the Wordle feedback mechanism.
    Args:
        truth (str): The hidden 11-letter uppercase word.
        query (str): The player's guess.
    Returns:
        str: Feedback string of length 11 using 'A', 'M', 'X', or a correction message if input is invalid.
    """
    # Check input validity
    if not isinstance(query, str):
        return "Query must be a string."
    if len(query) != 11:
        return "Query must be exactly 11 letters."
    if not query.isalpha() or not query.isupper():
        return "Query must be 11 uppercase English letters."
    if not isinstance(truth, str) or len(truth) != 11 or not truth.isalpha() or not truth.isupper():
        return "Internal error: truth word is not a valid 11-letter uppercase word."

    feedback = ['X'] * 11
    truth_list = list(truth)
    query_list = list(query)
    used = [False] * 11  # Track used letters in truth for 'M'

    # First pass: check for correct letter and position ('A')
    for i in range(11):
        if query_list[i] == truth_list[i]:
            feedback[i] = 'A'
            used[i] = True

    # Second pass: check for correct letter, wrong position ('M')
    for i in range(11):
        if feedback[i] == 'A':
            continue
        for j in range(11):
            if not used[j] and query_list[i] == truth_list[j] and i != j:
                feedback[i] = 'M'
                used[j] = True
                break

    return ''.join(feedback)

def check_answer_format(answer):
    """
    Checks if the answer is a valid 11-letter uppercase word.
    Args:
        answer (str): The answer to check.
    Returns:
        bool: True if valid, False otherwise.
    """
    if not isinstance(answer, str):
        return False
    if len(answer) != 11:
        return False
    if not answer.isalpha() or not answer.isupper():
        return False
    return True

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    player.evaluate(failure_num, version, max_turns)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(
        args[0], 
        args[1], 
        args[2], 
        args[3], 
        int(args[4]), 
        args[5], 
        args[6], 
        int(args[7]), 
        args[8], 
        int(args[9]), 
        int(args[10]), 
        args[11], 
        bool(eval(args[12]))
    )