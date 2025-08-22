
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
    Implements the blackbox for the 'consecutive 1' circuit for n=8.
    Returns the output of each gate as a list of 0/1.
    """
    n = 8
    if not isinstance(circuit_input, list) or len(circuit_input) != n or any(x not in (0, 1) for x in circuit_input):
        return "Error: Input must be a list of 8 bits (0 or 1)."
    gates = []
    # b[1] = a[1], b[2] = a[1], b[3] = a[2], ..., b[6] = a[5]
    # For i in 2..6, AND(a[i-1], a[i]) = c[i]
    # For i in 2..6, c[i] = ('AND', (0, i-1), (0, i))
    # s[2] = c[2], s[3] = OR(s[2], c[3]), ..., s[6] = OR(s[5], c[6])
    # Output is s[6]
    # We'll output all gate outputs as required

    # Step 1: Compute c[2]..c[6] (AND gates)
    c_indices = []
    for i in range(2, n+1):
        # ('AND', (0, i-1), (0, i))
        gates.append(('AND', (0, i-1), (0, i)))
        c_indices.append(len(gates))  # 1-based index of this gate

    # Step 2: Compute s[2]..s[6] (OR chain)
    s_indices = []
    for i in range(2, n+1):
        if i == 2:
            # s[2] = c[2]
            s_indices.append(c_indices[0])
        else:
            # s[i] = OR(s[i-1], c[i])
            gates.append(('OR', (1, s_indices[-1]), (1, c_indices[i-2])))
            s_indices.append(len(gates))  # 1-based index

    # The output is s[6] (i.e., s_indices[-1])
    # But as per instructions, return all gate outputs
    m = len(gates)
    result = simulate_circuit(n, m, circuit_input, gates)
    return result

def parse_input_bits(player_output, n=8):
    """
    Try to parse a list of 0/1 bits from player_output.
    Accepts formats like: [0,1,1,0,0,1], 0 1 1 0 0 1, etc.
    Returns list of bits if successful, else None.
    """
    # Try to find a list of 0/1s of length n
    # Accepts: [0,1,1,0,0,1], 0 1 1 0 0 1, 011001, etc.
    # Remove all non-0/1 and non-space/comma/[] chars
    # Try to find a list of n numbers
    # 1. Try to find a list in brackets
    match = re.search(r'\[([01][,\s]*){%d}\]' % n, player_output)
    if match:
        bits = re.findall(r'[01]', match.group(0))
        if len(bits) == n:
            return [int(b) for b in bits]
    # 2. Try to find n 0/1 separated by space or comma
    bits = re.findall(r'[01]', player_output)
    if len(bits) == n:
        return [int(b) for b in bits]
    # 3. Try to find a string of n 0/1s
    match = re.search(r'([01]{%d})' % n, player_output)
    if match:
        return [int(b) for b in match.group(1)]
    return None

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    n = 8
    rounds_left = max_turns
    blackbox_output = f"Game start. You are interacting with a blackbox boolean circuit with {n} input wires. In each round, submit a list of 8 bits (0 or 1) as your input, and you will receive the outputs of all gates. You have {rounds_left} rounds. Please enter your first input."
    for turn in range(max_turns):
        player_output = player.normal_output(blackbox_output)
        circuit_input = parse_input_bits(player_output, n)
        rounds_left = max_turns - turn - 1
        if circuit_input is not None:
            gate_output = blackbox(circuit_input)
            if isinstance(gate_output, str) and gate_output.startswith("Error"):
                blackbox_output = f"Error: {gate_output} Please submit a list of 8 bits (0 or 1). Rounds left: {rounds_left}."
            else:
                blackbox_output = f"Gate outputs: {gate_output}. Rounds left: {rounds_left}."
        else:
            blackbox_output = f"Invalid input format. Please submit a list of 8 bits (0 or 1), e.g., [0,1,1,0,0,1]. Rounds left: {rounds_left}."
    # Final answer phase
    player_output = player.normal_output(blackbox_output)
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), 
         args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
