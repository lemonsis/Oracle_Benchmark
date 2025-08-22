import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM

def blackbox(plaintext):
    # RSA parameters
    e = 13
    n = 713

    # Remove spaces and make case-insensitive
    filtered = ''.join([c for c in plaintext if c.isalpha()]).upper()

    # Map letter to number: A=1, ..., Z=26
    def letter_to_num(c):
        return ord(c) - ord('A') + 1

    if not filtered:
        return ''

    nums = [letter_to_num(c) for c in filtered]

    # Split into blocks of 2
    blocks = []
    i = 0
    while i < len(nums):
        if i+1 < len(nums):
            # Hexavigesimal: 26*first + second
            block_val = nums[i]*26 + nums[i+1]
            blocks.append(block_val)
            i += 2
        else:
            # Last single letter: treat as 26*val (second is 0)
            block_val = nums[i]*26
            blocks.append(block_val)
            i += 1

    # RSA encryption: c = m^e mod n
    ciphertext_blocks = []
    for m in blocks:
        c = pow(m, e, n)
        ciphertext_blocks.append(str(c))

    ciphertext = ','.join(ciphertext_blocks)
    return ciphertext

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    blackbox_output = f'You have {max_turns} interaction turns to understand the black-box. Now the interaction starts. Only output the value and DO NOT contain any unrelated text.'
    for i in range(max_turns+1):
        player_output = player.normal_output(blackbox_output)
        # Only pass the player's output (plaintext) to blackbox, strip whitespace and only take the first line
        blackbox_input = player_output.strip().split('\n')[0]
        blackbox_result = blackbox(blackbox_input)
        blackbox_output = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> {blackbox_result}'
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))