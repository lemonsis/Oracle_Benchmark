
import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from ckpt import simulate_circuit
from eva_models import ReasoningLLM
import re

def blackbox(circuit_input):
    # Validate input
    if not isinstance(circuit_input, list) or len(circuit_input) != 8 or any(x not in (0, 1) for x in circuit_input):
        return "Error: Input must be a list of 8 bits (0 or 1)."
    n = 8
    gates = []
    # a[1..8] are input wires (indices 1..8)
    # b[i] = a[i] AND a[n-i+1], for i=1..4
    # c[i] = a[i] OR a[n-i+1], for i=1..4
    # d[i] = b[i] OR (NOT c[i]), for i=1..4
    # e[i] = a[i] AND a[i+n/2], for i=1..4
    # f[i] = a[i] OR a[i+n/2], for i=1..4
    # g[i] = e[i] OR (NOT f[i]), for i=1..4
    # s[0] = 1, s[i] = s[i-1] AND d[i] AND g[i], for i=1..4

    # 1. b[1..4]
    b_indices = []
    for i in range(1, 5):
        # a[i] and a[n-i+1]
        gates.append(('AND', (0, i), (0, n - i + 1)))
        b_indices.append(len(gates))  # 1-based index

    # 2. c[1..4]
    c_indices = []
    for i in range(1, 5):
        gates.append(('OR', (0, i), (0, n - i + 1)))
        c_indices.append(len(gates))

    # 3. NOT c[1..4]
    not_c_indices = []
    for i in range(4):
        gates.append(('NOT', (1, c_indices[i])))
        not_c_indices.append(len(gates))

    # 4. d[1..4] = b[i] OR (NOT c[i])
    d_indices = []
    for i in range(4):
        gates.append(('OR', (1, b_indices[i]), (1, not_c_indices[i])))
        d_indices.append(len(gates))

    # 5. e[1..4] = a[i] AND a[i+4]
    e_indices = []
    for i in range(1, 5):
        gates.append(('AND', (0, i), (0, i + 4)))
        e_indices.append(len(gates))

    # 6. f[1..4] = a[i] OR a[i+4]
    f_indices = []
    for i in range(1, 5):
        gates.append(('OR', (0, i), (0, i + 4)))
        f_indices.append(len(gates))

    # 7. NOT f[1..4]
    not_f_indices = []
    for i in range(4):
        gates.append(('NOT', (1, f_indices[i])))
        not_f_indices.append(len(gates))

    # 8. g[1..4] = e[i] OR (NOT f[i])
    g_indices = []
    for i in range(4):
        gates.append(('OR', (1, e_indices[i]), (1, not_f_indices[i])))
        g_indices.append(len(gates))

    # 9. s[0] = 1 (constant), s[1..4]
    # We'll simulate s[0] as a[1] OR (NOT a[1]) == 1
    gates.append(('NOT', (0, 1)))  # gate N1: NOT a[1]
    not_a1_idx = len(gates)
    gates.append(('OR', (0, 1), (1, not_a1_idx)))  # gate N2: a[1] OR NOT a[1] == 1
    s_indices = [len(gates)]  # s[0] index

    # Now s[i] = s[i-1] AND d[i] AND g[i], for i=1..4
    for i in range(4):
        # temp1 = s[i-1] AND d[i]
        gates.append(('AND', (1, s_indices[-1]), (1, d_indices[i])))
        temp1_idx = len(gates)
        # s[i] = temp1 AND g[i]
        gates.append(('AND', (1, temp1_idx), (1, g_indices[i])))
        s_indices.append(len(gates))

    m = len(gates)
    output = simulate_circuit(n, m, circuit_input, gates)
    # Convert any boolean values to 0/1
    if isinstance(output, list):
        output = [1 if x else 0 for x in output]
    return output

def parse_input_bits(player_output):
    # Accepts a string, tries to extract a list of 8 bits (0/1)
    # Accepts formats like: [0,1,1,0,0,1,0,1] or 0 1 1 0 0 1 0 1 or 01100101
    # Returns list of 8 ints or None
    if isinstance(player_output, list) and len(player_output) == 8 and all(x in (0, 1) for x in player_output):
        return player_output
    # Try to find a list in brackets
    m = re.search(r'\[([01][,\s]*){8}\]', str(player_output))
    if m:
        bits = re.findall(r'[01]', m.group(0))
        if len(bits) == 8:
            return [int(b) for b in bits]
    # Try to find 8 space/comma separated bits
    bits = re.findall(r'[01]', str(player_output))
    if len(bits) == 8:
        return [int(b) for b in bits]
    return None

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    blackbox_output = "Game start: You are interacting with a blackbox boolean circuit. You may submit 8 input bits (0/1) to the circuit each round. Please provide your input as a list of 8 bits (e.g., [0,1,1,0,0,1,0,1])."
    for turn in range(max_turns):
        blackbox_output += f"\n[Round {turn+1}/{max_turns}]"
        player_output = player.normal_output(blackbox_output)
        circuit_input = parse_input_bits(player_output)
        if circuit_input is not None:
            # Valid input, run blackbox
            blackbox_result = blackbox(circuit_input)
            if isinstance(blackbox_result, str):
                # Error from blackbox
                blackbox_output = f"Error: {blackbox_result}\nPlease provide your input as a list of 8 bits (e.g., [0,1,1,0,0,1,0,1])."
            else:
                # Return the gate outputs as a string
                blackbox_output = f"Circuit outputs: {blackbox_result}\nYou have {max_turns - turn - 1} rounds left."
        else:
            blackbox_output = "Invalid input format. Please provide your input as a list of 8 bits (e.g., [0,1,1,0,0,1,0,1])."
    # Final answer
    blackbox_output += "\n[Final Answer] Please state your guess for the function of the circuit."
    player_output = player.normal_output(blackbox_output)
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), 
         args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))