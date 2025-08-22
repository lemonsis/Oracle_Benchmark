import os
import sys
import random

current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM

def blackbox(truth, query):
    """
    Blackbox for 3 Arm Bandit problem.
    truth: str, either 'Bandit A', 'Bandit B' or 'Bandit C'
    query: str, either ''Bandit A', 'Bandit B' or 'Bandit C', or a final answer
    Returns feedback string or advice if query is invalid.
    """
    valid_bandits = ['Bandit A', 'Bandit B', 'Bandit C']
    query = query.strip()
    # Check if query is a bandit pull
    if query in valid_bandits:
        if truth == 'Bandit A':
            if query == 'Bandit A':
                reward = 1 if random.random() < 0.7 else 0
            elif query == 'Bandit B':
                reward = 1 if random.random() < 0.2 else 0
            else:  # query == 'Bandit C'
                reward = 1 if random.random() < 0.1 else 0
        elif truth == 'Bandit B':
            if query == 'Bandit A':
                reward = 1 if random.random() < 0.2 else 0
            elif query == 'Bandit B':
                reward = 1 if random.random() < 0.7 else 0
            else:  # query == 'Bandit C'
                reward = 1 if random.random() < 0.1 else 0
        else:  # truth == 'Bandit C'
            if query == 'Bandit A':
                reward = 1 if random.random() < 0.1 else 0
            elif query == 'Bandit B':
                reward = 1 if random.random() < 0.2 else 0
            else:
                reward = 1 if random.random() < 0.7 else 0
        return f"Reward: {reward}"
    # Check if query is a final answer
    elif query.startswith('Bandit') and query in valid_bandits:
        return "Please specify if you want to pull or answer."
    elif query in ['A', 'B', 'C']:
        return "Please use the full bandit name: 'Bandit A', 'Bandit B' or 'Bandit C'."
    elif query.lower() in ['bandit a', 'bandit b', 'bandit c']:
        return "Please use the exact format: 'Bandit A', 'Bandit B' or 'Bandit C' (case sensitive)."
    elif query.lower().startswith('pull'):
        return "To pull a bandit, just enter 'Bandit A', 'Bandit B' or 'Bandit C'."
    elif query.lower().startswith('answer'):
        # Try to extract answer
        ans = query[len('answer'):].strip()
        if ans in valid_bandits:
            return "Your answer is noted."
        else:
            return "To answer, just enter 'Bandit A', 'Bandit B' or 'Bandit C' (case sensitive)."
    else:
        return "Invalid query format. Please enter 'Bandit A', 'Bandit B' or 'Bandit C' to pull, or submit your answer as 'Bandit A', 'Bandit B' or 'Bandit C'."

def check_answer_format(answer):
    """
    Checks if the answer is in the correct format: 'Bandit A', 'Bandit B' or 'Bandit C'
    """
    return answer in ['Bandit A', 'Bandit B', 'Bandit C']

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    player.evaluate(failure_num, version, max_turns)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))