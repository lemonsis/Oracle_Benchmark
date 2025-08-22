import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM

def blackbox(plaintext):
    # Helper functions
    def prepare_grid(keyword):
        # Remove duplicates, replace J with I, and build the grid
        seen = set()
        key = []
        for c in keyword.upper():
            if c == 'J':
                c = 'I'
            if c not in seen and c.isalpha():
                seen.add(c)
                key.append(c)
        for c in 'ABCDEFGHIKLMNOPQRSTUVWXYZ':  # J is omitted
            if c not in seen:
                key.append(c)
        grid = [key[i*5:(i+1)*5] for i in range(5)]
        return grid

    def find_position(grid, char):
        # char is uppercase
        for row in range(5):
            for col in range(5):
                if grid[row][col] == char:
                    return row, col
        return None

    def process_text(text):
        # Remove spaces, keep only letters, replace J with I
        result = []
        for c in text:
            if c.isalpha():
                if c.upper() == 'J':
                    result.append('I' if c.isupper() else 'i')
                else:
                    result.append(c)
        return result

    def create_digraphs(text):
        digraphs = []
        i = 0
        while i < len(text):
            a = text[i]
            if i+1 < len(text):
                b = text[i+1]
                if a.lower() == b.lower():
                    digraphs.append((a, 'X' if a.isupper() else 'x'))
                    i += 1
                else:
                    digraphs.append((a, b))
                    i += 2
            else:
                digraphs.append((a, 'X' if a.isupper() else 'x'))
                i += 1
        return digraphs

    def encrypt_pair(a, b, grid):
        # Determine case
        a_upper = a.upper()
        b_upper = b.upper()
        row_a, col_a = find_position(grid, 'I' if a_upper == 'J' else a_upper)
        row_b, col_b = find_position(grid, 'I' if b_upper == 'J' else b_upper)
        if row_a is None or row_b is None:
            return a, b  # Should not happen
        if row_a == row_b:
            # Same row: replace with letter to the right
            new_a = grid[row_a][(col_a+1)%5]
            new_b = grid[row_b][(col_b+1)%5]
        elif col_a == col_b:
            # Same column: replace with letter below
            new_a = grid[(row_a+1)%5][col_a]
            new_b = grid[(row_b+1)%5][col_b]
        else:
            # Rectangle: swap columns
            new_a = grid[row_a][col_b]
            new_b = grid[row_b][col_a]
        # Restore case
        new_a = new_a if a.isupper() else new_a.lower()
        new_b = new_b if b.isupper() else new_b.lower()
        return new_a, new_b

    # Main Playfair encryption
    keyword = 'SECURITY'
    grid = prepare_grid(keyword)
    # Keep track of spaces to re-insert them
    space_indices = [i for i, c in enumerate(plaintext) if c == ' ']
    # Remove spaces and process text
    processed = process_text(plaintext)
    digraphs = create_digraphs(processed)
    encrypted = []
    for a, b in digraphs:
        ea, eb = encrypt_pair(a, b, grid)
        encrypted.append(ea)
        encrypted.append(eb)
    # Re-insert spaces at original positions
    ciphertext_chars = []
    j = 0
    for i in range(len(plaintext)):
        if plaintext[i] == ' ':
            ciphertext_chars.append(' ')
        elif j < len(encrypted):
            ciphertext_chars.append(encrypted[j])
            j += 1
    # If there are leftover encrypted chars (shouldn't happen), append them
    while j < len(encrypted):
        ciphertext_chars.append(encrypted[j])
        j += 1
    return ''.join(ciphertext_chars)

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    blackbox_output = f'You have {max_turns} interaction turns to understand the black-box. Now the interaction starts. Only output the value and DO NOT contain any unrelated text.'
    for i in range(max_turns+1):
        player_output = player.normal_output(blackbox_output)
        # Only pass the player's output (plaintext) to blackbox, stripping any whitespace and newlines
        blackbox_input = ''.join([c for c in player_output if c.isalpha() or c == ' '])
        blackbox_output = f'<Current Turn: {i+1}, {max_turns-(i+1)} Turns Remaining> ' + blackbox(blackbox_input)
    player.evaluate(failure_num, version)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))
