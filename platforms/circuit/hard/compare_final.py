
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
    Implements a compare circuit for n=10 input bits: x1..x5, y1..y5.
    The circuit outputs 1 iff (x1..x5) > (y1..y5) in unsigned binary.
    Returns the output of each gate as a list.
    """
    # Validate input
    if not isinstance(circuit_input, list) or len(circuit_input) != 10 or any(x not in (0, 1) for x in circuit_input):
        return "Error: Input must be a list of 10 bits (0 or 1)."
    n = 10  # number of input wires
    gates = []
    # Indices: x1..x5: input 1..5, y1..y5: input 6..10
    # We'll build the compare circuit as described:
    # For i in 1..5, define:
    #   gt_i = x_i AND (NOT y_i)
    #   eq_i = (x_i AND y_i) OR ((NOT x_i) AND (NOT y_i))
    # Then recursively:
    #   result = gt_1 OR (eq_1 AND (gt_2 OR (eq_2 AND (gt_3 OR (eq_3 AND (gt_4 OR (eq_4 AND gt_5)))))))
    # We'll build all gates step by step, keeping track of their indices.

    # Step 1: For i=1..5, build NOT x_i and NOT y_i
    not_x = []
    not_y = []
    for i in range(5):
        # NOT x_i: input wire i+1
        gates.append(('NOT', (0, i+1)))
        not_x.append(len(gates))  # index of this gate
        # NOT y_i: input wire i+6
        gates.append(('NOT', (0, i+6)))
        not_y.append(len(gates))  # index of this gate

    # Step 2: For i=1..5, build gt_i = x_i AND (NOT y_i)
    gt = []
    for i in range(5):
        gates.append(('AND', (0, i+1), (1, not_y[i])))
        gt.append(len(gates))

    # Step 3: For i=1..5, build eq_i = (x_i AND y_i) OR ((NOT x_i) AND (NOT y_i))
    eq = []
    for i in range(5):
        # (x_i AND y_i)
        gates.append(('AND', (0, i+1), (0, i+6)))
        and1 = len(gates)
        # (NOT x_i) AND (NOT y_i)
        gates.append(('AND', (1, not_x[i]), (1, not_y[i])))
        and2 = len(gates)
        # OR of the above two
        gates.append(('OR', (1, and1), (1, and2)))
        eq.append(len(gates))

    # Step 4: Build the recursive compare logic
    # We'll build from the innermost to the outermost
    # Start with gt_5
    curr = gt[4]
    for i in range(3, -1, -1):
        # gt_{i+1} OR (eq_{i+1} AND curr)
        gates.append(('AND', (1, eq[i+1]), (1, curr)))
        and_idx = len(gates)
        gates.append(('OR', (1, gt[i]), (1, and_idx)))
        curr = len(gates)
    # curr now holds the index of the final output gate

    # The output of each gate is required
    m = len(gates)
    output = simulate_circuit(n, m, circuit_input, gates)
    return output

def parse_input_bits(player_output):
    """
    Try to parse a list of 10 bits (0/1) from the player's output.
    Accepts formats like: [0,1,0,1,1,0,0,1,0,1] or 0 1 0 1 1 0 0 1 0 1
    Returns list of 10 ints or None if parsing fails.
    """
    # Try to find a list of 10 numbers (0 or 1)
    # Accept both comma and space separated, with or without brackets
    # Remove brackets
    s = player_output.strip()
    s = re.sub(r'[\[\]\(\)]', '', s)
    # Split by comma or whitespace
    tokens = re.split(r'[,\s]+', s)
    bits = []
    for tok in tokens:
        if tok == '':
            continue
        if tok not in ('0', '1'):
            return None
        bits.append(int(tok))
    if len(bits) != 10:
        return None
    return bits

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    rounds_left = max_turns
    blackbox_output = (
        "Game start! You are interacting with a boolean circuit blackbox. "
        "Each round, you may submit a list of 10 bits (0/1), representing the circuit's 10 input wires. "
        "The circuit will return the output of each gate. "
        f"You have {rounds_left} rounds to interact. "
        "Please submit your input as a list of 10 bits, e.g., [0,1,0,1,1,0,0,1,0,1]."
    )
    for turn in range(max_turns):
        player_output = player.normal_output(blackbox_output)
        bits = parse_input_bits(player_output)
        rounds_left = max_turns - turn - 1
        if bits is not None:
            # Valid input, run blackbox
            gate_output = blackbox(bits)
            if isinstance(gate_output, str):
                # Error from blackbox
                blackbox_output = (
                    f"Error: {gate_output} "
                    f"Please submit your input as a list of 10 bits (0/1). "
                    f"Rounds left: {rounds_left}."
                )
            else:
                blackbox_output = (
                    f"Gate outputs: {gate_output}\n"
                    f"Rounds left: {rounds_left}."
                )
        else:
            blackbox_output = (
                "Invalid input format. Please submit your input as a list of 10 bits (0/1), "
                "e.g., [0,1,0,1,1,0,0,1,0,1]. "
                f"Rounds left: {rounds_left}."
            )
    # Final answer phase
    player_output = player.normal_output(blackbox_output)
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), 
         args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
