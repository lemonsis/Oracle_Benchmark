
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
    # Map input to 3x3 adjacency matrix G
    # G[i][j] = circuit_input[3*i + j]
    # G[i][i] is ignored (diagonal)
    # We want to compute G'[i][j] = 1 if there is a path from i to j (length 1 or 2), else 0
    # For all i, G'[i][i] = 1
    # For i != j: G'[i][j] = G[i][j] OR (OR over k of (G[i][k] AND G[k][j]))
    # We'll build the circuit step by step, using only AND/OR/NOT gates as specified

    gates = []
    # For referencing: input wire (0, idx+1), gate output (1, idx+1)
    # We'll keep track of gate indices for each intermediate result

    # Step 1: For each i,j, i != j, compute all (G[i][k] AND G[k][j]) for k=0..2
    # We'll store these AND gates' indices for each (i,j)
    and_gate_indices = {}  # (i,j): [gate_idx for k=0..2]
    gate_count = 0
    for i in range(3):
        for j in range(3):
            if i == j:
                continue
            and_gate_indices[(i, j)] = []
            for k in range(3):
                # Only consider k != i and k != j, but for path of length 2, k can be any node (including i or j)
                # But for a path of length 2, k can be any node (including i or j)
                # So we do not skip any k
                # G[i][k] is input wire 3*i + k + 1
                # G[k][j] is input wire 3*k + j + 1
                idx1 = 3 * i + k + 1
                idx2 = 3 * k + j + 1
                gates.append(('AND', (0, idx1), (0, idx2)))
                gate_count += 1
                and_gate_indices[(i, j)].append(gate_count)  # 1-based index

    # Step 2: For each i,j, i != j, OR all the ANDs together, and also OR with G[i][j]
    or_gate_indices = {}  # (i,j): gate_idx
    for i in range(3):
        for j in range(3):
            if i == j:
                continue
            # OR all the AND gates for (i,j)
            ands = and_gate_indices[(i, j)]
            # OR them together (pairwise)
            # If only one AND, just use it
            if len(ands) == 1:
                or_result = ands[0]
            else:
                # OR first two
                gates.append(('OR', (1, ands[0]), (1, ands[1])))
                gate_count += 1
                or_result = gate_count
                # If three, OR the third with previous result
                if len(ands) == 3:
                    gates.append(('OR', (1, or_result), (1, ands[2])))
                    gate_count += 1
                    or_result = gate_count
            # Now OR with G[i][j] (input wire 3*i + j + 1)
            gates.append(('OR', (1, or_result), (0, 3 * i + j + 1)))
            gate_count += 1
            or_gate_indices[(i, j)] = gate_count  # 1-based index

    # Step 3: For each i, set G'[i][i] = 1 (constant 1)
    # Since we can't have constant gates, we can just output 1 for these positions in the output, or simulate with a NOT(NOT(x)) for any input x
    # But since the output is the list of all gate outputs, we can just document that G'[i][i]=1

    # Step 4: Collect outputs for all G'[i][j] in row-major order (i=0..2, j=0..2)
    # For i==j, output 1; for i!=j, output the corresponding OR gate output
    outputs = []
    for i in range(3):
        for j in range(3):
            if i == j:
                outputs.append(1)
            else:
                outputs.append(None)  # Placeholder, will fill after simulation

    # Now, simulate the circuit
    m = len(gates)
    sim_result = simulate_circuit(n, m, circuit_input, gates)
    if isinstance(sim_result, str):
        return sim_result  # error message

    # Fill in outputs for i!=j
    for i in range(3):
        for j in range(3):
            if i != j:
                # The last OR gate for (i,j) is or_gate_indices[(i,j)] (1-based)
                outputs[3 * i + j] = sim_result[or_gate_indices[(i, j)] - 1]

    # Return the outputs as a list of 9 bits (row-major G' matrix)
    return outputs

def parse_input_bits(player_output):
    # Accepts a string, tries to extract a list of 9 bits (0 or 1)
    # Accepts formats like: [0,1,1,0,0,1,0,1,0] or 0 1 1 0 0 1 0 1 0 or 011001010
    # Returns list of 9 ints or None
    if isinstance(player_output, list) and len(player_output) == 9 and all(x in (0, 1) for x in player_output):
        return player_output
    # Try to find a list in brackets
    m = re.search(r'\[([01][,\s]*){9}\]', player_output)
    if m:
        bits = re.findall(r'[01]', m.group(0))
        if len(bits) == 9:
            return [int(b) for b in bits]
    # Try to find 9 digits in a row
    m = re.search(r'([01][\s,]*){9}', player_output)
    if m:
        bits = re.findall(r'[01]', m.group(0))
        if len(bits) == 9:
            return [int(b) for b in bits]
    # Try to find 9 digits anywhere
    bits = re.findall(r'[01]', player_output)
    if len(bits) == 9:
        return [int(b) for b in bits]
    return None

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    blackbox_output = "Game start. You are interacting with a blackbox boolean circuit. Each round, you may submit a list of 9 bits (0 or 1) as the circuit input. The platform will return the output of the circuit. You have {} rounds. Please enter your first input as a list of 9 bits.".format(max_turns)
    for turn in range(max_turns):
        blackbox_output += "\nRounds remaining: {}".format(max_turns - turn)
        player_output = player.normal_output(blackbox_output)
        circuit_input = parse_input_bits(player_output)
        if circuit_input is not None:
            # Valid input, run blackbox
            blackbox_result = blackbox(circuit_input)
            if isinstance(blackbox_result, str):
                # Error in blackbox
                blackbox_output = "Platform error: " + blackbox_result + " Please try again with a valid input of 9 bits."
            else:
                blackbox_output = "Circuit output: " + str(blackbox_result)
        else:
            blackbox_output = "Invalid input format. Please enter a list of 9 bits (0 or 1), e.g., [0,1,1,0,0,1,0,1,0]."
    # Final answer phase
    blackbox_output += "\nGame over. Please provide your final answer or guess for the function of the circuit."
    player_output = player.normal_output(blackbox_output)
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), 
         args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
