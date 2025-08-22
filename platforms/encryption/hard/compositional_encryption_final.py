
import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM

def blackbox(plaintext):
    # Keyword for polyalphabetic substitution
    keyword = 'LOVE'
    keyword_len = len(keyword)
    # Fixed permutation table (0-25 permutation)
    permutation_table = [
        7, 24, 2, 18, 12, 0, 22, 9, 16, 3, 25, 5, 20, 1, 14, 21, 6, 11, 8, 23, 19, 4, 13, 17, 10, 15
    ]
    ciphertext = ''
    letter_idx = 0  # Only incremented for letters, not spaces or non-letters
    for ch in plaintext:
        if ch == ' ':
            ciphertext += ' '
            continue
        if ch.isalpha():
            # Step 1: Letter to Number (a/A=0, ..., z/Z=25)
            p_i = ord(ch.lower()) - ord('a')
            # Step 2: Get keyword character and its value
            j = letter_idx % keyword_len
            k_j = ord(keyword[j].lower()) - ord('a')
            # Step 3: Polyalphabetic Substitution
            s1_i = (p_i + k_j) % 26
            # Step 4: Affine Transformation
            s2_i = (3 * s1_i + 10) % 26
            # Step 5: Fixed Permutation
            s3_i = permutation_table[s2_i]
            # Step 6: Number to Letter (preserve case)
            if ch.isupper():
                c_i = chr(ord('A') + s3_i)
            else:
                c_i = chr(ord('a') + s3_i)
            ciphertext += c_i
            letter_idx += 1
        else:
            # Ignore non-letter, non-space characters
            continue
    return ciphertext

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    blackbox_output = f'You have {max_turns} interaction turns to understand the black-box. Now the interaction starts. Only output the value and DO NOT contain any unrelated text.'
    for i in range(max_turns+1):
        player_output = player.normal_output(blackbox_output)
        # Only pass the player's output as plaintext to blackbox, stripping leading/trailing whitespace
        # FIX: Only pass the value, not the whole message, in case the model outputs extra text
        # Only keep English letters and spaces
        plaintext = ''.join([ch for ch in player_output.strip() if ch.isalpha() or ch == ' '])
        blackbox_output = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> ' + blackbox(plaintext)
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
