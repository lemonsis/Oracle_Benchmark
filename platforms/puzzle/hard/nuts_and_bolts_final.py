
import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM

def blackbox(truth, query):
    # truth: e.g. "Nut 1, Nut 3, Nut 2, Nut 5, Nut 4, Nut 6, Nut 7, Nut 8"
    # query: e.g. "Bolt 1, Nut 2; Bolt 2, Nut 3; Bolt 3, Nut 1"
    # returns: e.g. "small; large; equal"
    # Validate query format
    if not isinstance(query, str):
        return "Query must be a string."
    parts = [x.strip() for x in query.split(';')]
    if len(parts) != 3:
        return "Query must contain exactly 3 bolt-nut pairs separated by ';'."
    bolt_set = set()
    nut_set = set()
    for part in parts:
        items = [x.strip() for x in part.split(',')]
        if len(items) != 2:
            return "Each pair must be in the format 'Bolt X, Nut Y'."
        bolt, nut = items
        if not bolt.startswith("Bolt ") or not nut.startswith("Nut "):
            return "Each pair must be in the format 'Bolt X, Nut Y'."
        try:
            bolt_num = int(bolt[5:])
            nut_num = int(nut[4:])
        except ValueError:
            return "Bolt and Nut numbers must be integers."
        if not (1 <= bolt_num <= 8) or not (1 <= nut_num <= 8):
            return "Bolt and Nut numbers must be between 1 and 8."
        bolt_set.add(bolt_num)
        nut_set.add(nut_num)
    # Prepare the mapping from Bolt i to Nut j
    # truth: "Nut 1, Nut 3, Nut 2, Nut 5, Nut 4, Nut 6, Nut 7, Nut 8"
    truth_nuts = [int(x.strip()[4:]) for x in truth.split(',')]
    # truth_nuts[i] is the nut number that matches Bolt i+1
    feedback = []
    for part in parts:
        bolt, nut = [x.strip() for x in part.split(',')]
        bolt_num = int(bolt[5:])
        nut_num = int(nut[4:])
        correct_nut = truth_nuts[bolt_num - 1]
        if nut_num < correct_nut:
            feedback.append("small")
        elif nut_num > correct_nut:
            feedback.append("large")
        else:
            feedback.append("equal")
    return "; ".join(feedback)

def check_answer_format(answer):
    # answer: e.g. "Nut 1, Nut 3, Nut 2, Nut 5, Nut 4, Nut 6, Nut 7, Nut 8"
    if not isinstance(answer, str):
        return False
    items = [x.strip() for x in answer.split(',')]
    if len(items) != 8:
        return False
    seen = set()
    for item in items:
        if not item.startswith("Nut "):
            return False
        try:
            num = int(item[4:])
        except ValueError:
            return False
        if not (1 <= num <= 8):
            return False
        if num in seen:
            return False
        seen.add(num)
    return True

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    player.evaluate(failure_num, version, max_turns)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
