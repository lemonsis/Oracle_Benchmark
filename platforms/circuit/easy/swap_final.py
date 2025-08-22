
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
    Implements the swap circuit for n=9:
    - First 4 output gates are the last 4 input wires (input wires 6,7,8,9)
    - Last 5 output gates are the first 5 input wires (input wires 1,2,3,4,5)
    Returns the output of each gate as a list of 0/1 bits.
    """
    n = 9
    m = 9
    if not isinstance(circuit_input, list) or len(circuit_input) != n or any(x not in (0, 1) for x in circuit_input):
        return "Error: Input must be a list of 9 bits (0 or 1)."
    gates = []
    # Gates 1-4: output = input wires 6,7,8,9
    for i in range(6, 10):  # input wires 6,7,8,9 (indices 6-9)
        gates.append(('OR', (0, i), (0, i)))  # OR(a, a) = a, acts as copy
    # Gates 5-9: output = input wires 1,2,3,4,5
    for i in range(1, 6):  # input wires 1-5 (indices 1-5)
        gates.append(('OR', (0, i), (0, i)))
    # Simulate
    result = simulate_circuit(n, m, circuit_input, gates)
    return result

def parse_bit_list(s, n):
    """
    Try to parse a string s into a list of n bits (0/1).
    Accepts formats like: "0 1 0 1 1 0 0 1 1", "[0,1,0,1,1,0,0,1,1]", etc.
    Returns list of ints if successful, else None.
    """
    if not isinstance(s, str):
        return None
    # Find all 0/1 digits
    bits = re.findall(r'[01]', s)
    if len(bits) != n:
        return None
    return [int(b) for b in bits]

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    n = 9
    m = 9
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    blackbox_output = f"Game start! You are interacting with a blackbox boolean circuit with {n} input wires and {m} gates. "\
                      f"Each round, you may submit a list of {n} bits (0 or 1) as input. "\
                      f"Format: 9 bits separated by spaces or commas. "\
                      f"You will receive the output of each gate. You have {max_turns} rounds. "\
                      f"After the last round, you must guess the function of the circuit."
    for turn in range(max_turns):
        blackbox_output += f"\n[Round {turn+1}/{max_turns}]"
        player_output = player.normal_output(blackbox_output)
        circuit_input = parse_bit_list(player_output, n)
        if circuit_input is not None:
            # Valid input, run blackbox
            gate_output = blackbox(circuit_input)
            if isinstance(gate_output, str):
                # Error from blackbox
                blackbox_output = f"Error: {gate_output} Please submit a list of {n} bits (0 or 1)."
            else:
                blackbox_output = f"Gate outputs: {gate_output}. You have {max_turns - (turn+1)} rounds left."
        else:
            blackbox_output = f"Invalid input. Please submit a list of {n} bits (0 or 1), e.g. '0 1 0 1 1 0 0 1 1'. You have {max_turns - (turn)} rounds left."
    # Final answer phase
    blackbox_output += "\n[Final] Please state your guess for the function of the circuit."
    player_output = player.normal_output(blackbox_output)
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), 
         args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
