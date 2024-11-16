from typing import List, Tuple

def summarize_captions_prompt(captions: List[str]) -> Tuple[str, str]:
  '''Prompt to describe an image.
  :param captions: list of captions to summarize
  '''
  system_prompt = '''You are a helpful assistant that summarizes product descriptions. 
You will be given multiple descriptions of the same product.
Your description should keep the most important details of the product shared across the descriptions.
Your description should be of a single item, not plural.
Do not output generic descriptions such as "various sizes" or "various styles".
Avoid questions and avoid parentheses. 
Use 5 or fewer words.
'''
  captions_str = '\n'.join([f'- {caption}' for caption in captions])
  user_prompt = f'''Please summarize the following captions into a single one:
{captions_str}
'''
  return system_prompt, user_prompt

def edit_caption_prompt(caption: str, instruction: str) -> Tuple[str, str]:
  '''Prompt to describe an image with additional instructions.
  :param caption: original caption
  :param instruction: additional instruction
  '''
  system_prompt = '''You are a helpful assistant that summarizes product descriptions. 
You will be given an original caption, and additional edits from the user. 
Your description should be of a single item, not plural.
You may add or remove words from the caption. Usually the edits will be around the brand, color, texture, shape, or design.
You should avoid questions and avoid parentheses. 
Use 10 or fewer words.
You may remove words from the original caption that contradict user instructions.
For example, if the original caption is "red shirt with blue stripes", and the user instructs you to see a yellow shirt, the new caption should be "yellow shirt with blue stripes".
'''
  user_prompt = f'''Please edit this caption to include a user instruction.
CAPTION: {caption}
INSTRUCTION: {instruction}
'''
  return system_prompt, user_prompt
