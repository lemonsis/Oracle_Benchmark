from paths import PathManager
from dotenv import load_dotenv
from openai import OpenAI
from google import genai
from google.genai import types
from anthropic import Anthropic
import os
import json
from pydantic import BaseModel
import logging
from typing import Union

load_dotenv(override=True)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def code_clean(code):
    code = code.replace("```python", "")
    code = code.replace("```", "")
    return code

class Platform:
    def __init__(self, task, platformgen_model_family, platformgen_model_name):
        self.paths = PathManager()
        
        self.task = task
        self.platformgen_model_family = platformgen_model_family
        self.platformgen_model_name = platformgen_model_name

        if self.platformgen_model_family == 'gpt':
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        elif self.platformgen_model_family == 'claude':
            self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        elif self.platformgen_model_family == 'gemini':
            self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        with open(self.paths.platform_path / task / 'platformgen_system_prompt') as f:
            self.platformgen_system_prompt = f.read()
        with open(self.paths.platform_path / task / 'request') as f:
            self.platformgen_initial_prompt = f.read()  # request serves as input prompt for platformgen_model

    '''use LLM to generate the interface of the platform, output the code for the platform'''
    def generate(self, difficulty, task_id, version):
        with open(self.paths.task_path / self.task / difficulty / f'{task_id}.json', 'r', encoding='utf-8') as f:
            information = json.load(f)
        if self.task == 'game':
            instruction = self.platformgen_initial_prompt.format(
                algorithm=information['algorithm'],
                description=information['description'],
                strategy=information['strategy']
            )
        elif self.task == 'code' and 'recursion' in task_id:
            with open(self.paths.platform_path / self.task / 'request_recursion') as f:
                self.platformgen_initial_prompt = f.read()
            instruction = self.platformgen_initial_prompt.format(
                algorithm=information['algorithm'],
                description=information['description'],
            )
        else:
            instruction = self.platformgen_initial_prompt.format(
                algorithm=information['algorithm'],
                description=information['description'],
            )

        if self.platformgen_model_family == 'gpt':
            response = self.client.chat.completions.create(
                model=self.platformgen_model_name,
                messages=[
                    {
                        "role": "system",
                        "content": self.platformgen_system_prompt
                    },
                    {
                        "role": "user",
                        "content": instruction
                    }
                ],
                temperature=0,
            )
            response = response.choices[0].message.content
        elif self.platformgen_model_family == 'claude':
            think = False
            if think:
                response = self.client.messages.create(
                    model=self.platformgen_model_name,
                    system = self.platformgen_system_prompt,
                    messages=[
                        {
                            "role": "user",
                            "content": instruction
                        }
                    ],
                    thinking={
                            "type": "enabled",
                            "budget_tokens": 2000
                    },
                    max_tokens=8192,
                )
                if len(response.content) == 2:
                    response_content = response.content[1].text
                elif len(response.content) == 3:
                    response_content = response.content[2].text
                response = response_content
            else:
                response = self.client.messages.create(
                    model=self.platformgen_model_name,
                    system = self.platformgen_system_prompt,
                    messages=[
                        {
                            "role": "user",
                            "content": instruction
                        }
                    ],
                    temperature=0,
                    max_tokens=8192,
                )
                response = response.content[0].text
        elif self.platformgen_model_family == 'gemini':
            response = self.client.models.generate_content(
                model=self.platformgen_model_name,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_budget=-1),
                    system_instruction=self.platformgen_system_prompt,
                    temperature=0,
                ),
                contents=[instruction]
            )
            response = response.text
        platform_code = code_clean(response)

        output_dir = self.paths.platform_path / self.task / difficulty 
        # import_packages = 'import os \nimport sys \ncurrent_path = os.path.abspath(__file__) \noracle_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_path)))) \nif oracle_path not in sys.path: \n\tsys.path.insert(0, oracle_path) \nfrom ckpt import get_local_variables, check_query_validity, get_ckpt_numbers, get_function_params \nfrom eva_models import ReasoningLLM \nimport re \nimport ast \n'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        with open(output_dir / f'{task_id}_v{version}.py', 'w', encoding='utf-8') as f:
            # f.write(import_packages)
            f.write(platform_code)
        logging.info(f"Platform code generated and saved to {output_dir / f'{task_id}_v{version}.py'}")

 
class PolishModel:
    def __init__(self, task, model_family, model_name):
        self.paths = PathManager()

        self.task = task
        self.model_family = model_family
        self.model_name = model_name

        if self.model_family == 'gpt':
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        elif self.model_family == 'claude':
            self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        elif self.model_family == 'gemini':
            self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        with open(self.paths.platform_path / 'platformpolish_system_prompt', 'r', encoding='utf-8') as f:
            self.system_prompt = f.read()
        with open(self.paths.platform_path / 'platformpolish_initial_prompt_running_errors', 'r', encoding='utf-8') as f:
            self.initial_prompt_running_errors = f.read()
        with open(self.paths.platform_path / 'platformpolish_initial_prompt_logs_1', 'r', encoding='utf-8') as f:
            self.initial_prompt_logs_1 = f.read()
        with open(self.paths.platform_path / 'platformpolish_initial_prompt_logs_2', 'r', encoding='utf-8') as f:
            self.initial_prompt_logs_2 = f.read()

    def polish(self, task, difficulty, task_id, running_errors, version):
        '''if there exist running errors, no log'''
        with open(self.paths.platform_path / task / difficulty / f'{task_id}_v{version-1}.py', 'r', encoding='utf-8') as f:
            current_code = f.read()
        if running_errors != '':
            instruction = self.initial_prompt_running_errors.format(
                current_code=current_code,
                running_errors=running_errors,
            )
        else:
            with open(self.paths.logs_path / task / difficulty / f'{task_id}_logs_v{version-1}.json', 'r', encoding='utf-8') as f:
                interaction_log = json.load(f)
            with open(self.paths.task_path / task / 'task_intro', 'r', encoding='utf-8') as f:
                taskintro = f.read()
            with open(self.paths.task_path / self.task / difficulty / f'{task_id}.json', 'r', encoding='utf-8') as f:
                file = json.load(f)
                a = file['algorithm']
                d = file['description']
            if self.task == 'game' or self.task == 'puzzle':
                taskintro = taskintro.format(
                    algorithm=a,
                    description=d
                )
            instruction = self.initial_prompt_logs_1.format(
                algorithm=a,
                description=d,
                taskintro=taskintro,
                interaction_log=interaction_log,
            )
        if self.model_family == 'gpt':
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": self.system_prompt
                    },
                    {
                        "role": "user",
                        "content": instruction

                    }
                ],
                temperature=0,
            )
            response = response.choices[0].message.content
        elif self.model_family == 'claude':
            response = self.client.messages.create(
                model=self.model_name,
                system=self.system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": instruction
                    }
                ],
                temperature=0,
                max_tokens=8192,
            )
            response = response.content[0].text
        elif self.model_family == 'gemini':
            response = self.client.models.generate_content(
                model=self.model_name,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_budget=-1),
                    system_instruction=self.system_prompt,
                ),
                contents=[instruction]
            )
            response = response.text
        
        if 'correct' in response:
            logging.info(f"Current platform code is correct")
            return 'correct'
        else:
            if self.task == 'code' and 'recursion' in task_id:
                with open(self.paths.platform_path / task / 'request_recursion', 'r', encoding='utf-8') as f:
                    request = f.read()
            else:
                with open(self.paths.platform_path / task / 'request', 'r', encoding='utf-8') as f:
                    request = f.read()
                    
            with open(self.paths.task_path / self.task / difficulty / f'{task_id}.json', 'r', encoding='utf-8') as f:
                information = json.load(f)
            if task == 'game':
                request = request.format(
                    output_code_name=f'{task_id}_v{version-1}.py',
                    algorithm=information['algorithm'],
                    description=information['description'],
                    strategy=information['strategy']
                )
            else:
                request = request.format(
                    output_code_name=f'{task_id}_v{version-1}.py',
                    algorithm=information['algorithm'],
                    description=information['description']
                )
            instruction = self.initial_prompt_logs_2.format(
                request=request,
                mistake=response,
                current_code=current_code,
            )
            if self.model_family == 'gpt':
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {
                            "role": "system",
                            "content": self.system_prompt
                        },
                        {
                            "role": "user",
                            "content": instruction

                        }
                    ],
                    temperature=0,
                )
                response = response.choices[0].message.content
            elif self.model_family == 'claude':
                response = self.client.messages.create(
                    model=self.model_name,
                    system=self.system_prompt,
                    messages=[
                        {
                            "role": "user",
                            "content": instruction
                        }
                    ],
                    temperature=0,
                    max_tokens=8192,
                )
                response = response.content[0].text
            elif self.model_family == 'gemini':
                response = self.client.models.generate_content(
                    model=self.model_name,
                    config=types.GenerateContentConfig(
                        thinking_config=types.ThinkingConfig(thinking_budget=-1),
                        system_instruction=self.system_prompt,
                        temperature=0,
                    ),
                    contents=[instruction]
                )
                response = response.text
            output_dir = self.paths.platform_path / self.task / difficulty 
            # if not os.path.exists(output_dir):
            #     os.makedirs(output_dir)
            with open(output_dir / f'{task_id}_v{version}.py', 'w', encoding='utf-8') as f:
                f.write(code_clean(response))
            logging.info(f"Platform code updated and saved to {output_dir / f'{task_id}_v{version}.py'}")
            return code_clean(response)
        

class EncryptionFormat(BaseModel):
    class Encryption(BaseModel):
        plaintext: str
    
    sample: list[Encryption]

class CodeFormat(BaseModel):
    class Code(BaseModel):
        var_names: list[str]
        var_values: list[Union[str, int, list[int]]]
        checkpoints: list[list[Union[int, str]]]
    
    sample: list[Code]

class PuzzleFormat(BaseModel):
    class Puzzle(BaseModel):
        answer: str

    sample: list[Puzzle]

class GameFormat(BaseModel):
    class Game(BaseModel):
        settings: list[list[str, Union[int, str]]]

    sample: list[Game]

class CircuitFormat(BaseModel):
    class Input(BaseModel):
        input: list[int]

    sample: list[Input]


class TestSamplesGenerator:
    def __init__(self, task, model_family, model_name, max_turns):
        self.task = task
        self.model_family = model_family
        self.model_name = model_name
        self.max_turns = max_turns
        self.paths = PathManager()

        if self.model_family == 'gpt':
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        elif self.model_family == 'gemini':
            self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        with open(self.paths.test_path / task / 'testsamplegen_system_prompt', 'r', encoding='utf-8') as f:
            self.system_prompt = f.read()
        with open(self.paths.test_path / task / 'testsamplegen_initial_prompt', 'r', encoding='utf-8') as f:
            self.initial_prompt = f.read()

    def generate(self, difficulty, task_id, version):
        import inspect
        import importlib.util
        
        if self.task == 'encryption':
            num = 8
            with open(self.paths.task_path / self.task / difficulty / f'{task_id}.json', 'r') as f:
                algorithm = json.load(f)['description']
            if self.model_family == 'gpt':
                response = self.client.beta.chat.completions.parse(
                    model=self.model_name,
                    messages=[{"role": "system", "content": self.system_prompt},
                            {"role": "user", "content": self.initial_prompt.format(algorithm=algorithm, num=num)}],
                    temperature=1,
                    response_format=EncryptionFormat
                )
                response = response.choices[0].message.parsed
            test_samples = [code.model_dump() for code in response.sample]
            with open(self.paths.test_path / self.task / difficulty / f'{task_id}.json', 'w', encoding='utf-8') as f:
                json.dump(test_samples, f, ensure_ascii=False, indent=4)
            
        elif self.task == 'code':
            num1 = 5
            num2 = 7
            with open(self.paths.task_path / self.task / difficulty / f'{task_id}.json', 'r') as f:
                algorithm = json.load(f)['algorithm']

            path_to_code = str(self.paths.platform_path / self.task / difficulty / f'{task_id}_v{version}.py')
            module_name = os.path.splitext(os.path.basename(str(path_to_code)))[0]
            spec = importlib.util.spec_from_file_location(module_name, str(path_to_code))
            module = importlib.util.module_from_spec(spec)
            # Execute the module in its own namespace
            spec.loader.exec_module(module)
            # Get the function object from the module
            func = getattr(module, 'blackbox', None)
            code = inspect.getsource(func)
            if self.model_family == 'gpt':
                response = self.client.beta.chat.completions.parse(
                    model=self.model_name,
                    messages=[{"role": "system", "content": self.system_prompt},
                            {"role": "user", "content": self.initial_prompt.format(algorithm=algorithm, code=code, num1=num1, num2=num2)}],
                    temperature=1,
                    response_format=CodeFormat
                )
                response = response.choices[0].message.parsed
            test_samples = [code.model_dump() for code in response.sample]
            
            with open(self.paths.test_path / self.task / difficulty / f'{task_id}.json', 'w', encoding='utf-8') as f:
                f.write('[\n')
                for i in range(len(test_samples)):
                    json_line = json.dumps(test_samples[i])
                    if i == len(test_samples) - 1:
                        f.write(json_line + '\n')
                    else:
                        f.write(json_line + ',\n')
                f.write(']')

        elif self.task == 'physics':
            test_samples = [{"time": 1.7}, {"time": 3.8}, {"time": 7}, {"time": 80}, {"time": 5.2}, {"time": 10.7}]
            with open(self.paths.test_path / self.task / difficulty / f'{task_id}.json', 'w', encoding='utf-8') as f:
                json.dump(test_samples, f, ensure_ascii=False, indent=4)

        elif self.task == 'game':
            num = 4
            with open(self.paths.task_path / self.task / difficulty / f'{task_id}.json', 'r') as f:
                info = json.load(f)
                algorithm = info['algorithm']
                description = info['description']
                settings = info['settings']

            if self.model_family == 'gpt':
                response = self.client.beta.chat.completions.parse(
                    model=self.model_name,
                    messages=[{"role": "system", "content": self.system_prompt},
                            {"role": "user", "content": self.initial_prompt.format(algorithm=algorithm, num=num, description=description, settings=settings)}],
                    temperature=0,
                    response_format=GameFormat
                )
                response = response.choices[0].message.parsed
            test_samples = [code.model_dump()['settings'] for code in response.sample]

            for i in range(len(test_samples)):
                current_settings = dict()
                for setting in test_samples[i]:
                    try:
                        setting[1] = int(setting[1])
                    except ValueError:
                        pass
                    current_settings[setting[0]] = setting[1]
                test_samples[i] = current_settings

            with open(self.paths.test_path / self.task / difficulty / f'{task_id}.json', 'w', encoding='utf-8') as f:
                json.dump(test_samples, f, ensure_ascii=False, indent=4)
        
        elif self.task == 'puzzle':
            num = 6
            with open(self.paths.task_path / self.task / difficulty / f'{task_id}.json', 'r') as f:
                info = json.load(f)
                algorithm = info['algorithm']
                description = info['description']
                answer_format = info['answer_format']

            if self.model_family == 'gpt':
                response = self.client.beta.chat.completions.parse(
                    model=self.model_name,
                    messages=[{"role": "system", "content": self.system_prompt},
                            {"role": "user", "content": self.initial_prompt.format(algorithm=algorithm, num=num, description=description, answer_format=answer_format)}],
                    temperature=1,
                    response_format=PuzzleFormat
                )
                response = response.choices[0].message.parsed
            test_samples = [code.model_dump() for code in response.sample]

            with open(self.paths.test_path / self.task / difficulty / f'{task_id}.json', 'w', encoding='utf-8') as f:
                json.dump(test_samples, f, ensure_ascii=False, indent=4)

        elif self.task == 'circuit':
            num1 = 16
            with open(self.paths.task_path / self.task / difficulty / f'{task_id}.json', 'r') as f:
                info = json.load(f)
                input_size = info["input_size"]

            if self.model_family == 'gpt':
                response = self.client.beta.chat.completions.parse(
                    model=self.model_name,
                    messages=[{"role": "system", "content": self.system_prompt},
                            {"role": "user", "content": self.initial_prompt.format(num1=num1, input_size=input_size)}],
                    temperature=0.5,
                    response_format=CircuitFormat
                )
                response = response.choices[0].message.parsed
            
            test_samples = [code.model_dump() for code in response.sample]

            with open(self.paths.test_path / self.task / difficulty / f'{task_id}.json', 'w', encoding='utf-8') as f:
                json.dump(test_samples, f, ensure_ascii=False, indent=4)