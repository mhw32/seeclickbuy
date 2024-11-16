from os.path import dirname
from os import environ as env
import sys; sys.path.append(dirname(__file__))  # need to add path
from typing import List, Tuple
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from seeclickbuy.models import edit_caption, init_openai
from server.database import get_firebase_client
from server.crud import (
  create_click, 
  create_chat,
  favorite_item,
  unfavorite_item,
  fetch_item_by_id, 
  fetch_click_by_id,
  fetch_items_for_click,
  fetch_favorite_items_for_click,
  fetch_recent_clicks_by_user,
  search_items_for_click,
  upgrade_click_description_version,
  update_is_processed_for_click,
)
from server.schemas import ClickCreate, Click, Item, ChatCreate, Chat
from server.tasks import click_task, chat_task

# Load environment variables
load_dotenv()
assert env.get('SERP_API_KEY') is not None, 'SERP_API_KEY is not defined'
assert env.get('OPENAI_API_KEY') is not None, 'OPENAI_API_KEY is not defined'
# Initialize firebase client
db = get_firebase_client()
# Initialize FastAPI
app = FastAPI(title="See Click Buy API")
# Add CORS to site
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
# Initialize OpenAI client
openai = init_openai(env['OPENAI_API_KEY'])

@app.post("/")
def read_root():
  return {"message": "Welcome to the See Click Buy API"}

@app.post("/click")
def click(body: 'ClickCreate') -> Click:
  '''User clicks on an image. This endpoint will create a click document in firebase.
  It also triggers a celery task to process the click.
  :return: the created click document
  '''
  # Create the click document
  click = create_click(db, body)
  # Trigger the click task
  try:
    click_task.delay(click.click_id, body.base64_image)
  except Exception as e:
    print(f'Error processing click {click.click_id}: {e}')
  return click

@app.post("/chat")
def chat(body: 'ChatCreate') -> Tuple[Click, Chat]:
  '''Create a chat document in firebase.
  :return: click, chat
  '''
  # Fetch the click document and make sure its valid
  click = fetch_click_by_id(db, body.click_id)
  if click.description is None:
    raise HTTPException(status_code=400, detail=f"Click {body.click_id} description is not available")
  # Update the click to not be processed
  click = update_is_processed_for_click(db, body.click_id, False)
  # Call OpenAI to get the new description, factoring in user's instruction
  new_description = edit_caption(openai, click.description, body.text, model="gpt-4o-mini")
  # Create a chat document for a record
  chat = create_chat(db, body, click.description, new_description, click.version)
  # Upgrade the click version
  click = upgrade_click_description_version(db, body.click_id, new_description)
  # Trigger the click task
  try:
    chat_task.delay(click.click_id)
  except Exception as e:
    print(f'Error processing click {click.click_id}: {e}')
  return click, chat

@app.post("/click/{click_id}/search")
def search_click_items(click_id: str) -> List[Item]:
  '''Search for items in the click.
  :param click_id: id of the click
  :return: list of items
  '''
  items = search_items_for_click(db, env['SERP_API_KEY'], click_id)
  return items

@app.post("/item/{item_id}/favorite")
def favorite(item_id: str) -> Item:
  '''Favorite an item
  :param item_id: id of the item
  '''
  item = favorite_item(db, item_id)
  return item

@app.post('/item/{item_id}/unfavorite')
def unfavorite(item_id: str) -> Item:
  '''Unfavorite an item
  :param item_id: id of the item
  :return: the updated item
  '''
  item = unfavorite_item(db, item_id)
  return item

@app.post("/item/{item_id}")
def fetch_item(item_id: str) -> Item:
  '''Fetch a item by id.
  :param item_id: id of the item
  :return: item
  '''
  item = fetch_item_by_id(db, item_id)
  return item

@app.post("/click/{click_id}")
def fetch_click(click_id: str) -> Click:
  '''Fetch a click by id.
  :param click_id: id of the click
  :return: click
  '''
  click = fetch_click_by_id(db, click_id)
  return click

@app.post("/click/{click_id}/items")
def fetch_click_items(click_id: str, limit: int = 10) -> List[Item]:
  '''Fetch items for a given click.
  :param click_id: id of the click
  :param limit: maximum number of items to return
  :return: list of items
  '''
  click = fetch_click_by_id(db, click_id)
  items = fetch_items_for_click(db, click_id, click.version, limit)
  return items

@app.post("/click/{click_id}/items/favorites")
def fetch_click_favorite_items(click_id: str, limit: int = 10) -> List[Item]:
  '''Fetch favorited items for a given click.
  :param click_id: id of the click
  :param limit: maximum number of favorites to return
  :return: list of favorite items
  '''
  items = fetch_favorite_items_for_click(db, click_id, limit)
  return items

@app.post("/user/{user_id}/clicks")
def fetch_recent_clicks(user_id: str, limit: int = 10) -> List[Click]:
  '''Fetch recent clicks for a given user.
  :param user_id: id of the user
  :param limit: maximum number of clicks to return
  :return: list of clicks
  '''
  clicks = fetch_recent_clicks_by_user(db, user_id, limit)
  return clicks
