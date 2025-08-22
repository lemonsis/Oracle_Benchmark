import argparse
from paths import PathManager
import os
from auto_generation import Platform, PolishModel, TestSamplesGenerator
import subprocess
import logging
import sys
import multiprocessing

'''if you want to add new model family and model name, please add them in both the following function and argparse choices.'''
def get_model_name(model_family):
    if model_family == 'gpt':
        return ['o1', 'o3', 'o3-mini','o4-mini']
    elif model_family == 'claude':
        return ['claude-3.5-sonnet', 'claude-3.7-sonnet', 'claude-4-sonnet', 'claude-3.7-sonnet_thinking', 'claude-4-sonnet_thinking'] 
    elif model_family == 'gemini':
        return ['gemini-2.0-flash', 'gemini-2.5-flash', 'gemini-2.5-flash_thinking', 'gemini-2.5-pro_thinking'] 
    elif model_family == 'llama':
        return ['llama-4-marverick', 'llama-4-scout']
    elif model_family == 'qwen':
        return ['qwen3-32b_thinking', 'qwen3-235b-a22b_thinking', 'qwen-plus_thinking', 'qwq-plus_thinking']
    elif model_family == 'deepseek':
        return ['deepseek-v3', 'deepseek-r1']
    else:
        raise ValueError(f"Unknown model family: {model_family}")
    
def map_model_name_to_api_name(model_name: str) -> str:
    if model_name == 'gpt-4o':
        return 'gpt-4o-2024-08-06'
    elif model_name == 'gpt-4o-mini':
        return 'gpt-4o-mini-2024-07-18'
    elif model_name == 'gpt-4.1':
        return 'gpt-4.1-2025-04-14'
    elif model_name == 'gpt-4.1-mini':
        return 'gpt-4.1-mini-2025-04-14'
    elif model_name == 'o1':
        return 'o1-2024-12-17'
    elif model_name == 'o3-mini':
        return 'o3-mini-2025-01-31'
    elif model_name == 'o3':
        return 'o3-2025-04-16'
    elif model_name == 'o3-pro':
        return 'o3-pro-2025-06-10'
    elif model_name == 'o4-mini':
        return 'o4-mini-2025-04-16'
    
    elif model_name == 'claude-3-opus':
        return 'claude-3-opus-20240229'
    elif model_name == 'claude-3.5-haiku':
        return 'claude-3-5-haiku-20241022'
    elif model_name == 'claude-3.5-sonnet':
        return 'claude-3-5-sonnet-20241022'
    elif model_name == 'claude-3.7-sonnet':
        return 'claude-3-7-sonnet-20250219'
    elif model_name == 'claude-4-sonnet':
        return 'claude-sonnet-4-20250514'
    elif model_name == 'claude-4-opus':
        return 'claude-opus-4-20250514'
    
    elif model_name == 'gemini-2.5-pro':
        return 'gemini-2.5-pro'
    elif model_name == 'gemini-2.5-flash':
        return 'gemini-2.5-flash'
    elif model_name == 'gemini-2.0-flash':
        return 'gemini-2.0-flash'
    elif model_name == 'gemini-1.5-pro':
        return 'gemini-1.5-pro'
    
    elif model_name == 'qwen-max':
        return 'qwen-max'
    elif model_name == 'qwen-plus':
        return 'qwen-plus-latest'
    elif model_name == 'qwen3-235b-a22b':
        return 'qwen3-235b-a22b'
    elif model_name == 'qwen3-32b':
        return 'qwen3-32b'
    elif model_name == 'qwq-plus':
        return 'qwq-plus'
    elif model_name == 'qwq-32b':
        return 'qwq-32b'
    
    elif model_name == 'deepseek-r1':
        return 'deepseek-reasoner'
    elif model_name == 'deepseek-v3':
        return 'deepseek-chat'
    
    elif model_name == 'llama-4-scout':
        return 'meta-llama/llama-4-scout'
    elif model_name == 'llama-4-marverick':
        return 'meta-llama/llama-4-maverick'

    else:
        raise ValueError(f"Unsupported model name: {model_name}")

def run_evaluation(family, model, task_folder, eva_mode, n_runs, difficulty_folder, task_id_stem, \
    k, history_path, max_turns, thinking_mode, platform_path):
    command = [
        'python',
        platform_path / task_folder / difficulty_folder / f'{task_id_stem}_final.py',
        family,
        map_model_name_to_api_name(model),
        task_folder,
        eva_mode,
        str(n_runs),
        difficulty_folder,
        task_id_stem,
        str(k),
        str(history_path),
        str(max_turns),
        str(1),
        'evaluate',
        str(thinking_mode)
    ]

    if thinking_mode:
        task_identifier = f"({model}_thinking) on {task_folder}/{difficulty_folder}/{task_id_stem}.json"
        logging.info(f"Starting evaluation for {task_identifier}")
    else:
        task_identifier = f"({model}) on {task_folder}/{difficulty_folder}/{task_id_stem}.json"
        logging.info(f"Starting evaluation for {task_identifier}")

    result = subprocess.run(
        command,
        capture_output=False,
        text=True,
        encoding='utf-8' 
    )
    return task_identifier, result.stdout, result.stderr, result.returncode


def main():
    paths = PathManager()
    parser = argparse.ArgumentParser(description='Oracle-Benchmark')
    evaluator_group = parser.add_argument_group('eva_model')
    evaluator_group.add_argument('--eva_model_family', type=str, default='gpt', choices=['gpt', 'claude', 'gemini', 'llama', 'qwen', 'deepseek', 'all'], required=True, help='Model family to evaluate.')
    evaluator_group.add_argument('--eva_model_name', type=str, choices=['gpt-4o', 'gpt-4o-mini', 'gpt-4.1', 'gpt-4.1-mini', 'o1', 'o3-mini', 'o3', 'o4-mini',
                                                                    'claude-3.5-sonnet', 'claude-3.5-haiku', 'claude-3.7-sonnet', 'claude-4-sonnet', 'claude-4-opus',
                                                                    'gemini-2.0-flash', 'gemini-2.5-flash', 'gemini-2.5-pro',
                                                                    'qwen-max', 'qwen-plus', 'qwq-plus', 'qwen3-235b-a22b', 'qwen3-32b', 'qwq-32b',
                                                                    'llama-4-scout', 'llama-4-marverick',
                                                                    'deepseek-r1', 'deepseek-v3'], help='Model name to evaluate.')
    # some models can choose to open the thinking mode. Default is not using thinking mode.
    evaluator_group.add_argument('--thinking_mode', type=bool, default=False, help='Whether to use thinking mode. Only claude3.7, gemini2.5, and qwen3-series support this. Default is False.')
    evaluator_group.add_argument('--task', type=str, default='circuit', choices=['code', 'encryption', 'puzzle', 'game', 'physics', 'circuit'])
    evaluator_group.add_argument('--task_id', type=str, default=None, help='Task ID to evaluate. If not specified, all tasks in the task folder will be evaluated.')
    evaluator_group.add_argument('--difficulty', type=str, default=None, help='difficulty level to evaluate. If not specified, all difficulties in the task folder will be evaluated.')
    evaluator_group.add_argument('--k', type=int, default=0, help='Number of failures that can be tolerated, k=0 means no failure')
    evaluator_group.add_argument('--n_runs', type=int, default=1, help='Number of evaluation times')
    evaluator_group.add_argument('--eva_mode', type=str, default='normal', choices=['normal', 'concurrent'], help='Evaluation mode. If n_runs>1 or model_name=all, eva_model must be "concurrent"')
    evaluator_group.add_argument('--max_turns', type=int, default=10, help='when exceed max_turns, stop the interaction and start testing')
    evaluator_group.add_argument('--baseline_test', type=bool, default=False, help='baseline test')

    platform_group = parser.add_argument_group('platform')
    platform_group.add_argument('--platformgen_model_family', type=str, default='gemini', choices=['gpt', 'claude', 'gemini'], help='Model family to generate platform.')  # thinking mode for claude
    platform_group.add_argument('--platformgen_model_name', type=str, default='gemini-2.5-pro', choices=['gpt-4.1','claude-3.7-sonnet', 'claude-4-sonnet', 'gemini-2.5-pro', 'gemini-2.5-flash'], help='Model name to generate platform.')
    platform_group.add_argument('--platformpolish_model_family', type=str, default='gemini', choices=['gpt', 'claude', 'gemini'], help='Model family to polish platform.')
    platform_group.add_argument('--platformpolish_model_name', type=str, default='gemini-2.5-pro', choices=['claude-3.7-sonnet', 'claude-4-sonnet', 'gemini-2.5-pro', 'gpt-4.1'], help='Model name to polish platform.')
    platform_group.add_argument('--max_polish_times', type=int, default=3, help='Number of times to polish the platform')

    test_group = parser.add_argument_group('test_sample_generator')
    test_group.add_argument('--test_sample_generator_model_family', type=str, default='gpt', choices=['gpt'], help='Model family to generate test sample.')
    test_group.add_argument('--test_sample_generator_model_name', type=str, default='gpt-4.1', choices=['gpt-4.1','gpt-4o'], help='Model name to generate test sample.')

    args = parser.parse_args()

    # Step 0: A model must pass through baseline test first
    if args.baseline_test:
        for task_folder in os.listdir(paths.platform_path):
            if task_folder == 'code' or task_folder == 'encryption' or task_folder == 'physics':
                if os.path.isdir(os.path.join(paths.platform_path, task_folder)):
                    for task_id in os.listdir(paths.platform_path / task_folder / 'baseline'):
                        if task_id.endswith('.py'):
                            logging.info(f"Baseline test {task_folder}/{'baseline'}/{task_id}")
                            result = subprocess.run(
                                        [
                                            'python', 
                                            paths.platform_path / task_folder / 'baseline' / task_id,
                                            args.eva_model_family,
                                            map_model_name_to_api_name(args.eva_model_name),
                                            task_folder,
                                            args.eva_mode,
                                            str(1),
                                            'baseline',
                                            task_id.replace('_final.py', ''),
                                            str(0),
                                            paths.history_path,
                                            str(12),
                                            str(1),
                                            'evaluate',
                                            str(args.thinking_mode)
                                        ], 
                                        capture_output=False, 
                                        text=True
                                    )
                            running_errors = result.stderr if result.returncode != 0 else ''
                            output = result.stdout
        sys.exit(0)
    
    # Step 1: generate test samples by task
    for task_folder in os.listdir(paths.task_path):
        '''For code, generate test samples in step 2, so skip it here.'''
        if task_folder != args.task or task_folder == 'code': continue
        if os.path.isdir(os.path.join(paths.task_path, task_folder)):
            test_sample_generator = TestSamplesGenerator(
                task=task_folder, 
                model_family=args.test_sample_generator_model_family, 
                model_name=map_model_name_to_api_name(args.test_sample_generator_model_name),
                max_turns=args.max_turns
            )
            for difficulty_folder in os.listdir(paths.task_path / task_folder):
                if os.path.isdir(os.path.join(paths.task_path / task_folder, difficulty_folder)):
                    for task_id in os.listdir(paths.task_path / task_folder / difficulty_folder):
                        '''For code, generate test samples in step 2, so skip it here.'''
                        if task_id.endswith('.json') and not os.path.exists(paths.test_path / task_folder / difficulty_folder / task_id):
                            logging.info(f"Generating test samples for {task_folder}/{difficulty_folder}/{task_id}")
                            test_sample_generator.generate(
                                difficulty=difficulty_folder, 
                                task_id=task_id.replace('.json', ''),
                                version=None
                            )
    
    # Step 2: use LLM to generate black-box code and player-blackbox interaction platform simutaneously
    for task_folder in os.listdir(paths.task_path):
        if task_folder != args.task: continue
        if os.path.isdir(os.path.join(paths.task_path, task_folder)):
            platform = Platform(
                task=task_folder, 
                platformgen_model_family=args.platformgen_model_family, 
                platformgen_model_name=map_model_name_to_api_name(args.platformgen_model_name),
            )
            bug_fixer = PolishModel(
                task=task_folder,
                model_family=args.platformpolish_model_family,
                model_name=map_model_name_to_api_name(args.platformpolish_model_name),
            )
            for difficulty_folder in os.listdir(paths.task_path / task_folder):
                if os.path.isdir(os.path.join(paths.task_path / task_folder, difficulty_folder)):
                    for task_id in os.listdir(paths.task_path / task_folder / difficulty_folder):
                        if task_id.endswith('.json'):
                            logging.info(f"Generating blackbox and platform for {task_folder}/{difficulty_folder}/{task_id}")
                            if not os.path.exists(paths.platform_path / task_folder / difficulty_folder / f'{task_id.replace(".json", "")}_final.py'):    # DO NOT overwrite the existing code
                                loop_count = 1
                                platform.generate(
                                    difficulty=difficulty_folder, 
                                    task_id=task_id.replace('.json', ''),
                                    version=loop_count
                                )
                                '''For code, generate test samples here'''
                                if args.task == 'code':
                                    test_sample_generator = TestSamplesGenerator(
                                        task=task_folder, 
                                        model_family=args.test_sample_generator_model_family, 
                                        model_name=map_model_name_to_api_name(args.test_sample_generator_model_name),
                                    )
                                    logging.info(f"Generating test samples for {task_folder}/{difficulty_folder}/{task_id}_v{loop_count}")
                                    test_sample_generator.generate(
                                        difficulty=difficulty_folder, 
                                        task_id=task_id.replace('.json', ''),
                                        version=loop_count
                                    )
                                logging.info(f"Generation: Running {task_id.replace('.json', '')}_v{loop_count}.py")
                                result = subprocess.run(
                                    [
                                        'python', 
                                        paths.platform_path / task_folder / difficulty_folder / f'{task_id.replace(".json", "")}_v{loop_count}.py',
                                        args.eva_model_family,
                                        map_model_name_to_api_name(args.eva_model_name),
                                        task_folder,
                                        args.eva_mode,
                                        str(args.n_runs),
                                        difficulty_folder,
                                        task_id.replace('.json', ''),
                                        str(args.k),
                                        paths.logs_path,
                                        str(args.max_turns),
                                        str(loop_count),
                                        'generate',
                                        str(args.thinking_mode)
                                    ], 
                                    capture_output=True, 
                                    text=True
                                )
                                running_errors = result.stderr if result.returncode != 0 else ''
                                
                                while True:
                                    loop_count += 1
                                    if loop_count > args.max_polish_times:
                                        os.rename(
                                            paths.platform_path / task_folder / difficulty_folder / f'{task_id.replace(".json", "")}_v{loop_count-1}.py',
                                            paths.platform_path / task_folder / difficulty_folder / f'{task_id.replace(".json", "")}_final.py'
                                        )
                                        break
                                    response = bug_fixer.polish(
                                        task=task_folder, 
                                        difficulty=difficulty_folder, 
                                        task_id=task_id.replace('.json', ''), 
                                        running_errors=running_errors,
                                        version=loop_count
                                    )
                                    
                                    if response == 'correct':
                                        os.rename(
                                            paths.platform_path / task_folder / difficulty_folder / f'{task_id.replace(".json", "")}_v{loop_count-1}.py',
                                            paths.platform_path / task_folder / difficulty_folder / f'{task_id.replace(".json", "")}_final.py'
                                        )
                                        break
                                    else:
                                        if args.task == 'code':
                                            logging.info(f"Generating test samples for {task_folder}/{difficulty_folder}/{task_id}_v{loop_count}")
                                            test_sample_generator.generate(
                                                difficulty=difficulty_folder, 
                                                task_id=task_id.replace('.json', ''),
                                                version=loop_count
                                            )
                                        result = subprocess.run(
                                            [
                                                'python', 
                                                paths.platform_path / task_folder / difficulty_folder / f'{task_id.replace(".json", "")}_v{loop_count}.py',
                                                args.eva_model_family,
                                                map_model_name_to_api_name(args.eva_model_name),
                                                task_folder,
                                                args.eva_mode,
                                                str(args.n_runs),
                                                difficulty_folder,
                                                task_id.replace('.json', ''),
                                                str(args.k),
                                                paths.logs_path,
                                                str(args.max_turns),
                                                str(loop_count),
                                                'generate',
                                                str(args.thinking_mode)
                                            ], 
                                            capture_output=True, 
                                            text=True
                                        )
                                        running_errors = result.stderr if result.returncode != 0 else ''

    # Step 3: benchmark models
    if args.eva_model_family == 'all':
        assert args.eva_mode == 'concurrent'
        if args.eva_model_name:
            raise ValueError(f"Model name {args.eva_model_name} is not valid when model family is set as all.")

        tasks_to_run = []
        all_model_family = []
        for action in parser._actions:
            if action.dest == 'eva_model_family':
                all_model_family = action.choices
                break
        all_model_family.remove('all')  # remove 'all' from the list\

        print("Collecting tasks for evaluation...")
        for family in all_model_family:
            models = get_model_name(family)
            for model in models:
                task_folder_path = paths.task_path / args.task
                if not os.path.isdir(task_folder_path):
                    logging.warning(f"Task folder {args.task} not found. Skipping.")
                    continue

                for difficulty_folder in os.listdir(task_folder_path):
                    difficulty_folder_path = task_folder_path / difficulty_folder
                    if os.path.isdir(difficulty_folder_path):
                        for task_id_file in os.listdir(difficulty_folder_path):
                            if task_id_file.endswith('.json'):
                                task_id_stem = task_id_file.replace('.json', '')
                                if 'thinking' in model:
                                    args.thinking_mode = True
                                else:
                                    args.thinking_mode = False
                                task_params = (
                                    family,
                                    model.replace('_thinking', ''),
                                    args.task, # task_folder
                                    args.eva_mode,
                                    args.n_runs,
                                    difficulty_folder,
                                    task_id_stem,
                                    args.k,
                                    paths.history_path,
                                    args.max_turns,
                                    args.thinking_mode,
                                    paths.platform_path,
                                )
                                if args.thinking_mode:
                                    if not os.path.exists(os.path.join('results', args.task, difficulty_folder, task_id_stem, map_model_name_to_api_name(model.replace('_thinking', ''))+'_thinking')):
                                        tasks_to_run.append(task_params)
                                else:
                                    if not os.path.exists(os.path.join('results', args.task, difficulty_folder, task_id_stem, map_model_name_to_api_name(model))):
                                        tasks_to_run.append(task_params)

        print(tasks_to_run)
        if not tasks_to_run:
            logging.info("No tasks found to evaluate.")
        else:
            num_processes = 15
            logging.info(f"\nCollected {len(tasks_to_run)} tasks. Starting evaluation using {num_processes} concurrent processes...")
            with multiprocessing.Pool(processes=num_processes) as pool:
                results = pool.starmap(run_evaluation, tasks_to_run)

            print("\n--- All evaluations completed. Final Results: ---")
            for task_identifier, output, running_errors, return_code in results:
                print("=" * 80)
                print(f"Task: {task_identifier}")
                print(f"Return Code: {return_code}")
                print("-" * 20 + " STDOUT " + "-" * 20)
                print(output)
                if running_errors:
                    print("-" * 20 + " STDERR " + "-" * 20)
                    print(running_errors)
                print("=" * 80 + "\n")
        # merge results
        
    else:
        # benchmark models
        for i in range(args.n_runs):
            for task_folder in os.listdir(paths.task_path):
                if task_folder != args.task: continue
                if os.path.isdir(os.path.join(paths.task_path, task_folder)):
                    for difficulty_folder in os.listdir(paths.task_path / task_folder):
                        if args.difficulty != None and difficulty_folder != args.difficulty: continue
                        if os.path.isdir(os.path.join(paths.task_path / task_folder, difficulty_folder)):
                            for task_id in os.listdir(paths.task_path / task_folder / difficulty_folder):
                                if task_id.endswith('.json'):
                                    if args.task_id != None:
                                        if task_id != args.task_id:
                                            continue
                                    logging.info(f"Evaluating {task_folder}/{difficulty_folder}/{task_id}")
                                    result = subprocess.run(
                                                [
                                                    'python', 
                                                    paths.platform_path / task_folder / difficulty_folder / f'{task_id.replace(".json", "")}_final.py',
                                                    args.eva_model_family,
                                                    map_model_name_to_api_name(args.eva_model_name),
                                                    task_folder,
                                                    args.eva_mode,
                                                    str(args.n_runs),
                                                    difficulty_folder,
                                                    task_id.replace('.json', ''),
                                                    str(args.k),
                                                    paths.history_path,
                                                    str(args.max_turns),
                                                    str(i+1),
                                                    'evaluate',
                                                    str(args.thinking_mode)
                                                ], 
                                                capture_output=False, 
                                                text=True
                                            )
                                    running_errors = result.stderr if result.returncode != 0 else ''
                                    print(running_errors)
                                    output = result.stdout
                                    print(output)

if __name__ == "__main__":
    main()