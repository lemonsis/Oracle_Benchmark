
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
    circuit_input: list of 0/1 bits, length n=7
    Returns: list of 0/1 bits, length m=16 (outputs of each gate)
    """
    n = 7
    m = 16
    if not isinstance(circuit_input, list) or len(circuit_input) != n or any(x not in (0, 1) for x in circuit_input):
        return "Error: Input must be a list of 7 bits (0 or 1)."
    # Construct a circuit of 16 gates, arbitrary but valid and not for a well-known function
    # We'll mix AND, OR, NOT, and use both input wires and previous gates as inputs
    gates = [
        # 1-3: AND gates on pairs of input wires
        ('AND', (0, 1), (0, 2)),      # gate 1
        ('AND', (0, 3), (0, 4)),      # gate 2
        ('AND', (0, 5), (0, 6)),      # gate 3
        # 4-6: OR gates on pairs of input wires
        ('OR', (0, 2), (0, 3)),       # gate 4
        ('OR', (0, 4), (0, 5)),       # gate 5
        ('OR', (0, 6), (0, 7)),       # gate 6
        # 7-9: NOT gates on input wires
        ('NOT', (0, 1)),              # gate 7
        ('NOT', (0, 4)),              # gate 8
        ('NOT', (0, 7)),              # gate 9
        # 10-12: Mix previous gates
        ('AND', (1, 1), (1, 4)),      # gate 10: AND of gate 1 and gate 4
        ('OR', (1, 2), (1, 5)),       # gate 11: OR of gate 2 and gate 5
        ('AND', (1, 3), (1, 6)),      # gate 12: AND of gate 3 and gate 6
        # 13-14: NOT of previous gates
        ('NOT', (1, 10)),             # gate 13: NOT of gate 10
        ('NOT', (1, 12)),             # gate 14: NOT of gate 12
        # 15: OR of two NOTs
        ('OR', (1, 13), (1, 14)),     # gate 15: OR of gate 13 and gate 14
        # 16: AND of a NOT and an OR
        ('AND', (1, 8), (1, 11)),     # gate 16: AND of gate 8 and gate 11
    ]
    result = simulate_circuit(n, m, circuit_input, gates)
    return result

def parse_input_bits(player_output, n=7):
    """
    Try to parse a list of 0/1 bits from player_output.
    Accepts formats like: [0,1,1,0,1,0,1], 0 1 1 0 1 0 1, or comma/space separated.
    Returns: list of bits if valid, else None
    """
    # Remove brackets and extra characters
    s = player_output.strip()
    s = re.sub(r'[\[\]\(\)\{\}]', '', s)
    # Find all 0 or 1 digits
    bits = re.findall(r'[01]', s)
    if len(bits) != n:
        return None
    try:
        bits = [int(b) for b in bits]
    except Exception:
        return None
    if all(b in (0, 1) for b in bits):
        return bits
    return None

def platform(circuit_input):
    """
    Wrapper for blackbox, returns formatted output for the player.
    """
    result = blackbox(circuit_input)
    if isinstance(result, str):
        return f"Error: {result}"
    return f"Gate outputs: {result}"

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    n = 7
    rounds_left = max_turns
    blackbox_output = (
        f"Game start. You are interacting with a blackbox boolean circuit with {n} input wires and 16 gates. "
        f"Each round, you may submit a list of 7 bits (0 or 1) as input, e.g. [0,1,1,0,1,0,1]. "
        f"The platform will return the outputs of all 16 gates. "
        f"You have {max_turns} rounds. Please submit your input bits for round 1."
    )
    for turn in range(1, max_turns + 1):
        blackbox_output += f"\nRounds remaining: {max_turns - turn + 1}."
        player_output = player.normal_output(blackbox_output)
        circuit_input = parse_input_bits(player_output, n)
        if circuit_input is not None:
            # Valid input, get blackbox output
            gate_outputs = platform(circuit_input)
            blackbox_output = f"Input: {circuit_input}\n{gate_outputs}"
        else:
            # Invalid input, remind player
            blackbox_output = (
                f"Invalid input format. Please submit a list of 7 bits (0 or 1), e.g. [0,1,1,0,1,0,1]. "
                f"Rounds remaining: {max_turns - turn}."
            )
    # Final answer phase
    blackbox_output += "\nGame over. Please provide your final guess for the function of the circuit."
    player_output = player.normal_output(blackbox_output)
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]),
         args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
