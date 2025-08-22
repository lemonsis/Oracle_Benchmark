
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
    Simulates a fixed 8-gate boolean circuit with 4 input wires.
    Args:
        circuit_input: list of 4 integers (0 or 1)
    Returns:
        gate_output: list of 8 integers (0 or 1), or error string
    """
    # Validate input
    if not isinstance(circuit_input, list) or len(circuit_input) != 4 or not all(x in (0, 1) for x in circuit_input):
        return "Error: Input must be a list of 4 bits (0 or 1)."
    n = 4
    m = 8
    # Construct a nontrivial, arbitrary circuit of 8 gates
    # Gate indices: 1..8
    # Input wires: 1..4
    # Each gate: ('TYPE', (src_type, idx), (src_type, idx)) or ('NOT', (src_type, idx))
    # src_type: 0=input wire, 1=gate output

    gates = [
        # Gate 1: AND of input 1 and input 2
        ('AND', (0, 1), (0, 2)),          # gate 1
        # Gate 2: OR of input 3 and input 4
        ('OR', (0, 3), (0, 4)),           # gate 2
        # Gate 3: NOT of input 1
        ('NOT', (0, 1)),                  # gate 3
        # Gate 4: AND of gate 1 and gate 2
        ('AND', (1, 1), (1, 2)),          # gate 4
        # Gate 5: OR of gate 3 and input 2
        ('OR', (1, 3), (0, 2)),           # gate 5
        # Gate 6: NOT of gate 4
        ('NOT', (1, 4)),                  # gate 6
        # Gate 7: AND of gate 5 and gate 6
        ('AND', (1, 5), (1, 6)),          # gate 7
        # Gate 8: OR of gate 7 and input 4
        ('OR', (1, 7), (0, 4)),           # gate 8
    ]
    # Simulate
    result = simulate_circuit(n, m, circuit_input, gates)
    return result

def parse_input_bits(player_output, n_bits=4):
    """
    Try to parse a list of n_bits 0/1 from player_output string.
    Returns: list of bits or None
    """
    # Accept formats like: [0,1,1,0], 0 1 1 0, 0,1,1,0, etc.
    # Remove all non-0/1 and non-separator chars
    # Try to find n_bits numbers
    # First, try to find a list in brackets
    m = re.search(r'\[([01][,\s]*){%d,}\]' % (n_bits-1), player_output)
    if m:
        bits = re.findall(r'[01]', m.group(0))
        if len(bits) == n_bits:
            return [int(b) for b in bits]
    # Else, try to find n_bits numbers in a row
    bits = re.findall(r'[01]', player_output)
    if len(bits) >= n_bits:
        return [int(b) for b in bits[:n_bits]]
    return None

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    """
    Main interaction loop between LLM player and blackbox circuit.
    """
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    n_bits = 4
    rounds_left = max_turns
    # Initial prompt
    blackbox_output = (
        f"Game start. You are interacting with a blackbox boolean circuit with {n_bits} input wires and 8 gates. "
        f"Each round, you may submit a list of {n_bits} bits (0 or 1) as input, e.g. [0,1,1,0]. "
        f"The blackbox will return the outputs of all 8 gates. "
        f"You have {max_turns} rounds to interact. "
        f"After the rounds, you will be asked to guess the function of the circuit."
    )
    for turn in range(max_turns):
        blackbox_output += f"\nRounds remaining: {max_turns - turn}"
        player_output = player.normal_output(blackbox_output)
        # Try to parse input bits
        circuit_input = parse_input_bits(player_output, n_bits)
        if circuit_input is not None:
            # Valid input, run blackbox
            gate_output = blackbox(circuit_input)
            if isinstance(gate_output, str):
                # Error from blackbox
                blackbox_output = f"Error: {gate_output} Please submit a list of {n_bits} bits (0 or 1)."
            else:
                blackbox_output = (
                    f"Input: {circuit_input}\n"
                    f"Gate outputs: {gate_output}\n"
                )
        else:
            # Invalid input
            blackbox_output = (
                f"Invalid input. Please submit a list of {n_bits} bits (0 or 1), e.g. [0,1,1,0]."
            )
    # Final answer phase
    blackbox_output += "\nRounds finished. Please guess the function of the circuit."
    player_output = player.normal_output(blackbox_output)
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), 
         args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
