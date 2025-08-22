
import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM

def blackbox(plaintext):
    # Remove non-letter characters and ignore spaces
    """
    Encrypts plaintext using a zigzag cipher with a 999x6 table.

    Args:
        plaintext: The input string to encrypt.

    Returns:
        The ciphertext string.
    """

    NUM_COLS = 6

    # 1. Preprocess plaintext: remove spaces, keep case
    processed_plaintext = "".join(plaintext.split())
    num_chars = len(processed_plaintext)

    if num_chars == 0:
        return ""

    # 2. Conceptually fill the table
    # Determine the actual number of rows needed in the table
    actual_rows_in_table = (num_chars - 1) // NUM_COLS + 1
    
    # Store the table explicitly for easier access
    # '' denotes an empty cell if a column is shorter than others (not strictly needed here due to fill pattern)
    table = [['' for _ in range(NUM_COLS)] for _ in range(actual_rows_in_table)]
    for i, char_code in enumerate(processed_plaintext):
        row = i // NUM_COLS
        col = i % NUM_COLS
        table[row][col] = char_code
        
    # 3. Determine the starting column for reading
    # This is the rightmost column index that contains any character.
    # If num_chars = 1, initial_read_col = 0.
    # If num_chars <= NUM_COLS, initial_read_col = num_chars - 1.
    # If num_chars > NUM_COLS, initial_read_col = NUM_COLS - 1.
    # This simplifies to:
    initial_read_col = min(NUM_COLS - 1, num_chars - 1)

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
        R_max_overall = (num_chars - 1) // NUM_COLS
        C_last = (num_chars - 1) % NUM_COLS

        if c > C_last:
            # This column 'c' is shorter because it was not part of the last (possibly incomplete) row of filling.
            # So, its characters only go up to the row before R_max_overall.
            max_row_index_for_this_col = R_max_overall - 1
        else:
            # This column 'c' includes characters up to R_max_overall.
            max_row_index_for_this_col = R_max_overall
        
        # All columns processed by this loop are guaranteed to have at least one character
        # because 'c' ranges from initial_read_col (which must have a char if num_chars > 0)
        # down to 0, and row-wise filling ensures no gaps in columns to the left
        # of a filled cell in the same row or previous rows.
        # Thus, max_row_index_for_this_col will be >= 0.

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
                # If current_row is 0 (top) and also max_row_index_for_this_col (bottom),
                # it means it's the only cell. Direction effectively flips.
                if current_row == 0 and current_row == max_row_index_for_this_col:
                    current_direction *= -1 
                elif current_row == 0: # Hit top boundary
                    current_direction = 1  # Change to DOWN
                elif current_row == max_row_index_for_this_col: # Hit bottom boundary
                    current_direction = -1 # Change to UP
                # No change to current_row as we break next
                break 

            # Update row and direction for multi-element columns
            if current_direction == -1:  # Moving UP
                if current_row == 0:  # Hit top boundary
                    current_direction = 1  # Change to DOWN
                    current_row += current_direction # Move to row 1
                else:
                    current_row += current_direction # Move to row - 1
            else:  # Moving DOWN (current_direction == 1)
                if current_row == max_row_index_for_this_col:  # Hit bottom boundary for this column
                    current_direction = -1  # Change to UP
                    current_row += current_direction # Move to max_row_index - 1
                else:
                    current_row += current_direction # Move to row + 1
        
        ciphertext_column_parts.append("".join(current_column_chars))

    # 6. Join column strings with spaces to form the final ciphertext
    return " ".join(ciphertext_column_parts)

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    blackbox_output = f'You have {max_turns} interaction turns to understand the black-box. Now the interaction starts. Only output the value and DO NOT contain any unrelated text.'
    for i in range(max_turns+1):
        player_output = player.normal_output(blackbox_output)
        blackbox_output = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> ' + blackbox(player_output)
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))