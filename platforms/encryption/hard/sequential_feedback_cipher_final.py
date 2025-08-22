import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM

def blackbox(plaintext):
    # Mapping: A=0, B=1, ..., Z=25, a=26, ..., z=51
    def char_to_val(c):
        if 'A' <= c <= 'Z':
            return ord(c) - ord('A')
        elif 'a' <= c <= 'z':
            return ord(c) - ord('a') + 26
        else:
            return None  # For non-letter, should not happen

    def val_to_char(v):
        if 0 <= v <= 25:
            return chr(ord('A') + v)
        elif 26 <= v <= 51:
            return chr(ord('a') + (v - 26))
        else:
            return ''  # Should not happen

    ciphertext = ''
    prev_enc_val = char_to_val('b')  # initial hidden letter is 'b'
    for c in plaintext:
        if c == ' ':
            ciphertext += ' '
            continue
        val = char_to_val(c)
        if val is None:
            continue  # skip non-letters, though per spec, input only contains letters
        enc_val = (val + prev_enc_val) % 52
        enc_char = val_to_char(enc_val)
        ciphertext += enc_char
        prev_enc_val = enc_val
    return ciphertext

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    blackbox_output = f'You have {max_turns} interaction turns to understand the black-box. Now the interaction starts. Only output the value and DO NOT contain any unrelated text.'
    for i in range(max_turns+1):
        player_output = player.normal_output(blackbox_output)
        # Only use the first line of output as plaintext, strip whitespace
        if isinstance(player_output, str):
            # Only take the first non-empty line as plaintext
            lines = [line.strip() for line in player_output.split('\n') if line.strip() != '']
            if lines:
                player_output = lines[0]
            else:
                player_output = ''
        else:
            player_output = ''
        # Only keep letters and spaces in player_output
        player_output = ''.join([c for c in player_output if c.isalpha() or c == ' '])
        blackbox_output = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> ' + blackbox(player_output)
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
