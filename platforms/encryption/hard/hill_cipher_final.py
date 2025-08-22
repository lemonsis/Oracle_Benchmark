import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM

def blackbox(plaintext):
    # Hill cipher with key matrix [[3,5],[1,2]]
    import string

    key_matrix = [[3, 5], [1, 2]]
    alphabet = string.ascii_lowercase
    letter_to_num = {ch: idx for idx, ch in enumerate(alphabet)}
    num_to_letter = {idx: ch for idx, ch in enumerate(alphabet)}

    # Preprocess: keep only letters, lowercase, but keep spaces in output
    # We'll process blocks of letters, but keep track of spaces to re-insert
    # For simplicity, process letters only, then re-insert spaces at the same positions

    # Record positions of spaces
    space_positions = []
    letters = []
    for idx, ch in enumerate(plaintext):
        if ch.isalpha():
            letters.append(ch.lower())
        elif ch == ' ':
            space_positions.append(len(letters))

    # Pad if needed
    if len(letters) % 2 != 0:
        letters.append('x')

    # Encrypt in blocks of 2
    ciphertext_letters = []
    for i in range(0, len(letters), 2):
        block = letters[i:i+2]
        vec = [letter_to_num[block[0]], letter_to_num[block[1]]]
        # Matrix multiplication mod 26
        c0 = (key_matrix[0][0]*vec[0] + key_matrix[0][1]*vec[1]) % 26
        c1 = (key_matrix[1][0]*vec[0] + key_matrix[1][1]*vec[1]) % 26
        ciphertext_letters.extend([num_to_letter[c0], num_to_letter[c1]])

    # Re-insert spaces at the correct positions
    for pos in space_positions:
        ciphertext_letters.insert(pos, ' ')

    ciphertext = ''.join(ciphertext_letters)
    return ciphertext

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    blackbox_output = f'You have {max_turns} interaction turns to understand the black-box. Now the interaction starts. Only output the value and DO NOT contain any unrelated text.'
    for i in range(max_turns+1):
        player_output = player.normal_output(blackbox_output)
        # Only use the player's output as plaintext, strip any leading/trailing whitespace
        # Only keep letters and spaces, as per the rules
        filtered_plaintext = ''.join([ch for ch in player_output if ch.isalpha() or ch == ' '])
        blackbox_output = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> ' + blackbox(filtered_plaintext)
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
