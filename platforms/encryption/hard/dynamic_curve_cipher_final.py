
import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM

def blackbox(plaintext):
    """
    Encrypts plaintext by filling it into a table row by row (ignoring spaces),
    then reading it out in a zigzag manner column by column. The number of
    columns k is determined by l (number of letters in plaintext) using k = l % 3 + 3.
    Reading starts from the last letter in the last filled column.
    """
    # 1. Preprocess plaintext: remove spaces, keep case
    processed_plaintext = "".join(plaintext.split())
    l_val = len(processed_plaintext)  # l is the number of letters

    if l_val == 0:
        return ""

    # Determine the number of columns, k
    k_val = (l_val % 3) + 3

    # 2. Conceptually fill the table
    # Determine the actual number of rows needed in the table
    actual_rows_in_table = (l_val - 1) // k_val + 1
    
    # Store the table explicitly for easier access
    table = [['' for _ in range(k_val)] for _ in range(actual_rows_in_table)]
    for i, char_code in enumerate(processed_plaintext):
        row = i // k_val
        col = i % k_val
        table[row][col] = char_code
        
    # 3. Determine the starting column for reading
    # This is the rightmost column index that contains any character.
    initial_read_col = min(k_val - 1, l_val - 1)

    # 4. Initialize reading direction
    # Global direction: -1 for UP, +1 for DOWN.
    # Start by reading "up" from the "last letter" of the first column to be processed.
    current_direction = -1  # UP

    ciphertext_column_parts = []

    # 5. Loop through columns from right-to-left (initial_read_col down to 0)
    for c in range(initial_read_col, -1, -1):
        # Determine the maximum row index for the current column 'c'
        # R_max_overall: highest row index in the entire table that has a character.
        # C_last: column index of the very last character in the plaintext filling.
        R_max_overall = (l_val - 1) // k_val
        C_last = (l_val - 1) % k_val

        if c > C_last:
            # This column 'c' is shorter because it was not part of the last (possibly incomplete) row of filling.
            max_row_index_for_this_col = R_max_overall - 1
        else:
            # This column 'c' includes characters up to R_max_overall.
            max_row_index_for_this_col = R_max_overall
        
        current_column_chars = []
        num_elements_in_this_col = max_row_index_for_this_col + 1

        # Determine the starting row for reading this column based on current_direction
        if current_direction == -1:  # UP
            current_row = max_row_index_for_this_col
        else:  # DOWN (+1)
            current_row = 0
        
        # Read characters in the current column 'c' using zigzag pattern
        for _ in range(num_elements_in_this_col):
            current_column_chars.append(table[current_row][c])

            if num_elements_in_this_col == 1:
                # Single-element column: direction flips for the *next* column.
                if current_row == 0 and current_row == max_row_index_for_this_col: # Only cell
                    current_direction *= -1 
                elif current_row == 0: # Hit top boundary
                    current_direction = 1  # Change to DOWN
                elif current_row == max_row_index_for_this_col: # Hit bottom boundary
                    current_direction = -1 # Change to UP
                break 

            # Update row and direction for multi-element columns
            if current_direction == -1:  # Moving UP
                if current_row == 0:  # Hit top boundary
                    current_direction = 1  # Change to DOWN
                    current_row += current_direction 
                else:
                    current_row += current_direction 
            else:  # Moving DOWN (current_direction == 1)
                if current_row == max_row_index_for_this_col:  # Hit bottom boundary
                    current_direction = -1  # Change to UP
                    current_row += current_direction 
                else:
                    current_row += current_direction 
        
        ciphertext_column_parts.append("".join(current_column_chars))

    # 6. Join column strings with spaces to form the final ciphertext
    return " ".join(ciphertext_column_parts)

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    blackbox_output = f'You have {max_turns} interaction turns to understand the black-box. Now the interaction starts. Only output the value and DO NOT contain any unrelated text.'
    
    for i in range(max_turns):
        player_output = player.normal_output(blackbox_output)
        blackbox_output = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> ' + blackbox(player_output)
    
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))