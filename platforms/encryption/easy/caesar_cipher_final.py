import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM

def blackbox(plaintext):
    ciphertext = ''
    for c in plaintext:
        if 'A' <= c <= 'Z':
            shifted = chr((ord(c) - ord('A') + 8) % 26 + ord('A'))
            ciphertext += shifted
        elif 'a' <= c <= 'z':
            shifted = chr((ord(c) - ord('a') + 8) % 26 + ord('a'))
            ciphertext += shifted
        # Ignore non-letters (including spaces)
    return ciphertext

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    blackbox_output = f'You have {max_turns} interaction turns to understand the black-box. Now the interaction starts. Only output the value and DO NOT contain any unrelated text.'
    for i in range(max_turns+1):
        player_output = player.normal_output(blackbox_output)
        # Only keep letters (A-Z, a-z) and spaces from player_output
        filtered_player_output = ''.join([ch for ch in player_output if ch.isalpha() or ch == ' '])
        # Remove spaces before passing to blackbox, as blackbox ignores spaces
        blackbox_input = filtered_player_output.replace(' ', '')
        blackbox_cipher = blackbox(blackbox_input)
        # Insert spaces back to match the original positions in filtered_player_output
        cipher_with_spaces = ''
        idx = 0
        for ch in filtered_player_output:
            if ch == ' ':
                cipher_with_spaces += ' '
            else:
                if idx < len(blackbox_cipher):
                    cipher_with_spaces += blackbox_cipher[idx]
                    idx += 1
        blackbox_output = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> ' + cipher_with_spaces
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))