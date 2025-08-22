import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM

def blackbox(truth, query):
    # truth: "Heavy Coin X; Light Coin Y"
    # query: e.g. "Left: Coin 1, Coin 2; Right: Coin 3, Coin 4"
    # returns: "Left", "Right", "Equal", or error string

    # Parse truth
    try:
        truth = truth.strip()
        if not truth.startswith("Heavy Coin ") or "; Light Coin " not in truth:
            return "Truth format error. Should be 'Heavy Coin X; Light Coin Y'."
        heavy_part, light_part = truth.split("; Light Coin ")
        heavy_coin = int(heavy_part.replace("Heavy Coin ", "").strip())
        light_coin = int(light_part.strip())
        if not (1 <= heavy_coin <= 152 and 1 <= light_coin <= 152 and heavy_coin != light_coin):
            return "Truth coins must be two different numbers between 1 and 152."
    except Exception:
        return "Truth format error. Should be 'Heavy Coin X; Light Coin Y'."

    # Parse query
    query = query.strip()
    if not (query.startswith("Left:") and "; Right:" in query):
        return "Query format error. Please use 'Left: Coin X, Coin Y; Right: Coin Z, Coin W'."
    try:
        left_part, right_part = query.split("; Right:")
        left_part = left_part[len("Left:"):].strip()
        right_part = right_part.strip()
        # Allow empty sides
        left_coins = [c.strip() for c in left_part.split(",") if c.strip()] if left_part else []
        right_coins = [c.strip() for c in right_part.split(",") if c.strip()] if right_part else []
        # Validate coin names
        valid_names = {f"Coin {i}" for i in range(1, 153)}
        for c in left_coins + right_coins:
            if c not in valid_names:
                return f"Invalid coin name '{c}'. Use 'Coin 1' to 'Coin 152'."
        # Check for duplicate coins in both sides
        if set(left_coins) & set(right_coins):
            return "A coin cannot be on both sides of the scale."
    except Exception:
        return "Query format error. Please use 'Left: Coin X, Coin Y; Right: Coin Z, Coin W'."

    # Compute weights
    def coin_weight(coin_name):
        num = int(coin_name.replace("Coin ", ""))
        if num == heavy_coin:
            return 1.1
        elif num == light_coin:
            return 0.9
        else:
            return 1.0

    left_weight = sum(coin_weight(c) for c in left_coins)
    right_weight = sum(coin_weight(c) for c in right_coins)

    if abs(left_weight - right_weight) < 1e-8:
        return "Equal"
    elif left_weight > right_weight:
        return "Left"
    else:
        return "Right"

def check_answer_format(answer):
    # Should be "Heavy Coin X; Light Coin Y" where X and Y are different integers 1-152
    answer = answer.strip()
    if not answer.startswith("Heavy Coin ") or "; Light Coin " not in answer:
        return False
    try:
        heavy_part, light_part = answer.split("; Light Coin ")
        heavy_coin = int(heavy_part.replace("Heavy Coin ", "").strip())
        light_coin = int(light_part.strip())
        if not (1 <= heavy_coin <= 152 and 1 <= light_coin <= 152):
            return False
        if heavy_coin == light_coin:
            return False
    except Exception:
        return False
    return True

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    player.evaluate(failure_num, version, max_turns)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))