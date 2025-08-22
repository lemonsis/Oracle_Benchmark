
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
    circuit_input: list of 0/1 bits, length n=10
    Implements: add a[1] to the binary number a[2]a[3]...a[10]
    result[i]=a[n-i+1] xor b[i-1], b[i]=a[n-i+1] and b[i-1], b[0]=1
    Returns: gate_output (list of 0/1 bits for each gate)
    """
    n = 10
    if not isinstance(circuit_input, list) or len(circuit_input) != n or any(x not in (0, 1) for x in circuit_input):
        return "Error: Input must be a list of 10 bits (0 or 1)."
    gates = []
    # b[0] = 1 (constant)
    # We'll represent b[0] as a "virtual" input, not a gate.
    # For each i in 1..n-1, compute:
    #   b[i] = a[n-i+1] AND b[i-1]
    #   result[i] = a[n-i+1] XOR b[i-1]
    # We'll use gates for all b[i] and result[i]
    # To compute XOR: (A AND (NOT B)) OR ((NOT A) AND B)
    # We'll keep track of gate indices:
    #   gate indices start from 1
    # We'll need to map b[i-1] for each i
    # We'll use a virtual input wire for b[0]=1, which is not in circuit_input, so we need to handle it

    # To handle b[0]=1, we can add an extra input wire at the end (input wire 11), always set to 1
    # So, input wires: a[1]..a[10], b0=1 (input wire 11)
    # For simulate_circuit, n=11, input=[a[1]..a[10], 1]
    # But the interface expects n=10, so we need to simulate b[0]=1 as a constant using a NOT(NOT(x)) trick
    # Let's add a NOT gate on input wire 1, then NOT that output, so we get input wire 1 back, but we can use this to create a constant 1 if input[0]=1, but we want a constant 1 always
    # Instead, let's use a NOT(NOT(x)) on input wire 1, and if input[0]=0, we can NOT(NOT(input[0])) and OR with input[0] to get 1 if input[0]=0 or 1
    # But that's too complicated. Instead, let's just use a constant 1 as a virtual input in our code logic, not as a gate.

    # We'll keep a mapping: b_vals, result_vals, and gate indices
    # We'll build the gates list as we go

    # For each i in 1..n-1 (i=1..9):
    #   b[i] = a[n-i+1] AND b[i-1]
    #   result[i] = a[n-i+1] XOR b[i-1]
    # We'll need to keep track of the gate indices for b[i] and result[i]
    # We'll use a dict to map b[i] and result[i] to their gate indices

    # For XOR, we need 4 gates per result[i]:
    #   t1 = NOT b[i-1]
    #   t2 = a[n-i+1] AND t1
    #   t3 = NOT a[n-i+1]
    #   t4 = b[i-1] AND t3
    #   result[i] = t2 OR t4

    # For b[i], 1 AND gate per i

    # We'll keep a list of gate outputs to return at the end

    # We'll use the following mapping:
    #   input wires: 1..10 (a[1]..a[10])
    #   gate indices: start from 1

    # b[0] is a constant 1, not a gate
    # We'll keep a mapping: b_indices[i] = gate index of b[i] (for i>=1)
    # result_indices[i] = gate index of result[i] (for i>=1)

    gate_idx = 1
    b_indices = {}
    result_indices = {}

    # For b[0], we use a constant 1, so in simulate_circuit, we can't use a constant input, but we can use input wire 1 and NOT(NOT(input wire 1)) to get input wire 1 back, but that's not a constant 1 unless input[0]=1
    # Instead, let's use input wire 1, and require that the first input bit is always 1 (we can check this in the input validation)
    # But the problem says nothing about this, so let's use a trick: for b[0], we use input wire 1, and require that the first input bit is always 1

    # But to be robust, let's use a NOT(NOT(input wire 1)), and if input[0]=1, this is 1, if input[0]=0, this is 0
    # So, we can't get a constant 1 unless we have a constant input wire, which we don't
    # So, let's just use input wire 1 as b[0], and require that input[0]=1

    # But the problem says a[1] is the bit to add, so a[2]..a[10] is the number, and a[1] is the addend
    # So, b[0]=a[1]
    # So, for i=1, b[0]=a[1], a[n-i+1]=a[10]
    # For i=1..9:
    #   b[i] = a[n-i+1] AND b[i-1]
    #   result[i] = a[n-i+1] XOR b[i-1]

    # So, b[0]=a[1] (input wire 1)
    # For i=1..9:
    #   a[n-i+1] = input wire n-i+1

    # Let's proceed

    # b[0] is input wire 1
    b_prev = (0, 1)  # (0, 1) means input wire 1

    for i in range(1, n):
        a_idx = n - i + 1  # input wire index for a[n-i+1]
        # Compute t1 = NOT b_prev
        gates.append(('NOT', b_prev))
        t1_idx = gate_idx
        gate_idx += 1
        # t2 = a[n-i+1] AND t1
        gates.append(('AND', (0, a_idx), (1, t1_idx)))
        t2_idx = gate_idx
        gate_idx += 1
        # t3 = NOT a[n-i+1]
        gates.append(('NOT', (0, a_idx)))
        t3_idx = gate_idx
        gate_idx += 1
        # t4 = b_prev AND t3
        gates.append(('AND', b_prev, (1, t3_idx)))
        t4_idx = gate_idx
        gate_idx += 1
        # result[i] = t2 OR t4
        gates.append(('OR', (1, t2_idx), (1, t4_idx)))
        result_indices[i] = gate_idx
        gate_idx += 1
        # b[i] = a[n-i+1] AND b_prev
        gates.append(('AND', (0, a_idx), b_prev))
        b_indices[i] = gate_idx
        gate_idx += 1
        # Update b_prev for next iteration
        b_prev = (1, b_indices[i])

    m = len(gates)
    # simulate_circuit expects input wires 1..10
    # input: circuit_input (length 10)
    # gates: as constructed above
    # Output: list of gate outputs, length m

    output = simulate_circuit(n, m, circuit_input, gates)
    return output

def parse_input_bits(player_output, n=10):
    """
    Try to parse player_output into a list of n bits (0/1).
    Accepts formats like: "1 0 1 0 1 0 1 0 1 0", "[1,0,1,0,1,0,1,0,1,0]", etc.
    Returns: list of bits or None if parsing fails
    """
    # Remove brackets and commas
    s = re.sub(r'[\[\],]', ' ', player_output)
    # Find all 0 or 1
    bits = re.findall(r'\b[01]\b', s)
    if len(bits) != n:
        return None
    try:
        return [int(b) for b in bits]
    except Exception:
        return None

def platform(circuit_input):
    """
    Wrapper for blackbox, formats the output for the player.
    """
    output = blackbox(circuit_input)
    if isinstance(output, str):
        return output
    elif isinstance(output, list):
        return f"Gate outputs: {output}"
    else:
        return "Error: Unexpected output from blackbox."

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    n = 10
    rounds_left = max_turns
    blackbox_output = f"Game start. You are interacting with a blackbox boolean circuit with {n} input bits. "\
                      f"Each round, you may submit a list of {n} bits (0 or 1) as input. "\
                      f"The platform will return the outputs of all gates in the circuit. "\
                      f"You have {max_turns} rounds. Please enter your first input (as {n} bits, e.g. '1 0 1 0 1 0 1 0 1 0')."
    for turn in range(max_turns):
        blackbox_output += f"\nRounds remaining: {max_turns - turn}"
        player_output = player.normal_output(blackbox_output)
        circuit_input = parse_input_bits(player_output, n)
        if circuit_input is not None:
            blackbox_output = platform(circuit_input)
        else:
            blackbox_output = f"Invalid input format. Please enter exactly {n} bits (0 or 1), separated by spaces or commas. "\
                              f"Example: '1 0 1 0 1 0 1 0 1 0'.\nRounds remaining: {max_turns - turn - 1}"
    # Final answer
    blackbox_output += "\nThis is your last chance to guess the function of the circuit. Please provide your answer."
    player_output = player.normal_output(blackbox_output)
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), 
         args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
