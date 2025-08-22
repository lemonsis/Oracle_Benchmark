
import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM

def blackbox(
    last_turn_result,
    my_bullets,
    opp_bullets_public,  # None unless scouted last turn
    turn_id,
    total_turns,
    max_bullets=8
):
    """
    Fixed adversarial strategy for Load Shoot Defend Scout.
    last_turn_result: dict with keys: 'my_action', 'opp_action', 'my_score', 'opp_score', 'opp_shot', 'opp_defended', 'scouted_bullets'
    my_bullets: int, my current bullet count
    opp_bullets_public: int or None, opponent's bullet count if scouted last turn, else None
    turn_id: int, current turn (0-based)
    total_turns: int, total number of turns in the game
    max_bullets: int, maximum bullets can be held
    """
    # State for strategy
    # We need to know if opponent has shot yet, and if so, when to switch to shoot mode
    # We'll use a static variable to store state across calls
    if not hasattr(blackbox, "mode"):
        blackbox.mode = "load"
        blackbox.load_turns = 0
        blackbox.opp_shot = False
        blackbox.cycle = 0  # 0: load, 1: shoot
    # Reset at game start
    if turn_id == 0:
        blackbox.mode = "load"
        blackbox.load_turns = 0
        blackbox.opp_shot = False
        blackbox.cycle = 0

    # Determine how many initial load turns
    initial_load = 3 if total_turns < 10 else 6

    # Check if opponent shot last turn
    if last_turn_result is not None:
        if last_turn_result.get("opp_action", "").startswith("shoot"):
            blackbox.opp_shot = True

    # If in load phase
    if blackbox.cycle == 0:
        # If in initial load turns
        if blackbox.load_turns < initial_load and blackbox.opp_shot == False:
            
            if my_bullets < max_bullets:
                blackbox.load_turns += 1
                return "load"
            else:
                blackbox.cycle = 1
                if my_bullets >= 2:
                    return "shoot 2"
                elif my_bullets == 1:
                    return "shoot 1"
                else:
                    blackbox.load_turns += 1
                    return "load"
        elif blackbox.load_turns < initial_load and blackbox.opp_shot:
            # If opponent shot during initial load, switch to shoot mode immediately
            blackbox.cycle = 1
            if my_bullets >= 2:
                return "shoot 2"
            elif my_bullets == 1:
                return "shoot 1"
            else:
                blackbox.load_turns += 1
                return "load"
        else:
            # After initial load turns, if opponent never shot during our load, keep loading until opponent shoots or we have 8 bullets
            if not blackbox.opp_shot and my_bullets < max_bullets:
                blackbox.load_turns += 1
                return "load"
            else:
                blackbox.cycle = 1
                if my_bullets >= 2:
                    return "shoot 2"
                elif my_bullets == 1:
                    return "shoot 1"
                else:
                    blackbox.load_turns += 1
                    return "load"
    # If in shoot phase
    if blackbox.cycle == 1:
        if my_bullets >= 2:
            return "shoot 2"
        elif my_bullets == 1:
            return "shoot 1"
        else:
            blackbox.cycle = 0
            blackbox.opp_shot = False
            blackbox.load_turns = 0
            return "load"
    # Fallback
    return "load"

def platform(settings, player):
    """
    Judger for Load Shoot Defend Scout.
    settings: dict, must contain 'total_turns' (int)
    player: ReasoningLLM instance with .normal_output(str) method
    Returns: int, score of player (not blackbox)
    """
    total_turns = settings.get("total_turns")
    max_bullets = 8
    # Only total_turns is public
    public_settings = {"total_turns": total_turns}

    # Game state
    p1_bullets = 0  # blackbox
    p2_bullets = 0  # player
    p1_score = 0
    p2_score = 0
    last_turn_result = None
    last_turn_result_p2 = None
    opp_bullets_public_p1 = None
    opp_bullets_public_p2 = None

    for turn_id in range(total_turns):
        # Prepare info for blackbox
        blackbox_input = (
            last_turn_result,
            p1_bullets,
            opp_bullets_public_p1,
            turn_id,
            total_turns,
            max_bullets
        )
        # Prepare info for player (natural language)
        if last_turn_result_p2 is None:
            last_result_str = "This is the first turn."
        else:
            last_result_str = (
                f"Last turn, you chose '{last_turn_result_p2['my_action']}', "
                f"your opponent chose '{last_turn_result_p2['opp_action']}'. "
                f"Your score: {last_turn_result_p2['my_score']}, "
                f"opponent's score: {last_turn_result_p2['opp_score']}."
            )
            if last_turn_result_p2.get("scouted_bullets") is not None:
                last_result_str += f" You scouted and saw your opponent had {last_turn_result_p2['scouted_bullets']} bullets."
        state_str = (
            f"Turn {turn_id+1} of {total_turns}. "
        )
        if opp_bullets_public_p2 is not None:
            state_str += f" You know your opponent has {opp_bullets_public_p2} bullets (from last scout)."
        settings_str = f"Game setting: total_turns = {total_turns}."
        prompt = (
            f"{last_result_str} {state_str} {settings_str} "
        )

        # Get actions
        p1_action = blackbox(*blackbox_input)
        p2_action = player.normal_output(prompt)

        # Validate p2_action
        valid = False
        format_warning = ""
        while not valid:
            p2_action_stripped = p2_action.strip().lower()
            if p2_action_stripped == "load":
                valid = True
            elif p2_action_stripped == "scout":
                valid = True
            elif p2_action_stripped.startswith("shoot "):
                try:
                    x = int(p2_action_stripped.split()[1])
                    if 1 <= x <= p2_bullets:
                        valid = True
                    else:
                        format_warning = f"Invalid shoot: you have {p2_bullets} bullets, but tried to shoot {x}. You can't shoot."
                except:
                    format_warning = "Invalid format for shoot. Use 'shoot x' where x is an integer."
            elif p2_action_stripped.startswith("defend "):
                try:
                    y = int(p2_action_stripped.split()[1])
                    if 1 <= y <= p2_bullets:
                        valid = True
                    else:
                        format_warning = f"Invalid defend: you have {p2_bullets} bullets, but tried to defend {y}."
                except:
                    format_warning = "Invalid format for defend. Use 'defend y' where y is an integer."
            else:
                format_warning = "Invalid action format. Please reply with 'load', 'scout', 'shoot x', or 'defend y'."
            if not valid:
                prompt = (
                    f"{format_warning}. \n Retry. ONLY output the valid action. DO NOT contain any other text or symbols. "
                )
                p2_action = player.normal_output(prompt)

        # Parse actions
        def parse_action(action_str, bullets):
            action = action_str.strip().lower()
            if action == "load":
                return ("load", 0)
            elif action == "scout":
                return ("scout", 0)
            elif action.startswith("shoot "):
                x = int(action.split()[1])
                return ("shoot", x)
            elif action.startswith("defend "):
                y = int(action.split()[1])
                return ("defend", y)
            else:
                return ("invalid", 0)

        p1_type, p1_val = parse_action(p1_action, p1_bullets)
        p2_type, p2_val = parse_action(p2_action, p2_bullets)

        # Update bullets
        # For load/scout: +1 bullet (if not at max)
        # For shoot/defend: -x or -y bullets
        # But must check for max bullets
        if p1_type == "load":
            p1_bullets = min(p1_bullets + 1, max_bullets)
        elif p1_type == "scout":
            p1_bullets = min(p1_bullets + 1, max_bullets)
        elif p1_type == "shoot":
            p1_bullets -= p1_val
        elif p1_type == "defend":
            p1_bullets -= p1_val

        if p2_type == "load":
            p2_bullets = min(p2_bullets + 1, max_bullets)
        elif p2_type == "scout":
            p2_bullets = min(p2_bullets + 1, max_bullets)
        elif p2_type == "shoot":
            p2_bullets -= p2_val
        elif p2_type == "defend":
            p2_bullets -= p2_val

        # Calculate scores
        # Both shoot
        p1_point = 0
        p2_point = 0
        if p1_type == "shoot" and p2_type == "shoot":
            if p1_val > p2_val:
                p1_point = 1
                p2_point = -1
            elif p1_val <  p2_val:
                p2_point = 1
                p1_point = -1
            # else tie, both 0
        # shoot vs defend
        elif p1_type == "shoot" and p2_type == "defend":
            if p2_val >= p1_val:
                p2_point = 1
                p1_point = -1
            elif p2_val < p1_val:
                p1_point = 1
                p2_point = -1
        elif p2_type == "shoot" and p1_type == "defend":
            if p1_val >= p2_val:
                p1_point = 1
                p2_point = -1
            elif p1_val < p2_val:
                p2_point = 1
                p1_point = -1
            # else tie, both 0
        # shoot vs load/scout
        elif p1_type == "shoot" and (p2_type == "load" or p2_type == "scout"):
            p1_point = 1
            p2_point = -1
        elif p2_type == "shoot" and (p1_type == "load" or p1_type == "scout"):
            p2_point = 1
            p1_point = -1
        # defend vs defend: both 0
        # load/scout vs load/scout: both 0

        p1_score += p1_point
        p2_score += p2_point

        # For next turn: if scouted, reveal opponent's bullet count
        opp_bullets_public_p1 = None
        opp_bullets_public_p2 = None
        if p1_type == "scout":
            opp_bullets_public_p1 = p2_bullets
        if p2_type == "scout":
            opp_bullets_public_p2 = p1_bullets

        # Prepare last_turn_result for next turn
        last_turn_result = {
            "my_action": p1_action,
            "opp_action": p2_action,
            "my_score": p1_score,
            "opp_score": p2_score,
            "opp_shot": p2_type == "shoot",
            "opp_defended": p2_type == "defend",
            "scouted_bullets": opp_bullets_public_p1
        }
        last_turn_result_p2 = {
            "my_action": p2_action,
            "opp_action": p1_action,
            "my_score": p2_score,
            "opp_score": p1_score,
            "opp_shot": p1_type == "shoot",
            "opp_defended": p1_type == "defend",
            "scouted_bullets": opp_bullets_public_p2
        }

    return p2_score

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    player.evaluate(failure_num, version, max_turns)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
