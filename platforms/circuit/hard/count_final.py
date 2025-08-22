
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
    Constructs a 7-input bit-counting circuit using only AND, OR, NOT gates.
    Returns the output of each gate as a list of 0/1 bits.
    """
    n = 7
    if not isinstance(circuit_input, list) or len(circuit_input) != n or any(x not in (0, 1) for x in circuit_input):
        return "Error: Input must be a list of 7 bits (0 or 1)."
    gates = []
    # Helper to build XOR using only AND, OR, NOT
    # a xor b = (not a and b) or (not b and a)
    def xor(a, b, wire_type_a, wire_type_b, offset):
        # Returns: list of gates, output index (1-based, relative to all gates)
        # offset: current number of gates before this block
        # a, b: indices (1-based) of inputs
        # wire_type_a, wire_type_b: 0 for input wire, 1 for gate output
        # Build:
        # not_a = NOT a
        # not_b = NOT b
        # t1 = AND(not_a, b)
        # t2 = AND(not_b, a)
        # out = OR(t1, t2)
        gates = []
        # not_a
        gates.append(('NOT', (wire_type_a, a)))
        not_a_idx = offset + len(gates)
        # not_b
        gates.append(('NOT', (wire_type_b, b)))
        not_b_idx = offset + len(gates)
        # t1 = AND(not_a, b)
        gates.append(('AND', (1, not_a_idx), (wire_type_b, b)))
        t1_idx = offset + len(gates)
        # t2 = AND(not_b, a)
        gates.append(('AND', (1, not_b_idx), (wire_type_a, a)))
        t2_idx = offset + len(gates)
        # out = OR(t1, t2)
        gates.append(('OR', (1, t1_idx), (1, t2_idx)))
        out_idx = offset + len(gates)
        return gates, out_idx

    # Helper to build AND
    def and_gate(a, b, wire_type_a, wire_type_b):
        return [('AND', (wire_type_a, a), (wire_type_b, b))]

    # We will build a ripple-carry adder for 7 bits, outputting the sum in binary (3 bits)
    # We'll use a chain of full adders, each adding one input bit to the sum so far
    # Each full adder: sum = a xor b xor c, carry = (a and b) or (b and c) or (a and c)
    # We'll use only AND, OR, NOT, and build XOR as above

    # We'll keep track of the indices of the current sum bits (s0, s1, s2)
    # At the start, sum = 0, so s0 = 0, s1 = 0, s2 = 0 (represented as input wires 0)
    # But since we need to use only input wires and gate outputs, we need to initialize sum bits as 0
    # We'll use three constant-0 wires by adding three NOT gates on input wire 1 and ANDing with input wire 1 (if input[0]==0, this is always 0)
    # But since input[0] could be 1, we need a guaranteed 0. Instead, we can use NOT(OR(all inputs)), then AND with NOT(OR(all inputs)) to get 0
    # But for simplicity, let's just use input[0] as the first bit, and add the rest

    # We'll use a ripple-carry adder: sum = input[0] + input[1] + ... + input[6]
    # We'll build the adder step by step

    # To keep track of gate indices
    gate_idx = 0

    # First, sum = input[0]
    # sum0 = input[0]
    # carry0 = 0 (we need a constant 0)
    # Let's build a constant 0: NOT(OR(all inputs)) AND (OR(all inputs))
    # OR all inputs
    or_inputs = []
    for i in range(n-1):
        if i == 0:
            gates.append(('OR', (0, 1), (0, 2)))
            or_inputs.append(len(gates))
        else:
            gates.append(('OR', (1, or_inputs[-1]), (0, i+2)))
            or_inputs.append(len(gates))
    # NOT(OR(all inputs))
    gates.append(('NOT', (1, or_inputs[-1])))
    not_or_idx = len(gates)
    # AND(NOT(OR(all inputs)), OR(all inputs)) = 0 always
    gates.append(('AND', (1, not_or_idx), (1, or_inputs[-1])))
    const0_idx = len(gates)
    # Now, const0_idx is a constant 0

    # sum0 = input[0]
    sum_idx = [1]  # input wire 1
    sum_type = [0]
    # carry0 = const0_idx (gate output)
    carry_idx = [const0_idx]
    carry_type = [1]

    # Now, for each input[1] to input[6], add to the sum
    for i in range(1, n):
        # Full adder: sum = a xor b xor c, carry = (a and b) or (b and c) or (a and c)
        # a = sum_idx[-1], b = input[i], c = carry_idx[-1]
        # We'll first compute sum = sum_prev xor input[i] xor carry_prev
        # First, sum_prev xor input[i]
        xor1_gates, xor1_idx = xor(sum_idx[-1], i+1, sum_type[-1], 0, len(gates))
        gates.extend(xor1_gates)
        # (xor1_idx is the output of sum_prev xor input[i])
        # Now, sum = xor1 xor carry_prev
        xor2_gates, xor2_idx = xor(xor1_idx, carry_idx[-1], 1, carry_type[-1], len(gates))
        gates.extend(xor2_gates)
        # Now, compute carry = (sum_prev and input[i]) or (input[i] and carry_prev) or (sum_prev and carry_prev)
        # t1 = sum_prev and input[i]
        gates.extend(and_gate(sum_idx[-1], i+1, sum_type[-1], 0))
        t1_idx = len(gates)
        # t2 = input[i] and carry_prev
        gates.extend(and_gate(i+1, carry_idx[-1], 0, carry_type[-1]))
        t2_idx = len(gates)
        # t3 = sum_prev and carry_prev
        gates.extend(and_gate(sum_idx[-1], carry_idx[-1], sum_type[-1], carry_type[-1]))
        t3_idx = len(gates)
        # carry = t1 or t2
        gates.append(('OR', (1, t1_idx), (1, t2_idx)))
        or1_idx = len(gates)
        # carry = or1 or t3
        gates.append(('OR', (1, or1_idx), (1, t3_idx)))
        carry_out_idx = len(gates)
        # Update sum and carry
        sum_idx.append(xor2_idx)
        sum_type.append(1)
        carry_idx.append(carry_out_idx)
        carry_type.append(1)

    # After the loop, sum_idx[-1] is the least significant bit of the sum (S0)
    # To get the full count in binary, we need to extract the bits from the final sum and carries
    # For 7 bits, the sum can be up to 7 (111 in binary), so 3 bits: S2 S1 S0
    # The final sum_idx and carry_idx contain the necessary bits:
    # S0: sum_idx[-1]
    # S1: carry_idx[-1] (but this is the carry out of the last adder, which is S2)
    # To get S1, we need to track the second-to-last carry
    # S2: carry_idx[-1]
    # S1: sum of carries at the second-to-last stage
    # Actually, for a ripple-carry adder, the sum bits are the outputs of each adder's sum, and the final carry is the MSB

    # Let's collect the outputs:
    # S0: sum of all bits mod 2 (sum_idx[-1])
    # S1: sum of all bits // 2 mod 2 (carry_idx[-2])
    # S2: sum of all bits // 4 mod 2 (carry_idx[-1])
    # So, output bits: [S2, S1, S0] = [carry_idx[-1], carry_idx[-2], sum_idx[-1]]

    # For the blackbox, we return all gate outputs (simulate_circuit returns all gate outputs)
    m = len(gates)
    output = simulate_circuit(n, m, circuit_input, gates)
    return output

def parse_input_bits(player_output, n=7):
    """
    Try to parse a list of 0/1 bits from the player's output.
    Accepts formats like: [0,1,1,0,0,1,0] or 0 1 1 0 0 1 0 or 0110010
    Returns: list of 0/1 ints, or None if parsing fails
    """
    # Try to find a list of 0/1s
    # 1. [0,1,1,0,0,1,0]
    m = re.findall(r'\[([01][,\s]*){7}\]', player_output)
    if m:
        s = re.search(r'\[([01][,\s]*){7}\]', player_output)
        if s:
            bits = re.findall(r'[01]', s.group())
            if len(bits) == n:
                return [int(b) for b in bits]
    # 2. 0 1 1 0 0 1 0
    bits = re.findall(r'\b[01]\b', player_output)
    if len(bits) == n:
        return [int(b) for b in bits]
    # 3. 0110010
    bits = re.findall(r'[01]', player_output)
    if len(bits) == n:
        return [int(b) for b in bits]
    return None

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    n = 7
    rounds = int(max_turns)
    blackbox_output = f"Game start! You are interacting with a blackbox boolean circuit with {n} input bits. In each round, submit a list of 7 bits (0 or 1) as your input, and you will receive the outputs of all gates in the circuit. You have {rounds} rounds. Please enter your first input."
    for turn in range(rounds):
        # Append remaining rounds info
        blackbox_output += f"\nRounds remaining: {rounds - turn}"
        player_output = player.normal_output(blackbox_output)
        # Try to parse input bits
        circuit_input = parse_input_bits(player_output, n)
        if circuit_input is not None:
            # Valid input, run blackbox
            blackbox_result = blackbox(circuit_input)
            if isinstance(blackbox_result, str):
                # Error in blackbox
                blackbox_output = f"Error: {blackbox_result}\nPlease enter a list of 7 bits (0 or 1)."
            else:
                # Output is a list of gate outputs
                blackbox_output = f"Gate outputs: {blackbox_result}"
        else:
            blackbox_output = "Invalid input format. Please enter a list of 7 bits (0 or 1), e.g., [0,1,1,0,0,1,0] or 0 1 1 0 0 1 0 or 0110010."
    # Final answer
    blackbox_output += "\nGame over. Please provide your final guess for the function of the circuit."
    player_output = player.normal_output(blackbox_output)
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), 
         args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
