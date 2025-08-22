import os
import sys
current_path = os.path.abspath(__file__)
oracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path))))
if oracle_path not in sys.path:
    sys.path.insert(0, oracle_path)
from eva_models import ReasoningLLM

def blackbox(truth, query):
    # truth: string, 7 lines, each line 7 chars, only A, B, C, . and O
    # query: string, expected format: "(x, y)" where x and y are integers 1-7

    # Validate query format
    query = query.strip()
    if not (query.startswith("(") and query.endswith(")")):
        return "Query format error: Please use the format (x, y) where x and y are integers from 1 to 7."
    try:
        inner = query[1:-1].split(",")
        if len(inner) != 2:
            return "Query format error: Please use the format (x, y) where x and y are integers from 1 to 7."
        x = int(inner[0].strip())
        y = int(inner[1].strip())
    except Exception:
        return "Query format error: Please use the format (x, y) where x and y are integers from 1 to 7."

    if not (1 <= x <= 7 and 1 <= y <= 7):
        return "Query out of bounds: x and y must be between 1 and 7 (inclusive)."

    # Parse truth into grid
    lines = [line.strip() for line in truth.strip().split('\n') if line.strip()]
    if len(lines) != 7 or any(len(line) != 7 for line in lines):
        return "Internal error: truth format is invalid."

    # Convert to 0-based index
    row = y - 1
    col = x - 1
    cell = lines[row][col]
    if cell in ('A', 'B', 'C', 'O'):
        return "hit"
    else:
        return "miss"

def check_answer_format(answer):
    # answer: string, 7 lines, each line 7 chars, only A, B, C, .
    lines = [line.strip() for line in answer.strip().split('\n') if line.strip()]
    if len(lines) != 7:
        return False
    for line in lines:
        if len(line) != 7:
            return False
        for c in line:
            if c not in ('A', 'B', 'C', '.'):
                return False

    # Check ship counts and shapes
    from collections import Counter, deque

    grid = [list(line) for line in lines]
    ship_counts = Counter()
    visited = [[False]*7 for _ in range(7)]
    ships = {'A': [], 'B': [], 'C': []}

    for i in range(7):
        for j in range(7):
            if grid[i][j] in ('A', 'B', 'C') and not visited[i][j]:
                ch = grid[i][j]
                # BFS to find the full ship
                q = deque()
                q.append((i, j))
                visited[i][j] = True
                coords = [(i, j)]
                while q:
                    ci, cj = q.popleft()
                    for di, dj in [(-1,0),(1,0),(0,-1),(0,1)]:
                        ni, nj = ci+di, cj+dj
                        if 0<=ni<7 and 0<=nj<7 and not visited[ni][nj] and grid[ni][nj]==ch:
                            visited[ni][nj]=True
                            q.append((ni, nj))
                            coords.append((ni, nj))
                ships[ch].append(coords)

    # There must be exactly 1 A, 1 B, 1 C ship
    if len(ships['A']) != 1 or len(ships['B']) != 1 or len(ships['C']) != 1:
        return False

    # Check sizes
    if len(ships['A'][0]) != 3 or len(ships['B'][0]) != 4 or len(ships['C'][0]) != 5:
        return False

    # Check that each ship is straight (horizontal or vertical)
    for ch, size in [('A',3),('B',4),('C',5)]:
        coords = ships[ch][0]
        rows = set(i for i,j in coords)
        cols = set(j for i,j in coords)
        if not (len(rows)==1 or len(cols)==1):
            return False
        # Check contiguous
        if len(rows)==1:
            js = sorted(j for i,j in coords)
            if js != list(range(min(js), min(js)+size)):
                return False
        else:
            is_ = sorted(i for i,j in coords)
            if is_ != list(range(min(is_), min(is_)+size)):
                return False

    # Check no overlap (already ensured by BFS)
    # Check only allowed characters
    for i in range(7):
        for j in range(7):
            if grid[i][j] not in ('A','B','C','.'):
                return False

    return True

def main(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, failure_num, output_dir, max_turns, version, mode, thinking_mode):
    player = ReasoningLLM(model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode)
    player.evaluate(failure_num, version, max_turns)
    player.save_history(output_dir, version)

if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], args[2], args[3], int(args[4]), args[5], args[6], int(args[7]), args[8], int(args[9]), int(args[10]), args[11], bool(eval(args[12])))