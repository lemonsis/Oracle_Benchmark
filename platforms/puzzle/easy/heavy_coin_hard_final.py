
import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM

import re
import random

def blackbox(truth, query):
    """
    Implements the Heavy Coin blackbox.
    - truth: str, e.g. "Heavy Coin 42"
    - query: str, e.g. "Left: Coin 1, Coin 2; Right: Coin 3, Coin 4"
    Returns: "Balance" or "Imbalance" or error message string.
    """
    # Validate query format
    pattern = r"^Left:\s*((Coin\s\d{1,3}(,\s*)?)*)\s*;\s*Right:\s*((Coin\s\d{1,3}(,\s*)?)*)$"
    match = re.match(pattern, query.strip())
    if not match:
        return "Invalid query format. Please use: 'Left: Coin x, Coin y; Right: Coin a, Coin b' with valid coin numbers (1-100)."

    # Parse coins
    try:
        left_part = query.split(';')[0].replace('Left:', '').strip()
        right_part = query.split(';')[1].replace('Right:', '').strip()
        left_coins = [c.strip() for c in left_part.split(',') if c.strip()]
        right_coins = [c.strip() for c in right_part.split(',') if c.strip()]
    except Exception:
        return "Invalid query format. Please use: 'Left: Coin x, Coin y; Right: Coin a, Coin b'."

    # Check for valid coin names and duplicates
    valid_coin_pattern = r"^Coin\s([1-9][0-9]?|100)$"
    all_coins = set()
    for coin in left_coins + right_coins:
        if not re.match(valid_coin_pattern, coin):
            return "Invalid coin name detected. Use 'Coin X' where X is 1-100."
        if coin in all_coins:
            return "Duplicate coin detected in query. Each coin should appear only once per query."
        all_coins.add(coin)

    # Check for empty sides
    if not left_coins or not right_coins:
        return "Both Left and Right sides must have at least one coin."

    # Check for overlap
    if set(left_coins) & set(right_coins):
        return "A coin cannot be on both sides of the scale in the same query."

    # Determine which coin is heavy
    heavy_coin = truth.replace("Heavy ", "").strip()  # e.g. "Coin 42"

    # Determine the true result
    if heavy_coin in left_coins and heavy_coin not in right_coins:
        true_result = "Imbalance"
    elif heavy_coin in right_coins and heavy_coin not in left_coins:
        true_result = "Imbalance"
    else:
        true_result = "Balance"

    # Simulate lying: 1 in every 10 queries, the scale lies (randomly)
    # To ensure reproducibility, we can use a static counter attribute
    if not hasattr(blackbox, "query_count"):
        blackbox.query_count = 0
    blackbox.query_count += 1

    # Lie on every 10th query (randomly within each block of 10)
    if not hasattr(blackbox, "lie_turn"):
        blackbox.lie_turn = random.randint(1, 10)
    if blackbox.query_count % 10 == 1:
        blackbox.lie_turn = random.randint(1, 10)
    lie_this_turn = (blackbox.query_count % 10 == blackbox.lie_turn % 10)

    if lie_this_turn:
        result = "Balance" if true_result == "Imbalance" else "Imbalance"
    else:
        result = true_result

    return result

def check_answer_format(answer):
    """
    Checks if the answer is in the correct format: 'Heavy Coin X' where X is 1-100.
    Returns True if correct, False otherwise.
    """
    pattern = r"^Heavy Coin ([1-9][0-9]?|100)$"
    return bool(re.match(pattern, answer.strip()))

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    player.evaluate(failure_num, version, max_turns)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
