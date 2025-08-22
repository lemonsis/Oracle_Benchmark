'''Code Intent Inference'''
def get_local_variables(query_idx):

    import inspect
    frame = inspect.currentframe().f_back
    
    local_vars = frame.f_locals
    
    query_iter = local_vars.get('iter', 0)
    target_query_idx = local_vars.get('idx', 0)

    
    if not hasattr(get_local_variables, 'counters'):
        get_local_variables.counters = {}
        get_local_variables.max_visits = {}
    
    if query_idx not in get_local_variables.counters:
        get_local_variables.counters[query_idx] = 0
        get_local_variables.max_visits[query_idx] = 0
    
    get_local_variables.counters[query_idx] += 1
    current_count = get_local_variables.counters[query_idx]
    
    get_local_variables.max_visits[query_idx] = max(
        get_local_variables.max_visits[query_idx],
        get_local_variables.counters[query_idx]
    )
    
    if query_idx == target_query_idx and current_count == query_iter:
        x = []
        for var_name, var_value in local_vars.items():
            if not var_name.startswith('__') and var_name != 'idx' and var_name != 'iter':
                x.append(f"name={var_name}, value={var_value}, type={type(var_value).__name__}")
        print(str(x))

def check_query_validity(idx, iter):
    if idx not in get_local_variables.max_visits:
        print(f"Checkpoint {idx} does not exist or cannot be queried at current state")
    else:
        max_visits = get_local_variables.max_visits[idx]
        if iter > max_visits:
            print(f"Query iteration {iter} exceeds maximum possible visits {max_visits} for checkpoint {idx}")

def get_ckpt_numbers(blackbox, get_local_variables):
    import inspect
    source = inspect.getsource(blackbox)
    count = source.count(get_local_variables.__name__ + "(")
    return count

def get_function_params(func):
    import inspect
    from typing import get_type_hints

    signature = inspect.signature(func)
    type_hints = get_type_hints(func)
    
    params_info = []
    for param_name, param in signature.parameters.items():
        param_type = type_hints.get(param_name, None)
        if param_name == 'idx' or param_name == 'iter':
            continue
        else:
            params_info.append({'name': param_name, 'type': param_type})
    return params_info

from io import StringIO
from contextlib import redirect_stdout

def capture_print(func):
    def wrapper(*args, **kwargs):
        string_io = StringIO()
        with redirect_stdout(string_io):
            func(*args, **kwargs)
            output = string_io.getvalue().strip()
        return output
    return wrapper

_DEBUGGED_FUNCTION_REF = None
_DEBUGGED_FUNCTION_MARKER_ATTR_NAME = None

def set_current_debug_target(func_ref, marker_attr_name):
    """Sets the target function and its marker attribute name for reset."""
    global _DEBUGGED_FUNCTION_REF, _DEBUGGED_FUNCTION_MARKER_ATTR_NAME
    _DEBUGGED_FUNCTION_REF = func_ref
    _DEBUGGED_FUNCTION_MARKER_ATTR_NAME = marker_attr_name

def reset_debugger_state():
    """
    Resets the global state for get_local_variables and
    the specific marker attribute of the currently targeted debug function.
    """
    global _DEBUGGED_FUNCTION_REF, _DEBUGGED_FUNCTION_MARKER_ATTR_NAME
    
    # Reset state for get_local_variables
    get_local_variables.counters = {}
    get_local_variables.max_visits = {}

    # Reset state for the specific recursive function being debugged
    if _DEBUGGED_FUNCTION_REF and _DEBUGGED_FUNCTION_MARKER_ATTR_NAME:
        if hasattr(_DEBUGGED_FUNCTION_REF, _DEBUGGED_FUNCTION_MARKER_ATTR_NAME):
            delattr(_DEBUGGED_FUNCTION_REF, _DEBUGGED_FUNCTION_MARKER_ATTR_NAME)
            # print(f"DEBUG: Deleted {_DEBUGGED_FUNCTION_MARKER_ATTR_NAME} from {_DEBUGGED_FUNCTION_REF.__name__}") # For debugging reset
    _DEBUGGED_FUNCTION_REF = None # Clear after use or require setting each time
    _DEBUGGED_FUNCTION_MARKER_ATTR_NAME = None


'''Circuit Rule Inference'''

'''
    the function return a list of the gates' output, or a string of error message
    n: number of inputs wires
    m: number of gates
    gates: a list of tuples, each tuple contains the gate type and its inputs
           gate type: 'AND', 'OR', 'NOT'
           inputs: (0, i) means the input wire i
           (1, j) means the output of gate j
           e.g. ('AND', (0, 1), (1, 2)) means AND gate taking input wires 1 and the gate 2
           e.g. ('NOT', (1, 3)) means NOT gate taking the output of gate 3
    Example usage:
    gates = [
        ('AND', (0, 1), (0, 2)),
        ('AND', (0, 3), (1, 1)),
        ('OR', (0, 4), (1, 2)),
        ('NOT', (1, 3)),
        ('NOT', (0, 5))
    ]
    input = [1, 1, 0, 1, 0]
    print(simulate_circuit(5, 5, input, gates))
'''
def simulate_circuit(n, m, input_wires, gates) -> str | list:
    # Validate inputs
    if len(input_wires) != n:
        return f"Error: Expected {n} input wires, got {len(input_wires)}"

    if len(gates) != m:
        return f"Error: Expected {m} gates, got {len(gates)}"

    # Initialize gate outputs
    gate_outputs = [None] * m

    # Process each gate
    for i, gate in enumerate(gates):
        gate_type = gate[0]
        gate_inputs = gate[1:]

        # Validate gate type
        if gate_type not in ['AND', 'OR', 'NOT']:
            return f"Error: Invalid gate type '{gate_type}' at gate {i+1}"

        # Validate NOT gate has exactly one input
        if gate_type == 'NOT' and len(gate_inputs) != 1:
            return f"Error: NOT gate {i+1} must have exactly one input"

        # Validate AND/OR gates have exactly two inputs
        if gate_type in ['AND', 'OR'] and len(gate_inputs) != 2:
            return f"Error: {gate_type} gate {i+1} must have exactly two inputs"
        # Get input values for this gate
        input_values_for_gate = []
        for input_type, input_idx in gate_inputs:
            # Input from wire
            if input_type == 0:
                if not (1 <= input_idx <= n):
                    return f"Error: Gate {i+1} references invalid input wire {input_idx}"
                input_values_for_gate.append(input_wires[input_idx-1])
            # Input from another gate
            elif input_type == 1:
                if not (1 <= input_idx <= m):
                    return f"Error: Gate {i+1} references invalid gate {input_idx}"
                if input_idx >= i+1:
                    return f"Error: Gate {i+1} references gate {input_idx} which is not smaller than itself"
                input_values_for_gate.append(gate_outputs[input_idx-1])
            else:
                return f"Error: Invalid input type {input_type} for gate {i+1}"


        # Compute gate output
        if gate_type == 'AND':
            gate_outputs[i] = int(input_values_for_gate[0] and input_values_for_gate[1])
        elif gate_type == 'OR':
            gate_outputs[i] = int(input_values_for_gate[0] or input_values_for_gate[1])
        elif gate_type == 'NOT':
            gate_outputs[i] = int(not input_values_for_gate[0])

    return gate_outputs