import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM

def blackbox(truth, query):
    """
    truth: str, e.g. "HAPPY,APPLE,GRAPE,STORM"
    query: str, e.g. "ANGRY"
    Returns: str, e.g. "MXXXA,AXXXX,MXXMX,XXXAX"
    """
    # Validate truth
    if not isinstance(truth, str):
        return "Truth must be a string of four 8-letter uppercase words separated by commas."
    truths = [w.strip() for w in truth.split(',')]
    if len(truths) != 4 or not all(len(w) == 8 and w.isupper() and w.isalpha() for w in truths):
        return "Truth must be four 8-letter uppercase words separated by commas."
    # Validate query
    if not isinstance(query, str):
        return "Query must be a single 8-letter uppercase word."
    query = query.strip()
    if len(query) != 8 or not query.isupper() or not query.isalpha():
        return "Query must be a single 8-letter uppercase word (A-Z)."
    feedbacks = []
    for word in truths:
        fb = ['X'] * 8
        word_chars = list(word)
        query_chars = list(query)
        used_in_word = [False] * 8
        used_in_query = [False] * 8
        # First pass: correct position
        for i in range(8):
            if query_chars[i] == word_chars[i]:
                fb[i] = 'A'
                used_in_word[i] = True
                used_in_query[i] = True
        # Second pass: misplaced
        for i in range(8):
            if fb[i] == 'A':
                continue
            for j in range(8):
                if not used_in_word[j] and not used_in_query[i] and query_chars[i] == word_chars[j]:
                    fb[i] = 'M'
                    used_in_word[j] = True
                    used_in_query[i] = True
                    break
        feedbacks.append(''.join(fb))
    return ','.join(feedbacks)

def check_answer_format(answer):
    """
    answer: str, e.g. "HAPPY,APPLE,GRAPE,STORM"
    Returns: True if format is correct, else False
    """
    if not isinstance(answer, str):
        return False
    words = [w.strip() for w in answer.split(',')]
    if len(words) != 4:
        return False
    for w in words:
        if len(w) != 8 or not w.isupper() or not w.isalpha():
            return False
    return True

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    player.evaluate(failure_num, version, max_turns)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))