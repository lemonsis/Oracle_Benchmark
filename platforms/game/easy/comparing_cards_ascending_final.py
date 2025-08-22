
import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM

def blackbox(last_result, my_hand, opp_hand, played_cards, total_cards):
    """
    Fixed adversarial strategy for Comparing Cards:
    - First play the highest card (total_cards).
    - Then play cards in ascending order (1, 2, ..., total_cards-1).
    Args:
        last_result: dict or None, result of last turn (not used in this strategy)
        my_hand: list of int, cards currently in blackbox's hand
        opp_hand: list of int, cards currently in opponent's hand (not used)
        played_cards: list of tuples, history of played cards (not used)
        total_cards: int, total number of cards at start
    Returns:
        str: action in format 'card x'
    """
    # If still have the highest card, play it
    if total_cards in my_hand:
        return f"card {total_cards}"
    # Otherwise, play the lowest available card
    card_to_play = min(my_hand)
    return f"card {card_to_play}"

def platform(settings, player):
    """
    Judger for Comparing Cards.
    Args:
        settings: dict, must contain 'total_cards' (int)
        player: ReasoningLLM instance with .normal_output(str) method
    Returns:
        float: score of player
    """
    # Extract settings
    if 'total_cards' not in settings:
        raise ValueError("settings must contain 'total_cards'")
    total_cards = settings['total_cards']
    # Initialize hands
    blackbox_hand = list(range(1, total_cards+1))
    player_hand = list(range(1, total_cards+1))
    # For history
    played_cards = []
    player_score = 0.0
    last_result = None

    for turn in range(total_cards):
        # Prepare info for both players
        # For blackbox: pass last_result, my_hand, opp_hand, played_cards, total_cards
        blackbox_input = (
            last_result,
            blackbox_hand.copy(),
            player_hand.copy(),
            played_cards.copy(),
            total_cards
        )
        # For player: natural language string
        player_info = (
            f"Turn {turn+1} of {total_cards}.\n"
            f"Your current hand: {sorted(player_hand)}.\n"
            f"Opponent's remaining cards: {len(blackbox_hand)} cards (numbers unknown).\n"
            f"Last turn's result: {last_result if last_result is not None else 'N/A'}.\n"
            f"Game: Comparing Cards. Each turn, play a card from your hand in the format 'card x', where x is a number in your hand. "
            f"The player with the higher card gets 1 point, tie gives 0 each, lose gives -1. Cards are numbered 1 to {total_cards}. "
            f"Once a card is played, it cannot be used again. Try to maximize your score."
        )

        # Get actions
        blackbox_action = blackbox(*blackbox_input)
        player_action = player.normal_output(player_info)

        # Validate player action
        valid = False
        while not valid:
            # Check format: must be 'card x' where x is int in player_hand
            if isinstance(player_action, str):
                parts = player_action.strip().split()
                if len(parts) == 2 and parts[0].lower() == 'card':
                    try:
                        card_num = int(parts[1])
                        if card_num in player_hand:
                            valid = True
                        else:
                            player_action = player.normal_output(
                                f"Invalid action: You do not have card {card_num} in your hand. "
                                f"Your current hand: {sorted(player_hand)}. "
                                f"Please respond with your action in the format 'card x', where x is a number in your hand."
                            )
                    except ValueError:
                        player_action = player.normal_output(
                            f"Invalid action format: '{player_action}'. "
                            f"Please respond with your action in the format 'card x', where x is a number in your hand. "
                            f"Your current hand: {sorted(player_hand)}."
                        )
                else:
                    player_action = player.normal_output(
                        f"Invalid action format: '{player_action}'. "
                        f"Please respond with your action in the format 'card x', where x is a number in your hand. "
                        f"Your current hand: {sorted(player_hand)}."
                    )
            else:
                player_action = player.normal_output(
                    f"Invalid action type. Please respond with your action in the format 'card x', where x is a number in your hand. "
                    f"Your current hand: {sorted(player_hand)}."
                )

        # Parse actions
        blackbox_card = int(blackbox_action.strip().split()[1])
        player_card = int(player_action.strip().split()[1])

        # Remove played cards from hands
        blackbox_hand.remove(blackbox_card)
        player_hand.remove(player_card)

        # Determine result
        if player_card > blackbox_card:
            player_score += 1.0
            turn_result = {
                "player_card": player_card,
                "opponent_card": blackbox_card,
                "result": "win",
                "player_point": 1.0,
                "opponent_point": -1.0
            }
        elif player_card < blackbox_card:
            player_score -= 1.0
            turn_result = {
                "player_card": player_card,
                "opponent_card": blackbox_card,
                "result": "lose",
                "player_point": -1.0,
                "opponent_point": 1.0
            }
        else:
            player_score += 0
            turn_result = {
                "player_card": player_card,
                "opponent_card": blackbox_card,
                "result": "tie",
                "player_point": 0,
                "opponent_point": 0
            }
        played_cards.append((player_card, blackbox_card))
        last_result = turn_result

    return player_score

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    player.evaluate(failure_num, version, max_turns)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
