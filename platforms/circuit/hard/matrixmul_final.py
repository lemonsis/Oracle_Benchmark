
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
    # Validate input
    if not isinstance(circuit_input, list) or len(circuit_input) != 9 or any(x not in (0, 1) for x in circuit_input):
        return "Error: Input must be a list of 9 bits (0 or 1)."
    n = 9  # number of input wires
    gates = []
    # Map input bits to 3x3 matrix M[i][j] where i,j in 0..2
    # input index: i*3 + j
    # We want to compute M^2 over Z_2: M2[i][j] = XOR_k (M[i][k] AND M[k][j]) for k=0..2
    # XOR(a, b) = (a AND (NOT b)) OR (b AND (NOT a))
    # For 3 bits: XOR(a, b, c) = XOR(XOR(a, b), c)
    # We'll build the circuit step by step, keeping track of gate indices

    # Helper to build XOR of two signals (each is (src_type, idx)), returns output gate index
    def xor2(a, b):
        # a, b: (src_type, idx)
        # (a AND (NOT b)) OR (b AND (NOT a))
        # 1. NOT b
        gates.append(('NOT', b))
        not_b = (1, len(gates))
        # 2. a AND (NOT b)
        gates.append(('AND', a, not_b))
        a_and_notb = (1, len(gates))
        # 3. NOT a
        gates.append(('NOT', a))
        not_a = (1, len(gates))
        # 4. b AND (NOT a)
        gates.append(('AND', b, not_a))
        b_and_nota = (1, len(gates))
        # 5. OR of the two
        gates.append(('OR', a_and_notb, b_and_nota))
        return (1, len(gates))

    # Helper to build XOR of three signals (each is (src_type, idx)), returns output gate index
    def xor3(a, b, c):
        ab = xor2(a, b)
        abc = xor2(ab, c)
        return abc

    # For each output M2[i][j], we need to compute XOR_k (M[i][k] AND M[k][j]) for k=0..2
    # We'll store the output gate indices for each M2[i][j]
    M2_outputs = [[None for _ in range(3)] for _ in range(3)]
    # For each i, j in 0..2
    for i in range(3):
        for j in range(3):
            and_gates = []
            for k in range(3):
                # M[i][k] is input wire (0, i*3 + k + 1)
                # M[k][j] is input wire (0, k*3 + j + 1)
                a = (0, i*3 + k + 1)
                b = (0, k*3 + j + 1)
                gates.append(('AND', a, b))
                and_gates.append((1, len(gates)))
            # XOR the three ANDs
            xor_out = xor3(and_gates[0], and_gates[1], and_gates[2])
            M2_outputs[i][j] = xor_out

    # The outputs of the circuit are the outputs of the gates corresponding to M2_outputs (in row-major order)
    # But simulate_circuit returns all gate outputs, so we just need to build the gates list correctly
    m = len(gates)
    # Now, simulate the circuit
    result = simulate_circuit(n, m, circuit_input, gates)
    return result

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    blackbox_output = "Game start! You are interacting with a blackbox boolean circuit. Please input a list of 9 bits (0 or 1), separated by spaces, representing the input wires. You have {} rounds remaining.".format(max_turns)
    for turn in range(max_turns):
        player_output = player.normal_output(blackbox_output)
        # Try to parse player_output as a list of 9 bits
        # Accept formats like: "1 0 1 0 1 0 1 0 1" or "[1,0,1,0,1,0,1,0,1]"
        found = False
        bits = []
        # Try to extract 9 numbers 0 or 1
        # Remove brackets and commas
        cleaned = re.sub(r'[\[\],]', ' ', player_output)
        nums = re.findall(r'\b[01]\b', cleaned)
        if len(nums) == 9:
            bits = [int(x) for x in nums]
            found = True
        if found:
            # Call blackbox
            result = blackbox(bits)
            # Format output for player: show result and remaining rounds
            if isinstance(result, str):
                blackbox_output = result + " You have {} rounds remaining.".format(max_turns - turn - 1)
            else:
                # Show gate outputs as a space-separated string
                blackbox_output = "Gate outputs: " + ' '.join(str(x) for x in result) + ". You have {} rounds remaining.".format(max_turns - turn - 1)
        else:
            blackbox_output = "Invalid input format. Please input a list of 9 bits (0 or 1), separated by spaces or as a Python list. You have {} rounds remaining.".format(max_turns - turn - 1)
    # Final answer phase
    player_output = player.normal_output(blackbox_output)
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), 
         args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
