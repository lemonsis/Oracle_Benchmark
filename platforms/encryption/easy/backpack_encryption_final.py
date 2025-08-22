import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM

def blackbox(plaintext):
    # Public key for backpack encryption
    public_key = [34, 51, 58, 11, 35]  # length 5
    ciphertext_list = []
    for char in plaintext:
        if char.isalpha():
            idx = ord(char.lower()) - ord('a')
            if 0 <= idx <= 25:
                bin_str = format(idx, '05b')
                cipher_val = sum(public_key[j] * int(bin_str[j]) for j in range(5))
                ciphertext_list.append(str(cipher_val))
            else:
                continue
        else:
            continue
    ciphertext = ','.join(ciphertext_list)
    return ciphertext

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    blackbox_output = f'You have {max_turns} interaction turns to understand the black-box. Now the interaction starts. Only output the value and DO NOT contain any unrelated text.'
    for i in range(max_turns+1):
        player_output = player.normal_output(blackbox_output)
        # Only pass the player's output (plaintext) to blackbox, strip whitespace
        # FIX: Only keep English letters, remove all other characters (including spaces)
        blackbox_input = ''.join([c for c in player_output.strip() if c.isalpha()])
        blackbox_cipher = blackbox(blackbox_input)
        blackbox_output = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> {blackbox_cipher}'
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
