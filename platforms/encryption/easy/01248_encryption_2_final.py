import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM

def blackbox(plaintext):
    def letter_to_num(c):
        if c.isalpha():
            return ord(c.lower()) - ord('a') + 1
        return None

    def num_to_01248(n):
        # Decompose n into sum of 8, 4, 2, 1 (use largest first)
        counts = [0, 0, 0, 0]  # [8s, 4s, 2s, 1s]
        for idx, val in enumerate([8, 4, 2, 1]):
            while n >= val:
                n -= val
                counts[idx] += 1
        # Return as 4-digit string: thousands=8s, hundreds=4s, tens=2s, ones=1s
        return f"{counts[0]}{counts[1]}{counts[2]}{counts[3]}"

    ciphertext = ""
    for c in plaintext:
        if c == ' ':
            ciphertext += '0'
        elif c.isalpha():
            n = letter_to_num(c)
            ciphertext += num_to_01248(n)
        # Ignore non-letter, non-space characters
    return ciphertext

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    blackbox_output = f'You have {max_turns} interaction turns to understand the black-box. Now the interaction starts. Only output the value and DO NOT contain any unrelated text.'
    for i in range(max_turns+1):
        player_output = player.normal_output(blackbox_output)
        # Only keep English letters and spaces from player_output
        filtered_player_output = ''.join([ch for ch in player_output if ch.isalpha() or ch == ' '])
        blackbox_output = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> ' + blackbox(filtered_player_output)
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
    # main('deepseek', 'deepseek-reasoner', 'encryption', 'normal', 1, 'easy', '01248_encryption_2', 0, 'history', 10, 1, 'evaluate', False)
