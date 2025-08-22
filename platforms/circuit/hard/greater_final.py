
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
    Implements the described boolean circuit for n=6 input wires.
    The circuit checks if the number of 1s in the input is >= number of 0s,
    i.e., at least 3 of the 6 input wires are 1.
    Construction:
        - For every 3-combination of input wires, create an AND gate.
        - There are C(6,3) = 20 such combinations.
        - The output is the OR of all 20 AND gates.
    Returns:
        - If simulate_circuit returns a list, returns the list.
        - If simulate_circuit returns an error string, returns the string.
    """
    n = 6
    # Validate input
    if not isinstance(circuit_input, list) or len(circuit_input) != n or any(x not in (0,1) for x in circuit_input):
        return "Error: Input must be a list of 6 bits (0 or 1)."
    # Generate all 3-combinations of input wires (indices 1-based)
    from itertools import combinations
    and_gates = []
    combs = list(combinations(range(1, n+1), 3))  # Each is a tuple of 3 indices (1-based)
    for comb in combs:
        # Each AND gate takes three input wires: a, b, c
        # Since only 2-input AND gates are allowed, we need to chain them:
        # AND(a, AND(b, c)) or AND(AND(a, b), c)
        # We'll do: AND1 = AND(a, b), AND2 = AND(AND1, c)
        a, b, c = comb
        # We'll need to keep track of the gate indices
        # For each combination, we add two gates: first AND(a, b), then AND(prev, c)
        and_gates.append( ('AND', (0, a), (0, b)) )  # This will be gate index = len(gates)+1
        # The output of this gate is (1, current_gate_index)
        prev_gate_idx = len(and_gates)  # 1-based
        and_gates.append( ('AND', (1, prev_gate_idx), (0, c)) )
        # The output of this gate is (1, len(and_gates))
        # We'll collect the outputs of these final ANDs for the OR
    # Now, collect the outputs of the second AND of each combination
    # There are 20 combinations, so 40 AND gates so far
    or_inputs = []
    for i in range(20):
        # The output of the second AND for the i-th combination is at gate index 2*i+2 (1-based)
        or_inputs.append( (1, 2*i+2) )
    # Now, we need to OR all these together
    # Only 2-input OR gates allowed, so we need to build a binary OR tree
    or_gates = []
    current_layer = or_inputs
    while len(current_layer) > 1:
        next_layer = []
        for i in range(0, len(current_layer), 2):
            if i+1 < len(current_layer):
                # OR the two
                or_gates.append( ('OR', current_layer[i], current_layer[i+1]) )
                next_layer.append( (1, len(and_gates) + len(or_gates)) )
            else:
                # Odd one out, just pass to next layer
                next_layer.append(current_layer[i])
        current_layer = next_layer
    # The output of the circuit is the output of the last OR gate (or the only input if only one)
    gates = and_gates + or_gates
    m = len(gates)
    # Simulate
    result = simulate_circuit(n, m, circuit_input, gates)
    return result

def parse_input_bits(player_output, n=6):
    """
    Try to parse a list of 0/1 bits from the player's output.
    Accepts formats like: [0,1,1,0,0,1], 0 1 1 0 0 1, etc.
    Returns: list of bits if valid, else None
    """
    # Try to find a list of 0/1s of length n
    # Accepts: [0,1,1,0,0,1], 0 1 1 0 0 1, 011001, etc.
    # Remove all non-0/1 and non-separator chars
    # First, try to find a list in brackets
    match = re.search(r'\[([01][,\s]*){%d}\]' % n, player_output)
    if match:
        bits = re.findall(r'[01]', match.group(0))
        if len(bits) == n:
            return [int(b) for b in bits]
    # Try to find n 0/1s separated by space or comma
    bits = re.findall(r'[01]', player_output)
    if len(bits) == n:
        return [int(b) for b in bits]
    # Try to find a string of n 0/1s
    match = re.search(r'([01]{%d})' % n, player_output)
    if match:
        return [int(b) for b in match.group(1)]
    return None

def platform(circuit_input):
    """
    Platform function: calls blackbox and formats the output for the player.
    """
    result = blackbox(circuit_input)
    if isinstance(result, str):
        # Error message
        return result
    elif isinstance(result, list):
        # Return the gate outputs as a string
        return f"Gate outputs: {result}"
    else:
        return "Unknown error in platform."

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    n = 6
    rounds_left = max_turns
    blackbox_output = f"Game start. You are interacting with a blackbox boolean circuit with {n} input wires. In each round, submit a list of 6 bits (0 or 1) as your input. You will receive the outputs of all gates. Try to deduce the function of the circuit. Rounds left: {rounds_left}."
    for turn in range(max_turns):
        player_output = player.normal_output(blackbox_output)
        circuit_input = parse_input_bits(player_output, n)
        rounds_left = max_turns - (turn + 1)
        if circuit_input is not None:
            # Valid input, run platform
            blackbox_output = platform(circuit_input)
            blackbox_output += f"\nRounds left: {rounds_left}."
        else:
            # Invalid input, remind player
            blackbox_output = f"Invalid input format. Please submit a list of 6 bits (0 or 1), e.g., [0,1,1,0,0,1] or 0 1 1 0 0 1. Rounds left: {rounds_left}."
    # Final answer
    player_output = player.normal_output(blackbox_output)
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), 
         args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
