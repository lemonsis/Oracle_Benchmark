import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM
import re

def blackbox(truth, query):
    """
    truth: str, e.g. "Row 3" or "Column 2"
    query: str, either a guess of the form "(x, y)" or a final answer of the form "Row X" or "Column Y"
    Returns feedback string.
    """
    # Check if query is a guess of the form "(x, y)"
    query = query.strip()
    coord_pattern = r'^\(\s*([1-9])\s*,\s*([1-9])\s*\)$'
    row_pattern = r'^Row\s+([1-9])$'
    col_pattern = r'^Column\s+([1-9])$'

    if re.match(coord_pattern, query):
        m = re.match(coord_pattern, query)
        x = int(m.group(1))
        y = int(m.group(2))
        # Determine if the truth is a row or column
        if truth.startswith("Row "):
            row_num = int(truth.split()[1])
            if x == row_num:
                return "hit"
            else:
                return "miss"
        elif truth.startswith("Column "):
            col_num = int(truth.split()[1])
            if y == col_num:
                return "hit"
            else:
                return "miss"
        else:
            return "Internal error: invalid truth format."
    elif re.match(row_pattern, query) or re.match(col_pattern, query):
        # This is a final answer, but blackbox only gives feedback to queries, not to final answers
        return "You are submitting a final answer. Please use the answer submission interface."
    else:
        return "Invalid query format. Please guess using coordinates in the form (x, y), where x and y are integers from 1 to 9, e.g., (3, 2)."

def check_answer_format(answer):
    """
    answer: str, should be 'Row X' or 'Column Y' where X or Y is 1-9
    Returns True if format is correct, else False.
    """
    answer = answer.strip()
    if re.fullmatch(r'Row\s+[1-9]', answer):
        return True
    if re.fullmatch(r'Column\s+[1-9]', answer):
        return True
    return False

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    player.evaluate(failure_num, version, max_turns)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))