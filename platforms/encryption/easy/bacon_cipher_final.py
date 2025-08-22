import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM

def blackbox(plaintext):
    # Bacon's cipher variant: 5-bit binary for A-Z, X/Y for uppercase, x/y for lowercase
    # A-M: 0-12 (XXXXX to XYYXX), N-Z: 13-25 (YXXYY to YYYYY, i.e. 19-31)
    # Only letters are encoded, spaces are ignored
    # Case-sensitive: output X/Y for uppercase, x/y for lowercase

    def letter_to_bacon_index(ch):
        if ch.isupper():
            return ord(ch) - ord('A')
        elif ch.islower():
            return ord(ch) - ord('a')
        else:
            return None

    bacon_map = {}
    # A-M: 0-12 -> 00000 to 01100
    for i in range(13):
        bits = f"{i:05b}"
        bacon_map[i] = bits
    # N-Z: 13-25 -> 19-31 (10011 to 11111)
    for i, idx in enumerate(range(13, 26)):
        bits = f"{19 + i:05b}"
        bacon_map[idx] = bits

    ciphertext = ""
    for ch in plaintext:
        if ch.isalpha():
            idx = letter_to_bacon_index(ch)
            if idx is None or idx not in bacon_map:
                continue
            bits = bacon_map[idx]
            if ch.isupper():
                code = ''.join('X' if b == '0' else 'Y' for b in bits)
            else:
                code = ''.join('x' if b == '0' else 'y' for b in bits)
            ciphertext += code
        # Ignore non-letters (including spaces)
    return ciphertext

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    blackbox_output = f'You have {max_turns} interaction turns to understand the black-box. Now the interaction starts. Only output the value and DO NOT contain any unrelated text.'
    for i in range(max_turns+1):
        player_output = player.normal_output(blackbox_output)
        # Only use the value part of the output (strip any whitespace)
        if isinstance(player_output, str):
            # Only keep the first line and strip whitespace
            player_output = player_output.strip().split('\n')[0]
            # Remove any non-letter and non-space characters
            player_output = ''.join([c for c in player_output if c.isalpha() or c == ' '])
        blackbox_output = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> ' + blackbox(player_output)
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
