import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM

def blackbox(plaintext):
    # Positional keyword cipher with keyword 'Jackal'
    keyword = 'Jackal'
    # Build letter to value and value to letter mappings
    letters = [chr(i) for i in range(ord('A'), ord('Z')+1)] + [chr(i) for i in range(ord('a'), ord('z')+1)]
    letter_to_value = {ch: idx for idx, ch in enumerate(letters)}
    value_to_letter = {idx: ch for idx, ch in enumerate(letters)}
    ciphertext_chars = []
    keyword_len = len(keyword)
    keyword_idx = 0
    for ch in plaintext:
        if ch.isalpha():
            k_ch = keyword[keyword_idx % keyword_len]
            p_val = letter_to_value[ch]
            k_val = letter_to_value[k_ch]
            c_val = (p_val + k_val) % 52
            c_ch = value_to_letter[c_val]
            ciphertext_chars.append(c_ch)
            keyword_idx += 1
        elif ch == ' ':
            ciphertext_chars.append(' ')
    ciphertext = ''.join(ciphertext_chars)
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
