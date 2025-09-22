import re
import importlib.util
import sys
import logging
import os
import random
from openai import OpenAI
from google import genai
from google.genai import types
from anthropic import Anthropic
from dotenv import load_dotenv
import json
from paths import PathManager
import copy
from io import StringIO
import ast
import time
import csv
import requests
from ckpt import set_current_debug_target, reset_debugger_state

load_dotenv(override=True)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
def dynamic_import(module_path, module_name):
    if not os.path.exists(module_path):
        raise FileNotFoundError(f"The module at {module_path} was not found.")
    full_module_path = os.path.join(module_path, module_name + '.py')
    spec = importlib.util.spec_from_file_location(module_name, full_module_path)
    if spec is None:
        raise ImportError(f"Could not load module {module_name} from {full_module_path}.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    
    return module

class ReasoningLLM:
    def __init__(self, model_family, model_name, task, eva_mode, n_runs, difficulty, task_id, thinking_mode, mode):
        self.paths = PathManager()
        self.simulation_task_ids = ['double_pendulum', 'harmonic_friction', 'ball_air_resistance']

        self.model_family = model_family
        self.model_name = model_name
        self.thinking_mode = thinking_mode
        self.task = task
        self.difficulty = difficulty
        self.task_id = task_id
        
        self.eva_mode = eva_mode
        self.eva_nums = n_runs
        self.mode = mode  # generate or evaluate

        with open(self.paths.task_path / task / 'player_system_prompt') as f:
            self.system_prompt = f.read()  # system prompt for each task
        if task_id in self.simulation_task_ids:
            with open(self.paths.task_path / task / 'task_intro_simulation') as f:
                self.task_intro = f.read()  # task introduction serves as input prompt
        else:
            with open(self.paths.task_path / task / 'task_intro') as f:
                self.task_intro = f.read()
        if task == 'puzzle' or task =='game':
            with open(self.paths.task_path / task / difficulty / f'{task_id}.json', 'r', encoding='utf-8') as f:
                information = json.load(f)
                self.task_intro = self.task_intro.format(
                    algorithm=information['algorithm'],
                    description=information['description'],
                )

        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.claude_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.qwen_client = OpenAI(api_key=os.getenv("ALIBABA_API_KEY"), base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.deepseek_client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")
        openrouter = os.getenv("OPENROUTER_API_KEY")
        self.headers = {
                "Authorization": f"Bearer {openrouter}",
                "Content-Type": "application/json"
            }

        if model_family == 'gpt':
            self.client = self.openai_client
            self.messages = [{"role": "developer", "content": self.system_prompt},
                             {"role": "user", "content": self.task_intro},
                             {"role": "assistant", "content": 'I understand the rules. I will not output any unrelated text! Let us start the interaction.'}]
            self.history =  copy.deepcopy(self.messages)     # self.history output the complete interaction history, while self.messages filter some error messages
        elif model_family == 'claude':
            self.client = self.claude_client
            self.messages = [{"role": "user", "content": self.task_intro},
                             {"role": "assistant", "content": 'I understand the rules. I will not output any unrelated text! Let us start the interaction.'}]
            self.history =  copy.deepcopy(self.messages)
        elif model_family == 'gemini':
            self.client = self.gemini_client
            self.messages = [types.Content(role="user", parts=[types.Part.from_text(text=self.task_intro)]),
                             types.Content(role="model", parts=[types.Part.from_text(text='I understand the rules. I will not output any unrelated text! Let us start the interaction.')])]
            self.history =  [{"role": "user", "content": self.task_intro},
                             {"role": "assistant", "content": 'I understand the rules. I will not output any unrelated text! Let us start the interaction.'}]
        elif model_family == 'qwen':
            self.client = self.qwen_client
            self.messages = [{"role": "system", "content": self.system_prompt},
                             {"role": "user", "content": self.task_intro},
                             {"role": "assistant", "content": 'I understand the rules. I will not output any unrelated text! Let us start the interaction.'}]
            self.history =  copy.deepcopy(self.messages)
        elif model_family == 'deepseek':
            self.client = self.deepseek_client
            if self.model_name == 'deepseek-r1':
                self.messages = [{"role": "user", "content": self.task_intro},
                                {"role": "assistant", "content": 'I understand the rules. I will not output any unrelated text! Let us start the interaction.'}]
            else:
                self.messages = [{"role": "system", "content": self.system_prompt},
                                {"role": "user", "content": self.task_intro},
                                {"role": "assistant", "content": 'I understand the rules. I will not output any unrelated text! Let us start the interaction.'}]
            self.history =  copy.deepcopy(self.messages)
        elif model_family == 'llama':
            self.messages = [{"role": "system", "content": [{"text": self.system_prompt}]},
                             {"role": "user", "content": [{"text": self.task_intro}]},
                             {"role": "assistant", "content": [{"text": "I understand the rules. I will not output any unrelated text! Let us start the interaction."}]}]
            self.history =  copy.deepcopy(self.messages)

    def save_result(self, output_dir, result):
        if self.mode == 'generate':
            pass
        elif self.mode == 'evaluate':
            if self.thinking_mode:
                name = self.model_name + '_thinking'
            else:
                name = self.model_name

            if not os.path.exists(os.path.join(output_dir, self.task, self.difficulty, self.task_id, name)):
                os.makedirs(os.path.join(output_dir, self.task, self.difficulty, self.task_id, name))
                
            if not os.path.exists(os.path.join(output_dir, self.task, self.difficulty, self.task_id, name, 'result.csv')):
                header = ['difficulty', 'task_id', 'model_family', 'model_name', 'run_times', 'max_turns', 'failure_num', 'num_correct', 'total_samples', 'accuracy']
                with open(os.path.join(output_dir, self.task, self.difficulty, self.task_id, name, 'result.csv'), "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(header)

            with open(os.path.join(output_dir, self.task, self.difficulty, self.task_id, name, 'result.csv'), 'a', newline="", encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerows(result)
                logging.info(f"Results saved to {os.path.join(output_dir, self.task, self.difficulty, self.task_id, name, 'result.csv')}")

    def save_history(self, output_dir, version):
        if self.mode == 'generate':
            logging.info("Saving generation history...")
            if not os.path.exists(os.path.join(output_dir, self.task, self.difficulty)):
                os.makedirs(os.path.join(output_dir, self.task, self.difficulty))
            # if not os.path.exists(os.path.join(output_dir, self.task, difficulty, f'{task_id}_logs_v{version}.json')):
            with open(os.path.join(output_dir, self.task, self.difficulty, f'{self.task_id}_logs_v{version}.json'), 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=4)
        
        elif self.mode == 'evaluate':
            logging.info("Saving evaluation history...")

            if self.thinking_mode:
                if not os.path.exists(os.path.join(output_dir, self.task, self.difficulty, self.task_id, self.model_family, self.model_name+'_thinking')):
                    os.makedirs(os.path.join(output_dir, self.task, self.difficulty, self.task_id, self.model_family, self.model_name+'_thinking'))
                with open(os.path.join(output_dir, self.task, self.difficulty, self.task_id, self.model_family, self.model_name+'_thinking', f'run_{version}.json'), 'w', encoding='utf-8') as f:
                    json.dump(self.history, f, ensure_ascii=False, indent=4)
            else:
                if not os.path.exists(os.path.join(output_dir, self.task, self.difficulty, self.task_id, self.model_family, self.model_name)):
                    os.makedirs(os.path.join(output_dir, self.task, self.difficulty, self.task_id, self.model_family, self.model_name))
                with open(os.path.join(output_dir, self.task, self.difficulty, self.task_id, self.model_family, self.model_name, f'run_{version}.json'), 'w', encoding='utf-8') as f:
                    json.dump(self.history, f, ensure_ascii=False, indent=4)

    def normal_output(self, input):
        if self.model_family == 'gpt':
            self.messages.append({"role": "user", "content": str(input)})
            self.history.append({"role": "user", "content": str(input)})
            if 'gpt' in self.model_name:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=self.messages,
                    temperature=0,
                    max_tokens=500,
                )
                response = response.choices[0].message.content
            else:   # for o-series models
                response = self.client.responses.create(
                    model=self.model_name,
                    input=self.messages,
                    reasoning={"effort": "medium"},
                )
                response = response.output_text
            self.messages.append({"role": "assistant", "content": response})
            self.history.append({"role": "assistant", "content": response})

        elif self.model_family == 'claude':
            if self.thinking_mode == False:
                self.messages.append({"role": "user", "content": str(input)})
                self.history.append({"role": "user", "content": str(input)})
                response = self.client.messages.create(
                    model=self.model_name,
                    system = self.system_prompt,
                    messages=self.messages,
                    temperature=0,
                    max_tokens=500
                )
                if response.content and len(response.content) > 0:
                    response = response.content[0].text
                else:
                    response = 'claude did not return any response'
                self.messages.append({"role": "assistant", "content": response})
                self.history.append({"role": "assistant", "content": response})
            else:
                self.messages.append({"role": "user", "content": str(input)})
                self.history.append({"role": "user", "content": str(input)})
                response = self.client.messages.create(
                    model=self.model_name,
                    system = self.system_prompt,
                    messages=self.messages,
                    max_tokens=20500,
                    thinking={
                        "type": "enabled",
                        "budget_tokens": 20000,
                    }
                )
                thinking_content = ''
                response_content = 'claude did not return any response'

                for block in response.content:
                    if block.type == 'thinking':
                        thinking_content = block.thinking
                    elif block.type == 'text':
                        response_content = block.text
                self.messages.append({"role": "assistant", "content": response_content})
                if thinking_content != '':
                    self.history.append({"role": "thinking_assistant", "content": thinking_content})
                self.history.append({"role": "assistant", "content": response_content})
                response = response_content 

        elif self.model_family == 'gemini':
            self.messages.append(types.Content(role="user", parts=[types.Part.from_text(text=str(input))]))
            self.history.append({"role": "user", "content": str(input)})
            if '2.5' in self.model_name:
                if self.thinking_mode:
                    response = self.client.models.generate_content(
                        model=self.model_name,
                        config=types.GenerateContentConfig(
                            thinking_config=types.ThinkingConfig(thinking_budget=-1, include_thoughts=True),
                            system_instruction=self.system_prompt,
                        ),
                        contents=self.messages
                    )
                    response_content = 'gemini did not return any response'
                    for part in response.candidates[0].content.parts:
                        if not part.text:
                            continue
                        if part.thought:
                            thinking_content = part.text
                            self.history.append({"role": "thinking_assistant", "content": thinking_content})
                        else:
                            response_content = part.text
                    self.messages.append(types.Content(role="model", parts=[types.Part.from_text(text=response_content)]))
                    self.history.append({"role": "assistant", "content": response_content})
                    response = response_content
                else:
                    response = self.client.models.generate_content(
                        model=self.model_name,
                        config=types.GenerateContentConfig(
                            thinking_config=types.ThinkingConfig(thinking_budget=0),
                            system_instruction=self.system_prompt,
                            temperature=1,
                        ),
                        contents=self.messages
                    )
                    response = response.text
                    if response is None:
                        response = 'gemini did not return any response'
                    self.messages.append(types.Content(role="model", parts=[types.Part.from_text(text=response)]))
                    self.history.append({"role": "assistant", "content": response})
            else:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    config=types.GenerateContentConfig(
                        system_instruction=self.system_prompt,
                        temperature=0,
                        max_output_tokens=500,
                    ),
                    contents=self.messages
                )
                response = response.text
                self.messages.append(types.Content(role="model", parts=[types.Part.from_text(text=response)]))
                self.history.append({"role": "assistant", "content": response})

        elif self.model_family == 'qwen':
            self.messages.append({"role": "user", "content": str(input)})
            self.history.append({"role": "user", "content": str(input)})
            # no reasoning 
            if self.thinking_mode == False:
                response = self.client.chat.completions.create(
                        model=self.model_name,
                        messages=self.messages,
                        extra_body={"enable_thinking": False},
                        temperature=0,
                        max_tokens=500,
                    )
                response = response.choices[0].message.content
                self.messages.append({"role": "assistant", "content": response})
                self.history.append({"role": "assistant", "content": response})
            # reasoning
            else:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=self.messages,
                    extra_body={"enable_thinking": True, "thinking_budget": 20000},
                    stream=True,
                    max_tokens=500,
                )
                reasoning_content = ""
                response_content = ""
                for chunk in response:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, "reasoning_content") and delta.reasoning_content is not None:
                        reasoning_content += delta.reasoning_content
                    if hasattr(delta, "content") and delta.content:
                        response_content += delta.content

                self.messages.append({"role": "assistant", "content": response_content})
                self.history.append({"role": "thinking_assistant", "content": reasoning_content})
                self.history.append({"role": "assistant", "content": response_content})
                response = response_content

        elif self.model_family == 'deepseek':
            self.messages.append({"role": "user", "content": str(input)})
            self.history.append({"role": "user", "content": str(input)})
            if 'reasoner' in self.model_name:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=self.messages,
                    # max_tokens=2200,
                )
                reasoning_content = response.choices[0].message.reasoning_content
                response = response.choices[0].message.content
                self.history.append({"role": "thinking_assistant", "content": reasoning_content})
                self.messages.append({"role": "assistant", "content": response})
                self.history.append({"role": "assistant", "content": response})
            else:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=self.messages,
                    temperature=0,
                    max_tokens=500,
                )
                response = response.choices[0].message.content
                self.messages.append({"role": "assistant", "content": response})
                self.history.append({"role": "assistant", "content": response})

        elif self.model_family == 'llama':
            self.messages.append({"role": "user", "content": [{"text": str(input)}]})
            self.history.append({"role": "user", "content": str(input)})
            payload = {
                "model": self.model_name,
                "messages": self.messages,
                "provider":{
                    "order": [
                        'lambda/fp8'
                    ]
                },
                "max_tokens": 500,
                "temperature": 0
            }
            response = requests.post("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(payload), headers=self.headers)
            response = response.json()
            response = response['choices'][0]['message']['content']
            self.messages.append({"role": "assistant", "content": [{"text": str(response)}]})
            self.history.append({"role": "assistant", "content": response})

        '''If mistake happens, filter them in self.messages'''
        if self.has_format_mistake(str(input)):
            del self.messages[-3:-1]

        return response
    
    '''When the player is ready for evaluation, use this function'''
    def evaluate(self, failure_num, version, max_turns=20):
        with open(self.paths.test_path / self.task / self.difficulty / f"{self.task_id}.json", 'r', encoding='utf-8') as f:
            samples = json.load(f)
        # random.shuffle(samples)  # shuffle the samples for evaluation
        try:
            # during generation, import v_version plafform module
            if self.mode == 'generate':
                platform_module = dynamic_import(self.paths.platform_path / self.task / self.difficulty, f"{self.task_id}_v{version}")
            # during evaluation, import the final platform module
            elif self.mode == 'evaluate':
                platform_module = dynamic_import(self.paths.platform_path / self.task / self.difficulty, f"{self.task_id}_final")
        except (FileNotFoundError, ImportError) as e:
            print(e)
        
        if self.task == 'code':
            num_ckpts = 0   # number of checkpoints
            num_correct = 0    # number of correct answers
            name_value_pairs = []   # store var pairs
            active_samples = len(samples) if self.mode == 'evaluate' else 1

            max_turns = (len(self.messages)-3) / 2
            for i in range(active_samples):
                name_value_pairs.append(dict(zip(samples[i]['var_names'], samples[i]['var_values'])))
            name_value_pairs_copy = copy.deepcopy(name_value_pairs)
            
            for i in range(active_samples):
                for j in range(len(samples[i]["checkpoints"])):
                    num_ckpts += 1 
                    if i == 0 and j == 0:
                        self.messages.pop()
                        model_input = self.messages[-1]
                        self.messages.pop()
                        self.history.pop()
                        self.history.pop()
                        if self.model_family == 'gemini':
                            model_input = model_input.parts[0].text + f"\n********Evaluation Starts, You Have {failure_num+1} Chances for Answering Each Question********\n Now answer the question: When the input variables of the blackbox are {name_value_pairs[i]}, what's the value for {samples[i]['checkpoints'][j][2]} at checkpoint ({samples[i]['checkpoints'][j][0]}, {samples[i]['checkpoints'][j][1]})?"
                        elif self.model_family == 'llama':
                            model_input = model_input["content"][0]['text'] + f"\n********Evaluation Starts, You Have {failure_num+1} Chances for Answering Each Question********\n Now answer the question: When the input variables of the blackbox are {name_value_pairs[i]}, what's the value for {samples[i]['checkpoints'][j][2]} at checkpoint ({samples[i]['checkpoints'][j][0]}, {samples[i]['checkpoints'][j][1]})?"
                        else:
                            model_input = model_input["content"] + f"\n********Evaluation Starts, You Have {failure_num+1} Chances for Answering Each Question********\n Now answer the question: When the input variables of the blackbox are {name_value_pairs[i]}, what's the value for {samples[i]['checkpoints'][j][2]} at checkpoint ({samples[i]['checkpoints'][j][0]}, {samples[i]['checkpoints'][j][1]})?"
                    else:
                        model_input = f"Answer the question: When the input variables of the blackbox are {name_value_pairs[i]}, what's the value for {samples[i]['checkpoints'][j][2]} at checkpoint ({samples[i]['checkpoints'][j][0]}, {samples[i]['checkpoints'][j][1]})?"
                    model_output = self.normal_output(model_input)
                    model_output = model_output.rstrip('\n')
                    
                    # use StringIO to capture the output of the blackbox function
                    output = StringIO()
                    original_stdout = sys.stdout
                    sys.stdout = output
                    set_current_debug_target(platform_module.blackbox, 'original_n')
                    reset_debugger_state()
                    platform_module.blackbox(
                        **name_value_pairs[i], 
                        idx=samples[i]["checkpoints"][j][0], 
                        iter=samples[i]["checkpoints"][j][1], 
                    )
                    sys.stdout = original_stdout
                    truth = output.getvalue()
                    truth = ast.literal_eval(truth)  # convert the output to the expected type

                    type_mapping = {
                        'int': int,
                        'float': float,
                        'list': ast.literal_eval,
                        'dict': ast.literal_eval, 
                        'str': lambda s: s.strip("'\"") 
                    }
                    result_dict = {}
                    pattern = re.compile(r"(\w+)\s*=\s*(\{.*?\}|\[.*?\]|'.*?'|\".*?\"|[^,]*)")
                    for item in truth:
                        pairs = pattern.findall(item)
                        parts = {key.strip(): val.strip() for key, val in pairs}
        
                        name = parts['name']
                        value_str = parts.get('value', '')
                        type_str = parts.get('type', 'str')
                        convert_func = type_mapping.get(type_str, lambda val: val)
                        converted_value = convert_func(value_str)
                        
                        result_dict[name] = converted_value

                    query_var=samples[i]["checkpoints"][j][2]
                    truth = result_dict.get(query_var, None)

                    name_value_pairs = copy.deepcopy(name_value_pairs_copy)     # reset the name_value_pairs
                    num_try = 0
                    answer = True
                    while str(truth).replace(" ", "") != model_output.replace(" ", ""):    # exclude the influence of format
                        num_try += 1
                        if num_try > failure_num:
                            answer = False
                            break
                        model_output = self.normal_output("Your answer is wrong. Please try again. DO NOT output any other text, ONLY output the answer.")
                    
                    if answer == True:
                        num_correct += 1
                        if self.model_family == 'gemini':
                            self.messages.append(types.Content(role="user", parts=[types.Part.from_text(text="Your answer is correct. Let's move to next question.")]))
                            self.messages.append(types.Content(role="model", parts=[types.Part.from_text(text="Ok.")]))
                        elif self.model_family == 'llama':
                            self.messages.append({"role": "user", "content": [{"text": "Your answer is correct. Let's move to next question."}]})
                            self.messages.append({"role": "assistant", "content": [{"text":"Ok."}]})
                        else:
                            self.messages.append({"role": "user", "content": "Your answer is correct. Let's move to next question."})
                            self.messages.append({"role": "assistant", "content": "Ok."})
                        self.history.append({"role": "user", "content": "Your answer is correct. Let's move to next question."})
                        self.history.append({"role": "assistant", "content": "Ok."})
                    else:  
                        if self.model_family == 'gemini':
                            self.messages.append(types.Content(role="user", parts=[types.Part.from_text(text="Your answer is wrong. Let's move to next question.")]))
                            self.messages.append(types.Content(role="model", parts=[types.Part.from_text(text="Ok.")]))
                        elif self.model_family == 'llama':
                            self.messages.append({"role": "user", "content": [{"text": "Your answer is wrong. Let's move to next question."}]})
                            self.messages.append({"role": "assistant", "content": [{"text":"Ok."}]})
                        else:
                            self.messages.append({"role": "user", "content": "Your answer is wrong. Let's move to next question."})
                            self.messages.append({"role": "assistant", "content": "Ok."})
                        self.history.append({"role": "user", "content": "Your answer is wrong. Let's move to next question."})
                        self.history.append({"role": "assistant", "content": "Ok."})

            if self.mode == 'evaluate':
                if self.thinking_mode:
                    self.save_result(self.paths.result_path, [[self.difficulty, self.task_id, self.model_family, self.model_name+'_thinking', 'run_'+str(version), max_turns, failure_num, num_correct, active_samples*len(samples[0]["checkpoints"]), num_correct/(active_samples*len(samples[0]["checkpoints"]))]])  
                else:
                    self.save_result(self.paths.result_path, [[self.difficulty, self.task_id, self.model_family, self.model_name, 'run_'+str(version), max_turns, failure_num, num_correct, active_samples*len(samples[0]["checkpoints"]), num_correct/(active_samples*len(samples[0]["checkpoints"]))]])  
       
        elif self.task == 'encryption':
            max_turns = (len(self.messages)-5) / 2
            num_correct = 0 
            active_samples = len(samples) if self.mode == 'evaluate' else 1

            for i in range(active_samples):
                plaintext = samples[i]['plaintext']
                if i == 0:
                    self.messages.pop()
                    model_input = self.messages[-1]
                    self.messages.pop()
                    self.history.pop()
                    self.history.pop()
                    if self.model_family == 'gemini':
                        model_input = model_input.parts[0].text + f"\n********Evaluation Starts, You Have {failure_num+1} Chances for Answering Each Question********\n Now answer the question: What's the output of the blackbox when the input plaintext is '{plaintext}'?"
                    elif self.model_family == 'llama':
                        model_input = model_input["content"][0]['text'] + f"\n********Evaluation Starts, You Have {failure_num+1} Chances for Answering Each Question********\n Now answer the question: What's the output of the blackbox when the input plaintext is '{plaintext}'?"
                    else:
                        model_input = model_input["content"] + f"\n********Evaluation Starts, You Have {failure_num+1} Chances for Answering Each Question********\n Now answer the question: What's the output of the blackbox when the input plaintext is '{plaintext}'?"
                else:
                    model_input = f"Answer the question: What's the output of the blackbox when the input plaintext is '{plaintext}'?"
                logging.info(f"Evaluation Stage Model Input: {model_input}")
                model_output = self.normal_output(model_input)
                model_output = model_output.rstrip('\n')
                
                times = 0
                while self.check_text_format(model_output) != True:
                    times += 1
                    warning = "You must only return the result of the blackbox function, without any other unrelated text or symbols. Please try again."
                    model_output = self.normal_output(warning)
                    del self.messages[-3:-1]
                    if times > 1:
                        break

                logging.info(f"Evaluation Stage Model Output: {model_output}")
                truth = platform_module.blackbox(plaintext)

                num_try = 0
                answer = True
                while truth != model_output:
                    num_try += 1
                    if num_try > failure_num:
                        answer = False
                        break
                    model_output = self.normal_output("Your answer is wrong. Please try again. DO NOT output any other text, ONLY output the answer.")
                if answer == True:
                    num_correct += 1
                    if self.model_family == 'gemini':
                        self.messages.append(types.Content(role="user", parts=[types.Part.from_text(text="Your answer is correct. Let's move to next question.")]))
                        self.messages.append(types.Content(role="model", parts=[types.Part.from_text(text="Ok.")]))
                    elif self.model_family == 'llama':
                        self.messages.append({"role": "user", "content": [{"text": "Your answer is correct. Let's move to next question."}]})
                        self.messages.append({"role": "assistant", "content": [{"text":"Ok."}]})
                    else:
                        self.messages.append({"role": "user", "content": "Your answer is correct. Let's move to next question."})
                        self.messages.append({"role": "assistant", "content": "Ok."})
                    self.history.append({"role": "user", "content": "Your answer is correct. Let's move to next question."})
                    self.history.append({"role": "assistant", "content": "Ok."})
                else:  
                    if self.model_family == 'gemini':
                        self.messages.append(types.Content(role="user", parts=[types.Part.from_text(text="Your answer is wrong. Let's move to next question.")]))
                        self.messages.append(types.Content(role="model", parts=[types.Part.from_text(text="Ok.")]))
                    elif self.model_family == 'llama':
                        self.messages.append({"role": "user", "content": [{"text": "Your answer is wrong. Let's move to next question."}]})
                        self.messages.append({"role": "assistant", "content": [{"text":"Ok."}]})
                    else:
                        self.messages.append({"role": "user", "content": "Your answer is wrong. Let's move to next question."})
                        self.messages.append({"role": "assistant", "content": "Ok."})
                    self.history.append({"role": "user", "content": "Your answer is wrong. Let's move to next question."})
                    self.history.append({"role": "assistant", "content": "Ok."})

            if self.mode == 'evaluate':
                if self.thinking_mode:
                    self.save_result(self.paths.result_path, [[self.difficulty, self.task_id, self.model_family, self.model_name+'_thinking', 'run_'+str(version), max_turns, failure_num, num_correct, active_samples, num_correct/active_samples]])  
                else:
                    self.save_result(self.paths.result_path, [[self.difficulty, self.task_id, self.model_family, self.model_name, 'run_'+str(version), max_turns, failure_num, num_correct, active_samples, num_correct/active_samples]])  
        
        elif self.task == 'puzzle':
            num_correct = 0
            active_samples = len(samples) if self.mode == 'evaluate' else 1

            for i in range(active_samples):
                truth = samples[i]['answer']
                
                end_point = len(self.messages)
                model_input = f"********A New Puzzle Starts, You can Make {max_turns} Queries Before Answering Each Question. And Then You Have {failure_num+1} Chances for Answering. Output the Value Only.********"

                for j in range(max_turns):
                    # The model asking (`j`+1) -th  query
                    model_output = self.normal_output(model_input)
                    feedback = platform_module.blackbox(truth, model_output)
                    model_input = f'<Current Turn: {j+1}, {max_turns-(j+1)} Turns Remaining> ' + feedback

                model_input += f"********Evaluation Starts, You Have {failure_num+1} Chances for Answering, Please Output the Answer DIRECTLY.********\n"
                model_output = self.normal_output(model_input)
                model_output = model_output.rstrip('\n')

                times = 0
                while platform_module.check_answer_format(model_output) != True:
                    times += 1
                    warning = "You must only return the answer of the blackbox puzzle, strictly following the instructions in the puzzle rules, without more unrelated text or symbols. Please try again."
                    model_output = self.normal_output(warning)
                    del self.messages[-3:-1]
                    if times > 1:
                        break

                num_try = 0
                answer = True
                
                if self.task_id == 'battleship':
                    truth = truth.replace("O", ".")
                while truth != model_output:
                    num_try += 1
                    if num_try > failure_num:
                        answer = False
                        break
                    model_output = self.normal_output("Your answer is wrong. Please try again. DO NOT output any other text, ONLY output the answer.")
                if answer == True:
                    num_correct += 1
                    if self.model_family == 'gemini':
                        self.messages.append(types.Content(role="user", parts=[types.Part.from_text(text="Your answer is correct.")]))
                        self.messages.append(types.Content(role="model", parts=[types.Part.from_text(text="Ok.")]))
                    else:
                        self.messages.append({"role": "user", "content": "Your answer is correct."})
                        self.messages.append({"role": "assistant", "content": "Ok."})
                    self.history.append({"role": "user", "content": "Your answer is correct."})
                    self.history.append({"role": "assistant", "content": "Ok."})
                else:  
                    if self.model_family == 'gemini':
                        self.messages.append(types.Content(role="user", parts=[types.Part.from_text(text="Your answer is wrong.")]))
                        self.messages.append(types.Content(role="model", parts=[types.Part.from_text(text="Ok.")]))
                    else:
                        self.messages.append({"role": "user", "content": "Your answer is wrong."})
                        self.messages.append({"role": "assistant", "content": "Ok."})
                    self.history.append({"role": "user", "content": "Your answer is wrong."})
                    self.history.append({"role": "assistant", "content": "Ok."})

                self.messages = self.messages[:end_point]  

            if self.mode == 'evaluate':
                if self.thinking_mode:
                    self.save_result(self.paths.result_path, [[self.difficulty, self.task_id, self.model_family, self.model_name+'_thinking', 'run_'+str(version), max_turns, failure_num, num_correct, active_samples, num_correct/active_samples]])  
                else:
                    self.save_result(self.paths.result_path, [[self.difficulty, self.task_id, self.model_family, self.model_name, 'run_'+str(version), max_turns, failure_num, num_correct, active_samples, num_correct/active_samples]])  

        elif self.task == 'game':
            active_samples = len(samples) if self.mode == 'evaluate' else 1
            sum_score = [[0] * (failure_num+1) for _ in range(active_samples)]
            max_score = []
            initial_messages = copy.deepcopy(self.messages)

            model_input = f"********Exploration Phase Starts, We wll Play the Game for {max_turns} Times. Your Actions Will Not Be Recorded, and Your Score Does Not Matter.**********\n"
            model_output = self.normal_output(model_input)
            
            for i in range(active_samples):
                self.messages = copy.deepcopy(initial_messages)                
                settings = samples[i]

                for j in range(max_turns):
                    logging.info(f"Exploration Round {j+1}/{max_turns}")
                    model_input = f"***Exploration Round <{j+1}/{max_turns}> Start***\n"
                    model_output = f"Ok. I'm ready to play the game. This is round {j+1} of the exploration phase."
                    if self.model_family == 'gemini':
                        self.messages.append(types.Content(role="user", parts=[types.Part.from_text(text=model_input)]))
                        self.messages.append(types.Content(role="model", parts=[types.Part.from_text(text=model_output)]))
                    else:
                        self.messages.append({"role": "user", "content": model_input})
                        self.messages.append({"role": "assistant", "content": model_output})
                    self.history.append({"role": "user", "content": model_input})
                    self.history.append({"role": "assistant", "content": model_output})
                    platform_module.platform(settings, self)
                logging.info(f"Exploration Phase Ends, Now We Will Start the Evaluation Phase.")
                for k in range(failure_num+1):
                    model_input = f"********Evaluation Phase Starts, We Will Play the Game for {failure_num+1} Time. Now is the {k} time. The highest score Will Be Recorded.**********\n"
                    model_output = self.normal_output(model_input)
                    sum_score[i][k] += platform_module.platform(settings, self)
                best_score = [max(score) for score in sum_score]

                if 'rps' in self.task_id:
                    if self.task_id == 'anti_rps_random':
                        max_score.append(settings['total_turns'] / 2)
                    elif self.task_id == 'rps7_random_3':
                        max_score.append(settings['total_turns'] * 3 / 7)
                    else:
                        max_score.append(settings['total_turns'])
                elif 'comparing_cards' in self.task_id:
                    max_score.append(settings['total_cards'] - 1)
                elif 'load_shoot_defend' in self.task_id:
                    if self.task_id == 'load_shoot_defend_smart':
                        max_score = [2, 3, 4, 5]
                    elif self.task_id == 'load_shoot_defend_attacker':
                        max_score = [3, 4, 5, 6]
                    elif self.task_id == 'load_shoot_defend_balance':
                        max_score = [3, 5, 5, 7]
                    elif self.task_id == 'load_shoot_defend_defender':
                        max_score = [3, 4, 6 ,7]

            performance = sum([best_score[i]/max_score[i] if best_score[i]/max_score[i] >0 else 0 for i in range(active_samples)]) / active_samples
            logging.info(f"Total Score: {sum_score}, {best_score}, {max_score}")
            if self.mode == 'evaluate':
                if self.thinking_mode:
                    self.save_result(self.paths.result_path, [[self.difficulty, self.task_id, self.model_family, self.model_name+'_thinking', 'run_'+str(version), max_turns, failure_num, best_score, max_score, performance]])  
                else:
                    self.save_result(self.paths.result_path, [[self.difficulty, self.task_id, self.model_family, self.model_name, 'run_'+str(version), max_turns, failure_num, best_score, max_score, performance]])  

        elif self.task == 'physics':
            def check(output, truth):
                '''return a list of boolean values indicating whether the output is correct'''
                if len(output) != len(truth):
                    return [False] * len(truth)
                res = []
                for key in truth.keys():
                    x1, y1, z1 = output[key][:3]
                    x2, y2, z2 = truth[key]
                    if abs(float(x1) - x2) > eps or abs(float(y1) - y2) > eps or abs(float(z1) - z2) > eps:
                        res.append(False)
                    else:
                        res.append(True)
                return res
            max_turns = (len(self.messages)-5) / 2

            if self.task_id not in self.simulation_task_ids:
                '''calculate the coordinate of each object'''
                num_correct = 0
                eps = 0.01    # error tolerance
                active_samples = len(samples) if self.mode == 'evaluate' else 1
                for i in range(active_samples):
                    t = samples[i]['time']
                    if i == 0:
                        self.messages.pop()
                        model_input = self.messages[-1]
                        self.messages.pop()
                        self.history.pop()
                        self.history.pop()
                        if self.model_family == 'gemini':
                            model_input = model_input.parts[0].text + f"\n********Evaluation Starts, You Have {failure_num+1} Chances for Answering Each Question********\n Now answer the question: What is the coordinate of each object at time {t}?"
                        elif self.model_family == 'llama':
                            model_input = model_input["content"][0]['text'] + f"\n********Evaluation Starts, You Have {failure_num+1} Chances for Answering Each Question********\n Now answer the question: What is the coordinate of each object at time {t}?"
                        else:
                            model_input = model_input["content"] + f"\n********Evaluation Starts, You Have {failure_num+1} Chances for Answering Each Question********\n Now answer the question: What is the coordinate of each object at time {t}?"
                    else:
                        model_input = f"Answer the question: What is the coordinate of each object at time {t}?"
                    logging.info(f"Evaluation Stage Model Input: {model_input}")
                    model_output = self.normal_output(model_input)
                    model_output = model_output.rstrip('\n')
                    if 'json' in model_output:
                        model_output = re.findall(r"```json\n(.*?)```", model_output, re.DOTALL)[0]
                        model_output = model_output.rstrip()
                    logging.info(f"Evaluation Stage Model Output: {model_output}")
                    times = 0
                    while self.check_text_format(model_output) == False:
                        times += 1
                        warning = "Strictly follow the output format `{\"object1\": (x, y, z), \"object2\": (x, y, z), ...}`. Please try again."
                        model_output = self.normal_output(warning)
                        del self.messages[-3:-1]
                        if times > 1:
                            break

                    model_output = self.check_text_format(model_output)
                    if type(model_output) == bool or model_output is None:# 
                        format = False
                    else:
                        format = True

                    truth = platform_module.blackbox(t)
                    num_try = 0
                    answer = True
                    if format != False:
                        while False in check(model_output, truth):
                            num_try += 1
                            if num_try > failure_num:
                                answer = False
                                break
                            idx = ', '.join(str(i+1) for i in range(len(check(model_output, truth))) if check(model_output, truth)[i] == False)
                            model_output = self.normal_output(f"Your answer for object{idx} is wrong. Please try again. DO NOT output any other text, ONLY output the answer.")
                    if answer == True and format == True:
                        num_correct += 1
                        if self.model_family == 'gemini':
                            self.messages.append(types.Content(role="user", parts=[types.Part.from_text(text="Your answer is correct. Let's move to next question.")]))
                            self.messages.append(types.Content(role="model", parts=[types.Part.from_text(text="Ok.")]))
                        elif self.model_family == 'llama':
                            self.messages.append({"role": "user", "content": [{"text": "Your answer is right. Let's move to next question."}]})
                            self.messages.append({"role": "assistant", "content": [{"text":"Ok."}]})
                        else:
                            self.messages.append({"role": "user", "content": "Your answer is correct. Let's move to next question."})
                            self.messages.append({"role": "assistant", "content": "Ok."})
                        self.history.append({"role": "user", "content": "Your answer is correct. Let's move to next question."})
                        self.history.append({"role": "assistant", "content": "Ok."})
                    else:  
                        if self.model_family == 'gemini':
                            self.messages.append(types.Content(role="user", parts=[types.Part.from_text(text="Your answer is wrong. Let's move to next question.")]))
                            self.messages.append(types.Content(role="model", parts=[types.Part.from_text(text="Ok.")]))
                        elif self.model_family == 'llama':
                            self.messages.append({"role": "user", "content": [{"text": "Your answer is wrong. Let's move to next question."}]})
                            self.messages.append({"role": "assistant", "content": [{"text":"Ok."}]})
                        else:
                            self.messages.append({"role": "user", "content": "Your answer is wrong. Let's move to next question."})
                            self.messages.append({"role": "assistant", "content": "Ok."})
                        self.history.append({"role": "user", "content": "Your answer is wrong. Let's move to next question."})
                        self.history.append({"role": "assistant", "content": "Ok."})   

            else:
                '''let llm write function to simulate the mechanical system'''
                eps = 0.01    # error tolerance
                active_samples = len(samples) if self.mode == 'evaluate' else 1
                
                self.messages.pop()
                model_input = self.messages[-1]
                self.messages.pop()
                self.history.pop()
                self.history.pop()
                if self.model_family == 'gemini':
                    model_input = model_input.parts[0].text + f"\n********Evaluation Starts, You Have {failure_num+1} Chances for Answering Question********\n Now output runnable python code to simulate the mechanical system"
                else:
                    model_input = model_input["content"] + f"\n********Evaluation Starts, You Have {failure_num+1} Chances for Answering Question********\n Now output runnable python code to simulate the mechanical system"
                model_output = self.normal_output(model_input)
                scope = {} 
                
                for trys in range(failure_num + 1):
                    times = 0
                    flag = False
                    while True:
                        times += 1
                        if times > 2:
                            flag = True
                            break
                        try:
                            if 'python' in model_output:
                                model_output = re.findall(r"```python\n(.*?)```", model_output, re.DOTALL)[0]
                            exec(model_output, scope, scope)
                            test_res = scope['solution'](1)
                            if test_res is None:
                                model_input = f"The output code must **return the coordinates of each object**. Please try again. DO NOT output any other text, ONLY output the code."
                                model_output = self.normal_output(model_input)
                                self.messages.pop()
                                self.messages.pop()
                        except Exception as e:
                            model_input = f"The output code has error: {e}. Please try again. DO NOT output any other text, ONLY output the code."
                            model_output = self.normal_output(model_input)
                            self.messages.pop()
                            self.messages.pop()
                        else:
                            break
                    if flag:
                        num_correct = 0
                        continue
                    solution = scope.get('solution')
                    ans = ''
                    answer = [True for i in range(active_samples)]
                    for i in range(active_samples):
                        t = samples[i]['time']
                        truth = platform_module.blackbox(t)
                        if solution(t) is None:
                            ans += f"Your answer for time {t} is wrong."
                            continue
                        res = check(solution(t), truth)
                        for j in range(len(res)):
                            if res[j] == False:
                                answer[i] = False
                            ans += f"Your answer for position of object{i+1} at time {t} is {res[j]}. "
                        if answer[i] == False:
                            ans += f"The answer is wrong. \n"
                        else:
                            ans += f"The answer is correct. \n"
                    num_correct = sum(answer)
                    if trys == failure_num:
                        self.messages.append({"role": "user", "content": f"{ans}"})
                        self.history.append({"role": "user", "content": f"{ans}"})
                    else:
                        model_input = f"{ans} . You have a chance to try again. DO NOT output any other text, ONLY output runnable code."
                        model_output = self.normal_output(model_input)
            if self.mode == 'evaluate':
                if self.thinking_mode:
                    self.save_result(self.paths.result_path, [[self.difficulty, self.task_id, self.model_family, self.model_name+'_thinking', 'run_'+str(version), max_turns, failure_num, num_correct, active_samples, num_correct/active_samples]])  
                else:
                    self.save_result(self.paths.result_path, [[self.difficulty, self.task_id, self.model_family, self.model_name, 'run_'+str(version), max_turns, failure_num, num_correct, active_samples, num_correct/active_samples]])  

        elif self.task == 'circuit':
            num_correct = 0
            circuit_test_num = len(samples)

            for n in range(1, circuit_test_num+1):
                model_input = ""
                if n == 1:
                    self.messages.pop()
                    model_input = self.messages[-1]
                    self.messages.pop()
                    self.history.pop()
                    self.history.pop()
                    if self.model_family == 'gemini':
                        model_input = model_input.parts[0].text + f"\n********Evaluation Starts, You Have {failure_num+1} Chances for Answering Each Question********\n"
                    else:
                        model_input = model_input["content"] + f"\n********Evaluation Starts, You Have {failure_num+1} Chances for Answering Each Question********\n"
                    model_input += "The output format is described in the Evaluation section previosly. For example:\n[0, 1, 0, 1]\n"
                input = samples[n-1]["input"]

                model_input += f"In this turn, given the input {input}, answer the output of the gates in the format we dicussed without any text else."

                num_try = 0
                while num_try < failure_num + 1:
                    num_try += 1
                    
                    model_output = self.normal_output(model_input)
                    if model_output is None:
                        model_output = "model output is None"

                    def output_clear(code):
                        code = code.replace("```python", "")
                        code = code.replace("```", "")
                        return code

                    model_output = output_clear(model_output)

                    real_circuit_gates = platform_module.blackbox(input)
                    try:
                        circuit_gates = json.loads(model_output)
                        if real_circuit_gates != circuit_gates:
                            model_input = f"the answer is wrong when input = {input}"
                            continue

                        model_input = f"your answer is correct."
                        num_correct += 1
                        break
                    except Exception as e:
                        model_input = "Please strictly follow the format. Output a 0/1 list without anything else. For example:\n[0, 1, 0, 1]\n"
                
                if self.model_family == 'gemini':
                    self.messages.append(types.Content(role="user", parts=[types.Part.from_text(text=f"{model_input} Let's move to next question.")]))
                    self.messages.append(types.Content(role="model", parts=[types.Part.from_text(text="Ok.")]))
                else:
                    self.messages.append({"role": "user", "content": f"{model_input} Let's move to next question."})
                    self.messages.append({"role": "assistant", "content": "Ok."})
                self.history.append({"role": "user", "content": f"{model_input} Let's move to next question."})
                self.history.append({"role": "assistant", "content": "Ok."})
                if n == 1 and self.mode == 'generate':
                    break
            
            if self.mode == "evaluate":
                if self.thinking_mode:
                    self.save_result(self.paths.result_path, [[self.difficulty, self.task_id, self.model_family, self.model_name+'_thinking', 'run_'+str(version), max_turns, failure_num, num_correct, circuit_test_num, num_correct/circuit_test_num]])  
                else:
                    self.save_result(self.paths.result_path, [[self.difficulty, self.task_id, self.model_family, self.model_name, 'run_'+str(version), max_turns, failure_num, num_correct, circuit_test_num, num_correct/circuit_test_num]])  

    '''check if LLM make mistakes in output format.'''
    def has_format_mistake(self, input):
        if 'invalid' in input.lower() or 'error' in input.lower() or 'mistake' in input.lower():
            return True
        else:
            return False
    
    '''check if containing words'''
    def check_text_format(self, text):
        import string
        if self.task == 'code':
            if text == '':
                return False
            allowed_chars = string.ascii_letters + string.digits
            return all(char in allowed_chars for char in text)
        elif self.task == 'encryption':    # only allows for number letter space and comma
            if text == '':
                return False
            allowed_chars = string.ascii_letters + string.digits + ' ' + ','
            return all(char in allowed_chars for char in text)
        elif self.task == 'physics':
            try:
                parsed_object = ast.literal_eval(text)
                if isinstance(parsed_object, dict):
                    return parsed_object
                else:
                    return False
            except (ValueError, SyntaxError):
                return False
            except TypeError:
                return False