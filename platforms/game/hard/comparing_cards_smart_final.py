
import os
import sys

# Annotations: Add the project's root directory to the system path.
# This is necessary to ensure that the `eva_models` module can be found and imported.
# The path manipulation calculates the root directory based on the current file's location.
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)

from eva_models import ReasoningLLM

def blackbox(turn: int, blackbox_hand: set, player_last_card: int, total_cards: int, strategy_sequence: list) -> (int, list):
    """
    Implements the fixed strategy for the adversarial player in the Comparing Cards game.

    The strategy is as follows:
    1. On the first turn, play the median card.
    2. On subsequent turns, the strategy depends on the opponent's first move compared to the blackbox's median card.
       - If the opponent's first card was less than or equal to the median, play remaining cards in the order:
         [median-1, median-2, ..., 1, median+1, median+2, ..., highest]
       - If the opponent's first card was greater than the median, play remaining cards in the order:
         [median+1, median+2, ..., highest, median-1, median-2, ..., 1]

    Args:
        turn (int): The current turn number (starting from 1).
        blackbox_hand (set): A set of integers representing the cards the blackbox currently holds.
        player_last_card (int): The card played by the opponent in the previous turn. None for the first turn.
        total_cards (int): The total number of cards each player starts with.
        strategy_sequence (list): The predetermined sequence of cards to play. This is None until turn 2.

    Returns:
        tuple[int, list]: A tuple containing the card to be played and the updated strategy sequence.
    """
    # Annotations: Calculate the median card value. Integer division is used for both even and odd total_cards.
    median = (total_cards + 1) // 2

    # Annotations: On turn 1, the blackbox plays the median card. The strategy sequence is not yet determined.
    if turn == 1:
        return median, None

    # Annotations: On turn 2, determine the strategy sequence based on the player's move in turn 1.
    if strategy_sequence is None:
        # Annotations: Define the two possible playing sequences based on the strategy.
        # Sequence 1: Descending from median-1, then ascending from median+1.
        seq1 = [c for c in range(median - 1, 0, -1)] + [c for c in range(median + 1, total_cards + 1)]
        # Sequence 2: Ascending from median+1, then descending from median-1.
        seq2 = [c for c in range(median + 1, total_cards + 1)] + [c for c in range(median - 1, 0, -1)]

        # Annotations: Choose the sequence based on the opponent's first card.
        if player_last_card <= median:
            strategy_sequence = seq1
        else:
            strategy_sequence = seq2

    # Annotations: For turn 2 and onwards, find the first card in the determined sequence that is still in the hand.
    for card_to_play in strategy_sequence:
        if card_to_play in blackbox_hand:
            # Annotations: Return the chosen card and the established strategy sequence for future turns.
            return card_to_play, strategy_sequence

    # Annotations: Fallback in case of an unexpected state, though this should not be reached with correct logic.
    # It simply plays the smallest available card if no valid move is found in the sequence.
    return sorted(list(blackbox_hand))[0], strategy_sequence


def platform(settings: dict, player: 'ReasoningLLM') -> float:
    """
    Implements the game platform (judger) for the Comparing Cards game.

    This function manages the game flow, interacts with the player and the blackbox,
    validates moves, calculates scores, and returns the final score for the player.

    Args:
        settings (dict): A dictionary containing game settings. Must include 'total_cards'.
        player (ReasoningLLM): An instance of the player model that will interact with the game.

    Returns:
        float: The final score of the player.
    """
    # Annotations: Extract game settings.
    total_cards = settings['total_cards']

    # Annotations: Initialize the game state.
    player_hand = set(range(1, total_cards + 1))
    blackbox_hand = set(range(1, total_cards + 1))
    player_score = 0.0

    # Annotations: Variables to store the state of the last turn for reporting.
    last_player_card = None
    last_turn_summary = "This is the first turn. Let's start the game."

    # Annotations: State variable to hold the blackbox's strategy sequence once determined.
    blackbox_strategy_sequence = None

    # Annotations: The main game loop runs for a number of turns equal to total_cards.
    for turn in range(1, total_cards + 1):
        # Annotations: Construct the prompt for the player, providing all necessary information in natural language.
        player_prompt = f"""
Game: Comparing Cards
Rules: You and an opponent have cards numbered 1 to {total_cards}. Each turn, you both play one card. The player with the higher card gets 1 point. A tie gives 0.5 points to both. The goal is to maximize your total score over {total_cards} turns.

{last_turn_summary}

--- Current State ---
Turn: {turn}/{total_cards}
Your score: {player_score}
Your available cards: {sorted(list(player_hand))}

Please choose a card to play. Your action must be in the format 'card x', where x is a number from your hand.
"""

        # Annotations: Get the blackbox's action by calling its strategy function.
        # The platform passes the current game state to the blackbox.
        bb_card, blackbox_strategy_sequence = blackbox(
            turn=turn,
            blackbox_hand=blackbox_hand,
            player_last_card=last_player_card,
            total_cards=total_cards,
            strategy_sequence=blackbox_strategy_sequence
        )

        # Annotations: Loop to get and validate the player's action.
        while True:
            raw_action = player.normal_output(player_prompt)
            try:
                # Annotations: Check if the action format is correct.
                if not raw_action.strip().lower().startswith('card '):
                    raise ValueError("Invalid format. Please use the format 'card x'.")

                # Annotations: Parse the card number from the action string.
                card_num_str = raw_action.strip().lower().split('card ')[1]
                player_card = int(card_num_str)

                # Annotations: Check if the chosen card is actually in the player's hand.
                if player_card not in player_hand:
                    raise ValueError(f"Card {player_card} is not in your hand. Please choose from your available cards.")

                # Annotations: If all checks pass, the action is valid, so break the loop.
                break
            except (ValueError, IndexError) as e:
                # Annotations: If validation fails, create a new prompt with an error message and ask for input again.
                player_prompt = f"""
Your last action was invalid: {e}
Please try again.

--- Current State ---
Turn: {turn}/{total_cards}
Your score: {player_score}
Your available cards: {sorted(list(player_hand))}

Please choose a card to play in the format 'card x'.
"""

        # Annotations: Update both players' hands by removing the cards that were played.
        player_hand.remove(player_card)
        blackbox_hand.remove(bb_card)

        # Annotations: Determine the outcome of the turn and update the player's score.
        turn_result_str = ""
        if player_card > bb_card:
            player_score += 1.0
            turn_result_str = "You won this turn and got 1 point."
        elif player_card < bb_card:
            player_score -= 1.0
            turn_result_str = "You lost this turn and got 0 points."
        else:  # player_card == bb_card
            player_score += 0.0
            turn_result_str = "This turn was a tie, and you got 0.5 points."

        # Annotations: Prepare the summary of this turn to be shown to the player in the next turn.
        last_turn_summary = f"In turn {turn}, you played {player_card} and the opponent played {bb_card}. {turn_result_str}"
        # Annotations: Store the player's card for the blackbox's logic in the next turn (if it's turn 1).
        last_player_card = player_card

    # Annotations: After all turns are completed, return the player's final score.
    return player_score


def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    """
    The main function to set up and run the evaluation.
    """
    # Annotations: Instantiate the ReasoningLLM class, which represents the player.
    # The player's behavior is determined by the underlying language model specified.
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)

    # Annotations: Start the evaluation process. The `evaluate` method will likely call
    # the `platform` function internally to run the game simulations.
    player.evaluate(failure_num, version, max_turns)

    # Annotations: Save the history of interactions and results to a specified directory.
    player.save_history(output_dir, version)


if __name__ == "__main__":
    # Annotations: This block executes when the script is run directly.
    # It parses command-line arguments to configure the evaluation.
    args = sys.argv[1:]
    # Annotations: Call the main function with arguments provided from the command line.
    # Type conversions are applied as needed (e.g., to int, bool).
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
