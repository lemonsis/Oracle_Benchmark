import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM

def blackbox(plaintext):
    # Mapping for 1,2,4,8 combinations for numbers 1-26
    # Precompute the minimal digit representation for each number 1-26
    # Use larger numbers first, and put small number in the front
    # Only use 1,2,4,8 as building blocks, can use each multiple times
    # For each number, find the minimal digit representation (fewest digits, then smallest lexicographically)
    from collections import deque

    # Precompute for 1-26
    building_blocks = [8, 4, 2, 1]
    num_to_code = {}

    for n in range(1, 27):
        # BFS to find minimal digit representation
        queue = deque()
        queue.append( ([], 0) )  # (current list of blocks, current sum)
        visited = set()
        found = None
        min_len = float('inf')
        while queue:
            blocks, s = queue.popleft()
            if s == n:
                # Compose code: sort blocks ascending, join as string
                code = ''.join(str(b) for b in sorted(blocks))
                if (found is None) or (len(code) < min_len) or (len(code) == min_len and code < found):
                    found = code
                    min_len = len(code)
                continue
            if s > n:
                continue
            for b in building_blocks:
                new_blocks = blocks + [b]
                new_sum = s + b
                key = (tuple(sorted(new_blocks)), new_sum)
                if key in visited:
                    continue
                visited.add(key)
                queue.append( (new_blocks, new_sum) )
        num_to_code[n] = found

    # Now, process the plaintext
    ciphertext = ''
    for c in plaintext:
        if c == ' ':
            ciphertext += '0'
        elif c.isalpha():
            idx = ord(c.upper()) - ord('A') + 1
            ciphertext += num_to_code[idx]
        # Ignore non-letter, non-space characters
    return ciphertext

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
