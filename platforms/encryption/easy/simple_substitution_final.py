import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM

def blackbox(plaintext):
    # Simple substitution cipher mapping
    lower_src = 'abcdefghijklmnopqrstuvwxyz'
    lower_dst = 'phqgiumeaylnofdxjkrcvstzwb'
    upper_src = lower_src.upper()
    upper_dst = lower_dst.upper()
    lower_map = {src: dst for src, dst in zip(lower_src, lower_dst)}
    upper_map = {src: dst for src, dst in zip(upper_src, upper_dst)}
    ciphertext = ''
    for ch in plaintext:
        if ch in lower_map:
            ciphertext += lower_map[ch]
        elif ch in upper_map:
            ciphertext += upper_map[ch]
        elif ch == ' ':
            ciphertext += ' '
        # Ignore any other characters (as per instruction: only English letters and spaces)
    return ciphertext

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    blackbox_output = f'You have {max_turns} interaction turns to understand the black-box. Now the interaction starts. Only output the value and DO NOT contain any unrelated text.'
    for i in range(max_turns+1):
        player_output = player.normal_output(blackbox_output)
        # Only keep English letters and spaces from player_output, and remove leading/trailing spaces and split lines
        filtered_player_output = ''.join([ch for ch in player_output if (ch.isalpha() or ch == ' ')])
        filtered_player_output = filtered_player_output.strip()
        blackbox_output = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> ' + blackbox(filtered_player_output)
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
