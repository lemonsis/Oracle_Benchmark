
import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM

def blackbox(plaintext):
    # Define the mapping: a-z -> 0-25, A-Z -> 26-51
    def char_to_num(c):
        if 'a' <= c <= 'z':
            return ord(c) - ord('a')
        elif 'A' <= c <= 'Z':
            return ord(c) - ord('A') + 26
        else:
            return None  # For non-letter, e.g., space

    def num_to_char(n):
        if 0 <= n <= 25:
            return chr(n + ord('a'))
        elif 26 <= n <= 51:
            return chr(n - 26 + ord('A'))
        else:
            return ''  # Should not happen

    # Generate enough Fibonacci numbers
    fib = [1, 1]
    letter_count = sum(1 for c in plaintext if c.isalpha())
    while len(fib) < letter_count:
        fib.append(fib[-1] + fib[-2])

    ciphertext = ''
    fib_idx = 0
    for c in plaintext:
        if c.isalpha():
            num = char_to_num(c)
            shift = fib[fib_idx]
            enc_num = (num + shift) % 52
            ciphertext += num_to_char(enc_num)
            fib_idx += 1
        else:
            ciphertext += c  # Keep non-letters (e.g., spaces) as is
    return ciphertext

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    blackbox_output = f'You have {max_turns} interaction turns to understand the black-box. Now the interaction starts. Only output the value and DO NOT contain any unrelated text.'
    for i in range(max_turns+1):
        player_output = player.normal_output(blackbox_output)
        blackbox_output = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> ' + blackbox(player_output)
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
    # main('gpt', 'gpt-4o-mini', 'encryption', 'normal', 1, 'easy', 'fib_cipher', 0, 'logs', 5, 1, 'generate', False)