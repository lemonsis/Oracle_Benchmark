import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM

def blackbox(plaintext):
    # Helper: map letter to value
    def letter_to_value(ch):
        if 'a' <= ch <= 'z':
            return ord(ch) - ord('a')
        elif 'A' <= ch <= 'Z':
            return ord(ch) - ord('A') + 26
        else:
            return None

    # Helper: map value to letter
    def value_to_letter(val):
        if 0 <= val <= 25:
            return chr(val + ord('a'))
        elif 26 <= val <= 51:
            return chr(val - 26 + ord('A'))
        else:
            return ''

    ciphertext = ''
    idx = 0
    for ch in plaintext:
        if ch == ' ':
            ciphertext += ' '
        elif ('a' <= ch <= 'z') or ('A' <= ch <= 'Z'):
            val = letter_to_value(ch)
            shifted_val = (val + idx) % 52
            ciphertext += value_to_letter(shifted_val)
            idx += 1
        else:
            # Ignore non-letter, non-space characters
            pass
    return ciphertext

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    blackbox_output = f'You have {max_turns} interaction turns to understand the black-box. Now the interaction starts. Only output the value and DO NOT contain any unrelated text.'
    for i in range(max_turns+1):
        player_output = player.normal_output(blackbox_output)
        # Only keep the first line and strip whitespace, to ensure only the plaintext is used
        if isinstance(player_output, str):
            # Only keep the first non-empty line that contains only letters and spaces
            lines = [line.strip() for line in player_output.strip().split('\n') if line.strip()]
            valid_line = ''
            for line in lines:
                if all((c.isalpha() or c == ' ') for c in line):
                    valid_line = line
                    break
            player_output = valid_line
        else:
            player_output = str(player_output)
        blackbox_output = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> ' + blackbox(player_output)
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
