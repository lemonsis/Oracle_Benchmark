import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM

def blackbox(plaintext):
    # Vigenere cipher with keyword 'MEMORY'
    keyword = 'MEMORY'
    ciphertext = ''
    # Only process English letters, keep spaces
    # The input is only English letters and blank space (per instruction)
    # Convert to uppercase for case-insensitivity
    plaintext = plaintext.upper()
    keyword = keyword.upper()
    key_len = len(keyword)
    key_indices = [ord(k) - ord('A') for k in keyword]
    j = 0  # index for keyword
    for c in plaintext:
        if c.isalpha():
            shift = key_indices[j % key_len]
            # Shift character
            shifted = (ord(c) - ord('A') + shift) % 26
            ciphertext += chr(shifted + ord('A'))
            j += 1
        elif c == ' ':
            ciphertext += c  # keep spaces
        # Ignore any other characters (should not appear per instruction)
    return ciphertext

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    blackbox_output = f'You have {max_turns} interaction turns to understand the black-box. Now the interaction starts. Only output the value and DO NOT contain any unrelated text.'
    for i in range(max_turns+1):
        player_output = player.normal_output(blackbox_output)
        # Only keep English letters and blank spaces from player_output
        filtered_player_output = ''.join([c for c in player_output if c.isalpha() or c == ' '])
        blackbox_output = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> ' + blackbox(filtered_player_output)
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
