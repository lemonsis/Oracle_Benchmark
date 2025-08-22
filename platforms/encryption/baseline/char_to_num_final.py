import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM
import logging

def blackbox(plaintext):
   ciphertext = []
   for char in plaintext:
        if 'a' <= char <= 'z':
            ciphertext.append(str(ord(char) - ord('a') + 1) + " ")
        elif 'A' <= char <= 'Z':
            ciphertext.append(str(ord(char) - ord('A') + 1) + " ")
        else:
            ciphertext.append(char)
   return "".join(ciphertext).strip()

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    blackbox_output = f'You have {max_turns} interaction turns to understand the black-box. Now the interaction starts. Only output the value and DO NOT contain any unrelated text.'
    for i in range(max_turns+1):
        player_output = player.normal_output(blackbox_output)
        # Only take the first line of output, strip whitespace
        if isinstance(player_output, str):
            player_output = player_output.strip().split('\n')[0]
        else:
            player_output = str(player_output).strip().split('\n')[0]
        # Only keep letters and spaces, as per the rules
        filtered_player_output = ''.join([ch for ch in player_output if ch.isalpha() or ch == ' '])
        blackbox_output = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> ' + blackbox(filtered_player_output)
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
    #main('qwen', 'qwq-plus', 'encryption', 'normal', 1, 'baseline', 'char_to_num', 0, 'history', 12, 1, 'evaluate', True)