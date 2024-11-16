import torch
import transformers
import numpy as np
import numpy.typing as npt
from openai import OpenAI
from os.path import join
from typing import List, Dict, Tuple, Optional
from .utils import get_checkpoints_dir
from .prompts import summarize_captions_prompt, edit_caption_prompt

if torch.cuda.is_available():
  from sam2.build_sam import build_sam2
  from sam2.sam2_image_predictor import SAM2ImagePredictor
else:
  print(f"No CUDA found. Cannot import SAM2.")

def load_sam2(model_cfg: str = 'sam2.1_hiera_large', device_name: str = 'cuda') -> 'SAM2ImagePredictor':
  '''Load all the models needed to do inference.
  '''
  device = torch.device(device_name)
  ckpt_path = join(get_checkpoints_dir(), f'{model_cfg}.pt')
  config_path = 'configs/sam2.1/sam2.1_hiera_l.yaml'
  sam2_model = build_sam2(config_path, ckpt_path, device=device)
  predictor = SAM2ImagePredictor(sam2_model)
  return predictor

def infer_click(sam2: 'SAM2ImagePredictor', image: npt.NDArray, click: Tuple[int, int]) -> npt.NDArray:
  '''Infer a click for an image.
  :param sam2: SAM2 predictor
  :param image: loaded image to infer click on
  :param click: click coordinates
  :return: binary mask of clicked object
  '''
  sam2.set_image(image)
  input_point = np.array([[click[0], click[1]]])
  input_label = np.array([1])
  # We may want to do something with the scores
  masks, _, _ = sam2.predict(
    point_coords=input_point, 
    point_labels=input_label,
    multimask_output=True,
  )
  if len(masks) == 0:
    raise ValueError(f'No mask found for click {click}')
  return masks[0]

def infer_selection(sam2: 'SAM2ImagePredictor', image: npt.NDArray, selection: Tuple[int, int, int, int]) -> npt.NDArray:
  '''Infer a bounding box for an image.
  :param sam2: SAM2 predictor
  :param image: loaded image to infer bbox on
  :param selection: selection coordinates (x1, y1, x2, y2)
  :return: binary mask of clicked object
  '''
  sam2.set_image(image)
  input_selection = np.array([[selection[0], selection[1], selection[2], selection[3]]])
  input_label = np.array([1])
  # We may want to do something with the scores
  masks, _, _ = sam2.predict(
    point_coords=None, 
    point_labels=input_label,
    box=input_selection,
    multimask_output=True,
  )
  if len(masks) == 0:
    raise ValueError(f'No mask found for selection {selection}')
  return masks[0]

def init_huggingface_llm(model: str = 'meta-llama/Meta-Llama-3.1-8B-Instruct') -> transformers.Pipeline:
  '''Load a Huggingface LLM model.
  - meta-llama/Meta-Llama-3.1-8B-Instruct
  - meta-llama/Meta-Llama-3.1-70B-Instruct
  :param model: model name
  '''
  pipeline = transformers.pipeline(
    "text-generation",
    model=model,
    model_kwargs={"torch_dtype": torch.bfloat16},
    device_map="auto",
  )
  return pipeline

def craft_llm_messages(system_prompt: str, user_prompt: str) -> List[Dict]:
  return [
    {'role': 'system', 'content': system_prompt},
    {'role': 'user', 'content': user_prompt},
  ]

def call_llm(
  pipeline: transformers.pipeline, 
  system_prompt: str, 
  user_prompt: str, 
  max_new_tokens: int = 256,
  temperature: float = 0.8,
  ) -> str:
  '''Call Llama model to generate a response.
  :return generation: generated text
  '''
  messages = craft_llm_messages(system_prompt, user_prompt)
  outputs = pipeline(
    messages, 
    max_new_tokens=max_new_tokens, 
    temperature=temperature,
    pad_token_id=pipeline.tokenizer.eos_token_id,
  )
  generation = outputs[0]["generated_text"][-1]
  return generation

def init_openai(api_key: str) -> 'OpenAI':
  '''Initialize OpenAI client.
  '''
  return OpenAI(api_key=api_key)

def call_openai(
  client: 'OpenAI',
  system_prompt: str,
  user_prompt: str,
  model: str = "gpt-3.5-turbo",
  max_tokens: int = 10,
) -> Optional[str]:
  '''Call OpenAI API to generate a response.
  :param system_prompt: system prompt
  :param user_prompt: user prompt
  :param model: OpenAI model name
  :param max_tokens: maximum number of tokens in the response
  '''
  messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_prompt}
  ]
  try:
    response = client.chat.completions.create(
      model=model,
      messages=messages,
      max_tokens=max_tokens,
    )
    output = response.choices[0].message.content.strip()
  except Exception as e:
    print(f'Error calling OpenAI: {e}')
    return None
  return output

def summarize_captions(client: 'OpenAI', captions: List[str], model: str = "gpt-3.5-turbo") -> Optional[str]:
  '''Summarize a list of captions.
  :param captions: list of captions to summarize
  :param model: OpenAI model name
  :return: summarized caption
  '''
  system_prompt, user_prompt = summarize_captions_prompt(captions)
  return call_openai(client, system_prompt, user_prompt, model)

def edit_caption(client: 'OpenAI', caption: str, instruction: str, model: str = "gpt-3.5-turbo") -> Optional[str]:
  '''Edit a caption with additional instructions.
  :param caption: original caption
  :param instruction: additional instruction
  :param model: OpenAI model name
  :return: edited caption
  '''
  system_prompt, user_prompt = edit_caption_prompt(caption, instruction)
  return call_openai(client, system_prompt, user_prompt, model)
