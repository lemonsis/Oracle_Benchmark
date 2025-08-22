from pathlib import Path

class PathManager:
    def __init__(self):
        self.base_path = '.'
        self.base_path = Path(self.base_path)

        # paths for test
        self.test_path = self.base_path / 'test'

        # paths for natural language task descrption and prompt
        self.task_path = self.base_path / 'task'

        # paths for platform
        self.platform_path = self.base_path / 'platforms'

        # paths for logs
        self.logs_path = self.base_path / 'logs'
        
        # paths for interaction history
        self.history_path = self.base_path / 'history'

        # paths for results
        self.result_path = self.base_path / 'results'

        # paths for baseline
        self.baseline_path = self.base_path / 'baseline'