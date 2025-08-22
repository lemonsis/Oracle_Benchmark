import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM

def blackbox(plaintext):
    # Helper: map letter to value (A-Z:0-25, a-z:26-51)
    def letter_to_value(ch):
        if 'A' <= ch <= 'Z':
            return ord(ch) - ord('A')
        elif 'a' <= ch <= 'z':
            return ord(ch) - ord('a') + 26
        else:
            return None

    # Helper: map value to letter
    def value_to_letter(val):
        if 0 <= val <= 25:
            return chr(val + ord('A'))
        elif 26 <= val <= 51:
            return chr(val - 26 + ord('a'))
        else:
            return None

    # Preference order: A-Z, a-z
    preference_order = [chr(i) for i in range(ord('A'), ord('Z')+1)] + [chr(i) for i in range(ord('a'), ord('z')+1)]

    ciphertext = ""
    prev_letters = ['H']  # p_0 = 'H'

    for idx, ch in enumerate(plaintext):
        if not (('A' <= ch <= 'Z') or ('a' <= ch <= 'z')):
            # Keep blank spaces in the ciphertext
            ciphertext += ch
            continue

        # Build frequency for p_0...p_{i-1}
        freq_window = {}
        for l in prev_letters:
            freq_window[l] = freq_window.get(l, 0) + 1

        max_freq = max(freq_window.values())
        # Get all letters with max_freq
        candidates = [l for l in preference_order if freq_window.get(l, 0) == max_freq]
        # Pick the first in preference order
        shift_letter = candidates[0]
        shift_value = letter_to_value(shift_letter)

        # Encrypt current letter
        p_value = letter_to_value(ch)
        c_value = (p_value + shift_value) % 52
        c_letter = value_to_letter(c_value)
        ciphertext += c_letter

        prev_letters.append(ch)

    return ciphertext

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    blackbox_output = f'You have {max_turns} interaction turns to understand the black-box. Now the interaction starts. Only output the value and DO NOT contain any unrelated text.'
    for i in range(max_turns+1):
        player_output = player.normal_output(blackbox_output)
        # Only use the value part of the player's output (strip whitespace and remove all non-letter and non-space chars)
        player_output = ''.join([c for c in player_output.strip() if (('A' <= c <= 'Z') or ('a' <= c <= 'z') or c == ' ')])
        blackbox_output = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> ' + blackbox(player_output)
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))