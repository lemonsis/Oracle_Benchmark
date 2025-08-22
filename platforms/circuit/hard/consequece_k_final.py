
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
    circuit_input: list of 0/1, length 10
    Returns: list of gate outputs (0/1), or error string
    Implements: For n=10, output whether there are four consecutive 1s in the input (circularly).
    Construction:
        - For each i in 1..10:
            s1[i] = x[i] AND x[next(i)]
            s2[i] = s1[i] AND x[next(next(i))]
            s3[i] = s2[i] AND x[next(next(next(i)))]
        - Output: s3[1..10] (each is 1 iff there are four consecutive 1s starting at i)
    """
    n = 10
    if not isinstance(circuit_input, list) or len(circuit_input) != n or any(x not in (0, 1) for x in circuit_input):
        return "Error: Input must be a list of 10 bits (0 or 1)."
    # Gate indices:
    # s1[1..10]: gates 1..10
    # s2[1..10]: gates 11..20
    # s3[1..10]: gates 21..30
    gates = []
    # s1[i] = x[i] AND x[next(i)]
    for i in range(n):
        a = (0, i+1)
        b = (0, ((i+1)%n)+1)
        gates.append(('AND', a, b))
    # s2[i] = s1[i] AND x[next(next(i))]
    for i in range(n):
        a = (1, i+1)  # s1[i] is gate i+1
        b = (0, ((i+2)%n)+1)
        gates.append(('AND', a, b))
    # s3[i] = s2[i] AND x[next(next(next(i)))]
    for i in range(n):
        a = (1, n+i+1)  # s2[i] is gate n+i+1
        b = (0, ((i+3)%n)+1)
        gates.append(('AND', a, b))
    m = len(gates)
    # simulate_circuit returns list of gate outputs
    result = simulate_circuit(n, m, circuit_input, gates)
    return result

def parse_input_bits(player_output, n=10):
    """
    Try to parse a list of 0/1 bits of length n from player_output.
    Accepts: e.g. "1 0 1 1 0 0 1 0 1 0" or "[1,0,1,1,0,0,1,0,1,0]"
    Returns: list of ints, or None if parsing fails
    """
    # Try to find n numbers 0 or 1
    # Accepts both comma and space separated, with or without brackets
    # Remove brackets
    s = player_output.strip()
    s = re.sub(r'[\[\]\(\)\{\}]', '', s)
    # Split by comma or whitespace
    tokens = re.split(r'[\s,]+', s)
    bits = []
    for tok in tokens:
        if tok == '':
            continue
        if tok not in ('0', '1'):
            return None
        bits.append(int(tok))
    if len(bits) != n:
        return None
    return bits

def platform(circuit_input):
    """
    Wrapper for blackbox, formats the output for the player.
    """
    result = blackbox(circuit_input)
    if isinstance(result, str):
        return result
    # result is a list of 30 bits (outputs of all gates)
    return f"Gate outputs: {result}"

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    n = 10
    rounds_left = max_turns
    blackbox_output = f"Game start. You are interacting with a blackbox boolean circuit with {n} input wires. In each round, submit a list of 10 bits (0 or 1) as your input, and you will receive the outputs of the circuit's gates. You have {rounds_left} rounds. Please enter your first input."
    for turn in range(max_turns):
        blackbox_output += f"\nRounds remaining: {max_turns - turn}"
        player_output = player.normal_output(blackbox_output)
        bits = parse_input_bits(player_output, n)
        if bits is not None:
            # Valid input, run through platform
            blackbox_output = platform(bits)
        else:
            blackbox_output = ("Invalid input format. Please enter a list of 10 bits (0 or 1), separated by spaces or commas. Example: 1 0 1 1 0 0 1 0 1 0")
    # Final answer phase
    blackbox_output += "\nGame over. Please provide your final guess for the function of the circuit."
    player_output = player.normal_output(blackbox_output)
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), 
         args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
