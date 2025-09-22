
import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM

import random
import copy

def blackbox(last_result, my_hand, oppo_played, total_cards):
    """
    last_result: dict or None, e.g. {'my_card': x, 'oppo_card': y, 'result': 1/-1/0}
    my_hand: list of int, cards currently in hand
    oppo_played: list of int, cards opponent has played so far (in order)
    total_cards: int, total number of cards at start
    Returns: str, e.g. "card 5"
    """
    # Arrange all cards ascending, divide into 4 piles a,b,c,d (smallest to largest)
    sorted_cards = list(range(1, total_cards+1))
    n = total_cards
    pile_size = n // 4
    remain = n % 4
    sizes = [pile_size]*4
    for i in range(remain):
        sizes[i] += 1
    a = sorted_cards[:sizes[0]]
    b = sorted_cards[sizes[0]:sizes[0]+sizes[1]]
    c = sorted_cards[sizes[0]+sizes[1]:sizes[0]+sizes[1]+sizes[2]]
    d = sorted_cards[sizes[0]+sizes[1]+sizes[2]:]
    # For each pile, keep the cards that are still in hand
    pile_a = [x for x in a if x in my_hand]
    pile_b = [x for x in b if x in my_hand]
    pile_c = [x for x in c if x in my_hand]
    pile_d = [x for x in d if x in my_hand]
    # Play from b, then d, then a, then c
    if pile_b:
        card = random.choice(pile_b)
    elif pile_d:
        card = random.choice(pile_d)
    elif pile_a:
        card = random.choice(pile_a)
    elif pile_c:
        card = random.choice(pile_c)
    else:
        # Should not happen, but fallback
        card = random.choice(my_hand)
    return f"card {card}"

def platform(settings, player):
    """
    settings: dict, must contain 'total_cards': int
    player: ReasoningLLM instance, must have .normal_output(str) method
    Returns: int, score of player
    """
    # Only 'total_cards' is public
    total_cards = settings['total_cards']
    # Initialize hands
    my_hand = list(range(1, total_cards+1))  # blackbox
    player_hand = list(range(1, total_cards+1))
    # History
    blackbox_played = []
    player_played = []
    # Scores
    player_score = 0
    # For each turn
    last_result = None
    for turn in range(total_cards):
        # Prepare info for blackbox
        blackbox_info = (
            last_result,
            copy.deepcopy(my_hand),
            copy.deepcopy(player_played),
            total_cards
        )
        # Prepare info for player: natural language string
        if last_result is None:
            last_result_str = "This is the first turn."
        else:
            lr = last_result
            if lr['result'] == 1:
                outcome = "You won the last turn."
            elif lr['result'] == -1:
                outcome = "You lost the last turn."
            else:
                outcome = "The last turn was a tie."
            last_result_str = (
                f"Last turn: You played card {lr['player_card']}, "
                f"your opponent played card {lr['oppo_card']}. {outcome}"
            )
        player_hand_str = ", ".join(str(x) for x in sorted(player_hand))
        oppo_played_str = ", ".join(str(x) for x in blackbox_played)
        prompt = (
            f"{last_result_str}\n"
            f"Your current hand: {player_hand_str}.\n"
            f"Opponent has played: {oppo_played_str if oppo_played_str else 'None'}.\n"
            f"Total cards in the game: {total_cards}.\n"
            f"Please choose a card from your hand to play this turn. "
            f"Reply in the format: 'card x', where x is a number in your hand."
        )
        # Get actions
        blackbox_action = blackbox(*blackbox_info)
        player_action = player.normal_output(prompt)
        # Validate player action
        valid = False
        while not valid:
            # Check format: must be "card x" where x is int in player_hand
            if isinstance(player_action, str):
                parts = player_action.strip().lower().split()
                if len(parts) == 2 and parts[0] == "card":
                    try:
                        x = int(parts[1])
                        if x in player_hand:
                            valid = True
                            player_card = x
                        else:
                            warn = (
                                f"Invalid card: {x} is not in your hand. "
                                f"Your hand: {player_hand_str}. "
                                f"Please reply in the format: 'card x', where x is a number in your hand."
                            )
                            player_action = player.normal_output(warn)
                    except:
                        warn = (
                            f"Invalid format. Please reply in the format: 'card x', "
                            f"where x is a number in your hand. Your hand: {player_hand_str}."
                        )
                        player_action = player.normal_output(warn)
                else:
                    warn = (
                        f"Invalid format. Please reply in the format: 'card x', "
                        f"where x is a number in your hand. Your hand: {player_hand_str}."
                    )
                    player_action = player.normal_output(warn)
            else:
                warn = (
                    f"Invalid format. Please reply in the format: 'card x', "
                    f"where x is a number in your hand. Your hand: {player_hand_str}."
                )
                player_action = player.normal_output(warn)
        # Blackbox action is always valid
        blackbox_card = int(blackbox_action.strip().split()[1])
        # Remove played cards from hands
        my_hand.remove(blackbox_card)
        player_hand.remove(player_card)
        blackbox_played.append(blackbox_card)
        player_played.append(player_card)
        # Judge
        if player_card > blackbox_card:
            player_score += 1
            result = 1
        elif player_card < blackbox_card:
            player_score -= 1
            result = -1
        else:
            result = 0
        last_result = {
            'player_card': player_card,
            'oppo_card': blackbox_card,
            'result': result
        }
    return player_score

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    player.evaluate(failure_num, version, max_turns)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
