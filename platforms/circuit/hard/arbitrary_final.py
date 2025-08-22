
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
    circuit_input: list of 0/1 bits, length 7
    Returns: list of 0/1 bits, each is the output of a gate in the circuit
    The circuit computes f(x) = 1 iff x in {x1, x2, ..., x8}, for 8 fixed 7-bit vectors
    """
    # Validate input
    if not isinstance(circuit_input, list) or len(circuit_input) != 7 or any(x not in (0, 1) for x in circuit_input):
        return "Error: Input must be a list of 7 bits (0 or 1)."

    n = 7  # number of input wires

    # Choose 8 arbitrary 7-bit vectors (no pattern)
    x_list = [
        [0,0,0,0,0,0,0],
        [1,0,1,0,1,0,1],
        [0,1,1,0,0,1,1],
        [1,1,0,1,0,1,0],
        [1,1,1,1,1,1,1],
        [0,1,0,1,0,1,0],
        [1,0,0,1,1,0,0],
        [0,0,1,1,1,0,1]
    ]
    # For each x_i, build a subcircuit that outputs 1 iff input == x_i
    # For each bit, compare input[j] == x_i[j]:
    #   - If x_i[j]==1: just use input wire j+1
    #   - If x_i[j]==0: use NOT(input wire j+1)
    # Then AND all 7 together

    gates = []
    eq_outputs = []  # For each x_i, the output gate index of the equality check

    for xi in x_list:
        bit_outputs = []
        for j in range(7):
            if xi[j] == 1:
                # Use input wire j+1
                bit_outputs.append((0, j+1))
            else:
                # NOT(input wire j+1)
                gates.append(('NOT', (0, j+1)))
                bit_outputs.append((1, len(gates)))  # output of the last gate
        # Now AND all 7 together
        # Chain ANDs: (((b1 AND b2) AND b3) AND ...)
        prev = bit_outputs[0]
        for k in range(1, 7):
            gates.append(('AND', prev, bit_outputs[k]))
            prev = (1, len(gates))
        eq_outputs.append(prev)  # output of this equality check

    # Now OR all eq_outputs together
    prev = eq_outputs[0]
    for k in range(1, len(eq_outputs)):
        gates.append(('OR', prev, eq_outputs[k]))
        prev = (1, len(gates))
    # The output of the circuit is the output of the last gate

    m = len(gates)
    # Simulate the circuit
    result = simulate_circuit(n, m, circuit_input, gates)
    return result

def parse_input_bits(player_output):
    """
    Try to parse a list of 7 bits (0/1) from player_output string.
    Returns: list of 7 bits if successful, else None
    """
    # Accept formats like: [0,1,0,1,1,0,1] or 0 1 0 1 1 0 1 or 0,1,0,1,1,0,1
    # Remove all non-0/1 and non-separator chars
    # Try to find 7 numbers 0/1
    # First, try to find a list of 7 numbers
    matches = re.findall(r'[01]', player_output)
    if len(matches) == 7:
        return [int(x) for x in matches]
    return None

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    blackbox_output = "Game start. You are interacting with a blackbox boolean circuit with 7 input bits. "\
                      "In each round, submit a list of 7 bits (0/1) as your input, e.g. [0,1,0,1,1,0,1]. "\
                      "You will receive the outputs of all gates in the circuit. "\
                      f"You have {max_turns} rounds. Please submit your first input."
    for turn in range(max_turns):
        blackbox_output += f"\nRounds remaining: {max_turns - turn}"
        player_output = player.normal_output(blackbox_output)
        circuit_input = parse_input_bits(player_output)
        if circuit_input is not None:
            # Valid input, run blackbox
            blackbox_result = blackbox(circuit_input)
            if isinstance(blackbox_result, str):
                # Error in blackbox
                blackbox_output = f"Platform error: {blackbox_result}\nPlease submit a list of 7 bits (0/1)."
            else:
                blackbox_output = f"Gate outputs: {blackbox_result}"
        else:
            blackbox_output = "Invalid input format. Please submit a list of 7 bits (0/1), e.g. [0,1,0,1,1,0,1]."
    # Final answer
    blackbox_output += "\nFinal round: Please submit your guess for the function of the circuit."
    player_output = player.normal_output(blackbox_output)
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), 
         args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))