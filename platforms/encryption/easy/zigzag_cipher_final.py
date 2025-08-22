
import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM

def blackbox(plaintext):
    # Remove spaces and non-letter characters, convert to uppercase
    filtered = ''.join([c for c in plaintext if c.isalpha()])
    if not filtered:
        return ''
    rows = ['' for _ in range(3)]
    row = 0
    direction = 1  # 1: down, -1: up
    for c in filtered:
        rows[row] += c
        if row == 0:
            direction = 1
        elif row == 2:
            direction = -1
        row += direction
    ciphertext = ''.join(rows)
    return ciphertext

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    blackbox_output = f'You have {max_turns} interaction turns to understand the black-box. Now the interaction starts. Only output the value and DO NOT contain any unrelated text.'
    for i in range(max_turns+1):
        player_output = player.normal_output(blackbox_output)
        # Only use the player's output as plaintext, strip any leading/trailing whitespace and take only the first line
        plaintext = player_output.strip().split('\n')[0]
        blackbox_cipher = blackbox(plaintext)
        blackbox_output = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> {blackbox_cipher}'
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
