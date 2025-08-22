
import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from ckpt import simulate_circuit
from eva_models import ReasoningLLM
import re

def build_tree_and_gates(n):
    """
    Build a tree AND circuit for n input wires.
    Returns a list of gates in the format required by simulate_circuit.
    Each gate is a tuple: ('AND', input1, input2)
    input1/input2: (0, i) for input wire i (1-based), (1, j) for output of gate j (1-based)
    """
    # Each node is (start, end, output_ref)
    # output_ref: (0, i) for input wire, (1, j) for gate output
    # We build the tree bottom-up, and collect gates in order
    gates = []
    def build(start, end):
        if start == end:
            # Leaf: input wire
            return (0, start)
        else:
            mid = (start + end) // 2
            left = build(start, mid)
            right = build(mid+1, end)
            # The next gate index is len(gates)+1 (1-based)
            gates.append(('AND', left, right))
            return (1, len(gates)) # output of this gate
    build(1, n)
    return gates

def blackbox(circuit_input):
    """
    circuit_input: list of 0/1 bits, length n
    Returns: list of 0/1 bits, length m (outputs of each gate in order)
    """
    # Validate input
    if not isinstance(circuit_input, list) or not all(x in (0,1) for x in circuit_input):
        return "Error: Input must be a list of 0/1 bits."
    n = len(circuit_input)
    if n < 2:
        return "Error: At least 2 input wires required."
    gates = build_tree_and_gates(n)
    m = len(gates)
    result = simulate_circuit(n, m, circuit_input, gates)
    return result

def parse_input_bits(s, n=None):
    """
    Try to parse a string s into a list of 0/1 bits.
    Accepts formats like: [0,1,1,0], 0 1 1 0, 0110, etc.
    If n is given, checks that the length matches n.
    Returns: list of bits or None if parsing fails.
    """
    s = s.strip()
    # Try to find a list of numbers
    # Remove brackets
    s_clean = re.sub(r'[\[\]\(\)\{\}]', '', s)
    # Split by comma or whitespace
    tokens = re.split(r'[,\s]+', s_clean)
    bits = []
    for tok in tokens:
        if tok == '':
            continue
        if tok not in ('0','1'):
            return None
        bits.append(int(tok))
    if n is not None and len(bits) != n:
        return None
    if len(bits) == 0:
        return None
    return bits

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    # For this circuit, fix n=8
    n = 8
    m = n - 1 if n == 2 else (2*n-2) # Actually, for binary tree, m = n-1, but our build_tree_and_gates returns m = n-1
    # But let's use build_tree_and_gates to get m
    gates = build_tree_and_gates(n)
    m = len(gates)
    blackbox_output = f"Game start! You are interacting with a blackbox boolean circuit with {n} input wires and {m} gates. " \
                      f"In each round, you may submit a list of {n} bits (0/1) as input. The platform will return the outputs of all {m} gates in order. " \
                      f"Format your input as a list of {n} bits, e.g., [0,1,1,0,0,1,0,1]. You have {max_turns} rounds. Good luck!"
    for turn in range(max_turns):
        remain = max_turns - turn
        blackbox_output += f"\n[Platform] Remaining rounds: {remain}."
        player_output = player.normal_output(blackbox_output)
        # Try to parse input
        circuit_input = parse_input_bits(player_output, n)
        if circuit_input is not None:
            # Valid input, run blackbox
            gate_output = blackbox(circuit_input)
            if isinstance(gate_output, str):
                # Error from blackbox
                blackbox_output = f"[Platform] Error: {gate_output} Please submit a list of {n} bits (0/1)."
            else:
                blackbox_output = f"[Platform] Gate outputs: {gate_output}"
        else:
            blackbox_output = f"[Platform] Invalid input format. Please submit a list of {n} bits (0/1), e.g., [0,1,1,0,0,1,0,1]."
    # Final answer
    blackbox_output += "\n[Platform] Game over. Please submit your final guess of the circuit's function."
    player_output = player.normal_output(blackbox_output)
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), 
         args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
