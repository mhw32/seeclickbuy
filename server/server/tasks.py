import numpy as np
from os import makedirs
from os.path import join
from os import environ as env
from typing import List
from dotenv import load_dotenv
from celery import shared_task
from celery.utils.log import get_task_logger
from celery.signals import worker_process_init
from seeclickbuy.utils import load_image
from seeclickbuy.models import load_sam2, init_openai, summarize_captions
from seeclickbuy.models import infer_click, infer_selection
from .database import get_firebase_client
from .schemas import click_to_pydantic
from .crud import (
  update_click, 
  search_items_for_click, 
  search_items_for_text,
  update_is_processed_for_click,
)
from .schemas import ClickUpdate, Item
from .utils import (
  tick, 
  binary_mask_to_coco_format, 
  round_bbox, 
  upload_file_to_firebase,
  binary_mask_to_bbox, 
  create_masked_image,
  standardize_text,
  decode_base64_to_image,
)

def build_response(success, data={}, error=None):
  return {'success': success, 'error': error, 'data': data}

logger = get_task_logger("task-logger")

# Load environment variables
load_dotenv()
assert env.get('SERP_API_KEY') is not None, 'SERP_API_KEY is not defined'
assert env.get('OPENAI_API_KEY') is not None, 'OPENAI_API_KEY is not defined'

# Initialize models and db only when called
sam2 = None
db = None
openai = None

@worker_process_init.connect
def init_worker_models(**kwargs):
  '''Initialize models only when called.
  '''
  global sam2, db, openai
  if sam2 is None:
    start_time = tick()
    sam2 = load_sam2()
    logger.info(f"sam2 initialized - {tick()-start_time}s elapsed")
  if db is None:
    start_time = tick()
    db = get_firebase_client()
    logger.info(f"db connected - {tick()-start_time}s elapsed")
  if openai is None:
    start_time = tick()
    openai = init_openai(env['OPENAI_API_KEY'])
    logger.info(f"openai initialized - {tick()-start_time}s elapsed")

@shared_task(name="seeclickbuy:click_task")
def click_task(click_id: str, base64_image: str, cache_dir: str = './cache') -> bool:
  '''
  :param click_id: The firebase document id of the click
  :param base64_image: The base64 encoded image
  :param cache_dir: The directory to store the cache in
  '''
  logger.info(f'received click task with click_id={click_id}')
  # Fetch click
  start_time = tick()
  fb_click_ref = db.collection('Clicks').document(click_id)
  fb_click = fb_click_ref.get()
  if not fb_click.exists:  # bail if click does not exist
    logger.error(f'click {click_id} document does not exist. quitting...')
    return build_response(success=False, error=f"click {click_id} does not exist")
  click = click_to_pydantic(fb_click, click_id)
  logger.info(f'fetched click doc - {tick()-start_time}s elapsed')  
  if not click.click and not click.selection:
    logger.error(f'click {click_id} does not have a click or selection. quitting...')
    return build_response(success=False, error=f"click {click_id} does not have a click or selection")
  # Use cached directory to store the image
  makedirs(cache_dir, exist_ok=True)
  image_pil = decode_base64_to_image(base64_image)  # Parse the base64 image
  image_pil = image_pil.convert('RGB')              # Convert to rgb
  width, height = image_pil.size
  logger.info(f'image loaded - {tick()-start_time}s elapsed')
  image_path = join(cache_dir, f'{click_id}.png')
  image_pil.save(image_path)
  image = np.asarray(image_pil)
  # Upload the image to Firebase Storage
  image_url = upload_file_to_firebase(image_path, f'images/{click.click_id}.png')
  logger.info(f'uploading image - {tick()-start_time}s elapsed')
  # Call SAM2 to get the mask
  # If we have a selection, use that. Otherwise, use the click
  if click.selection is not None:
    segm = infer_selection(sam2, image, click.selection)
  elif click.click is not None:
    segm = infer_click(sam2, image, click.click)
  else:
    raise ValueError(f'click {click_id} does not have a click or selection')
  logger.info(f'sam2 inference - {tick()-start_time}s elapsed')
  # Create PNG mask image and upload to Firebase Storage
  masked_path = create_masked_image(image, segm, join(cache_dir, f'{click.click_id}.masked.png'))
  logger.info(f'creating mask image - {tick()-start_time}s elapsed')
  masked = load_image(masked_path)
  # Upload the mask image to Firebase Storage
  masked_url = upload_file_to_firebase(masked_path, f'masks/{click.click_id}.png')
  logger.info(f'uploading mask image - {tick()-start_time}s elapsed')
  # Compress the info for storage
  bbox = round_bbox(binary_mask_to_bbox(segm))
  segm = binary_mask_to_coco_format(segm)
  # Search for items in the click
  try: 
    items = search_items_for_click(db, env['SERP_API_KEY'], click_id, masked_url, click.version, limit=25)
    logger.info(f'{len(items)} items found - {tick()-start_time}s elapsed')
  except Exception as e:
    logger.error(f'error searching for items: {e}')
    raise e
  items: List[Item] = items
  # Call OpenAI to get the description
  try:
    captions = [item.title for item in items]
    # for now, cap at 5 to now overwhelm
    description = summarize_captions(openai, captions[:5], model="gpt-4o-mini")
    logger.info(f'generated description: {description}')
  except Exception as e:
    logger.error(f'error summarizing captions: {e}')
    description = None
  # Update the click doc with the mask and description
  update_request = ClickUpdate(
    image_url=image_url,
    image_size=[int(width), int(height)],
    bbox=bbox,
    segm=[int(x) for x in segm[0]],
    masked_url=masked_url,
    masked_size=[int(x) for x in list(masked.shape)[:2]],  # width, height
    description=description,
  )
  click = update_click(db, click_id, update_request)
  logger.info(f'click task complete {click_id} - {tick()-start_time}s elapsed')
  return True

@shared_task(name="seeclickbuy:chat_task")
def chat_task(click_id: str) -> bool:
  '''Search for new items based on a new description.
  :param click_id: id of the click
  '''
  logger.info(f'received chat task with click_id={click_id}')
  # Fetch click
  start_time = tick()
  fb_click_ref = db.collection('Clicks').document(click_id)
  fb_click = fb_click_ref.get()
  if not fb_click.exists:  # bail if click does not exist
    logger.error(f'click {click_id} document does not exist. quitting...')
    return build_response(success=False, error=f"click {click_id} does not exist")
  click = click_to_pydantic(fb_click, click_id)
  logger.info(f'fetched click doc - {tick()-start_time}s elapsed')
  # Bail if click does not have a description
  if click.description is None:
    logger.error(f'click {click_id} does not have a description. quitting...')
    return build_response(success=False, error=f"click {click_id} does not have a description")
  # Search for items in the click
  try:  
    items = search_items_for_text(db, env['SERP_API_KEY'], click_id, standardize_text(click.description), click.version, limit=25)
    logger.info(f'{len(items)} items found - {tick()-start_time}s elapsed')
  except Exception as e:
    logger.error(f'error searching for items: {e}')
    return False
  # Update the click to be processed
  click = update_is_processed_for_click(db, click_id, True)
  logger.info(f'chat task complete - {tick()-start_time}s elapsed')
  return True
