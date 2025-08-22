
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
    """
    Implements a prefix XOR circuit for n=8 input bits.
    Returns the output of each gate as a list of 0/1 bits.
    """
    n = 8
    if not isinstance(circuit_input, list) or len(circuit_input) != n or any(x not in (0, 1) for x in circuit_input):
        return "Error: Input must be a list of 8 bits (0 or 1)."
    gates = []
    # s[0] = a[0]
    # For i >= 1: s[i] = s[i-1] xor a[i]
    # xor(a, b) = (a and (not b)) or ((not a) and b)
    # We'll build the gates step by step, keeping track of the output index for each s[i]
    # Gate indices start from 1

    # s[0] = a[0], so no gate needed for s[0], but for uniformity, we can treat s[0] as input wire 1

    # We'll store the output index for each s[i]
    s_indices = [None] * n
    s_indices[0] = 0  # input wire 1 (index 0 in code, but (0,1) in gate input)

    gate_idx = 1  # gate indices start from 1

    for i in range(1, n):
        # s[i-1] is s_indices[i-1]
        # a[i] is input wire i+1 (since input wires are 1-indexed in gate tuples)
        # Build NOT gates for s[i-1] and a[i]
        # NOT s[i-1]
        if s_indices[i-1] == 0:
            not_s_prev = ('NOT', (0, 1))
        else:
            not_s_prev = ('NOT', (1, s_indices[i-1]))
        gates.append(not_s_prev)
        not_s_prev_idx = gate_idx
        gate_idx += 1

        # NOT a[i]
        not_a_i = ('NOT', (0, i+1))
        gates.append(not_a_i)
        not_a_i_idx = gate_idx
        gate_idx += 1

        # (s[i-1] AND (NOT a[i]))
        if s_indices[i-1] == 0:
            and1 = ('AND', (0, 1), (1, not_a_i_idx))
        else:
            and1 = ('AND', (1, s_indices[i-1]), (1, not_a_i_idx))
        gates.append(and1)
        and1_idx = gate_idx
        gate_idx += 1

        # ((NOT s[i-1]) AND a[i])
        and2 = ('AND', (1, not_s_prev_idx), (0, i+1))
        gates.append(and2)
        and2_idx = gate_idx
        gate_idx += 1

        # OR of the two ANDs
        or1 = ('OR', (1, and1_idx), (1, and2_idx))
        gates.append(or1)
        or1_idx = gate_idx
        gate_idx += 1

        # s[i] is the output of or1
        s_indices[i] = or1_idx

    m = len(gates)
    # simulate_circuit expects input wires to be 1-indexed in gate tuples
    result = simulate_circuit(n, m, circuit_input, gates)
    return result

def parse_input_bits(player_output, n=8):
    """
    Try to parse a list of 0/1 bits from player_output.
    Accepts formats like: [0,1,1,0,0,1], 0 1 1 0 0 1, 011001, etc.
    Returns list of bits if successful, else None.
    """
    # Try to find a list of 0/1s in brackets
    match = re.search(r'\[([01][,\s]*){%d}\]' % n, player_output)
    if match:
        bits = re.findall(r'[01]', match.group(0))
        if len(bits) == n:
            return [int(b) for b in bits]
    # Try to find n space-separated or comma-separated 0/1s
    match = re.findall(r'[01]', player_output)
    if len(match) == n:
        return [int(b) for b in match]
    # Try to find a string of exactly n 0/1s
    match = re.search(r'\b[01]{%d}\b' % n, player_output)
    if match:
        return [int(b) for b in match.group(0)]
    return None

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    n = 8
    rounds_left = max_turns
    blackbox_output = (
        f"Game start! You are interacting with a blackbox Boolean circuit with {n} input wires. "
        f"In each round, you may submit a list of {n} bits (0 or 1) as input, and the platform will return the outputs of all gates. "
        f"Format your input as a list of {n} bits."
        f"You have {rounds_left} rounds. Good luck!"
    )
    for turn in range(max_turns):
        blackbox_output += f"\n[Platform] Rounds remaining: {max_turns - turn}"
        player_output = player.normal_output(blackbox_output)
        circuit_input = parse_input_bits(player_output, n)
        if circuit_input is not None:
            # Valid input, run blackbox
            gate_output = blackbox(circuit_input)
            if isinstance(gate_output, str):
                # Error from blackbox
                blackbox_output = f"[Platform] Error: {gate_output}\nPlease submit a list of {n} bits (0 or 1)."
            else:
                blackbox_output = (
                    f"[Platform] Gate outputs: {gate_output}\n"
                    f"Submit your next input as a list of {n} bits."
                )
        else:
            blackbox_output = (
                f"[Platform] Invalid input format. Please submit a list of {n} bits (0 or 1), "
                f"e.g., [0,1,1,0,0,1,1,1]."
            )
    # Final answer phase
    blackbox_output += "\n[Platform] Game over. Please submit your final guess for the function of the circuit."
    player_output = player.normal_output(blackbox_output)
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), 
         args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
