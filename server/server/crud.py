import time
from typing import List, Dict, Any
from serpapi import GoogleSearch
from firebase_admin import firestore
from .schemas import ClickCreate, Click, ClickUpdate, ChatCreate, Chat, Item
from .schemas import click_to_pydantic, chat_to_pydantic, item_to_pydantic

def create_click(db: 'firestore.Client', click_request: 'ClickCreate') -> Click:
  '''Create a click document in firebase.
  :note: it sets `is_processed` to `False` and waits for the job to set it to `True`
  '''
  now = int(time.time())
  click = Click(
    click=click_request.click,
    selection=click_request.selection,
    user_id=click_request.user_id,
    channel=click_request.channel,
    version=1,
    is_processed=False,
    created_at=now,
    updated_at=now,
  )
  _, click_ref = db.collection('Clicks').add(click.model_dump())
  click.click_id = click_ref.id
  return click

def update_click(db: 'firestore.Client', click_id: str, update_request: 'ClickUpdate') -> Click:
  '''Update a click document in firebase.
  :note: this sets `is_processed` to `True`
  '''
  now = int(time.time())
  click_ref = db.collection('Clicks').document(click_id)
  click_doc = click_ref.get()
  if not click_doc.exists:
    raise ValueError(f'Click with id {click_id} does not exist')
  click_ref.update({
    'image_url': update_request.image_url,
    'image_size': update_request.image_size,
    'bbox': update_request.bbox,
    'segm': update_request.segm,
    'masked_url': update_request.masked_url,
    'masked_size': update_request.masked_size,
    'description': update_request.description,
    'is_processed': True,
    'updated_at': now,
  })
  click_doc = click_ref.get()
  click = click_to_pydantic(click_doc, click_id)
  return click

def fetch_click_by_id(db: 'firestore.Client', click_id: str) -> Click:
  '''Fetch a click document by id.
  '''
  fb_click = db.collection('Clicks').document(click_id).get()
  if not fb_click.exists:
    raise ValueError(f'Click with id {click_id} does not exist')
  return click_to_pydantic(fb_click, click_id)

def create_chat(
  db: 'firestore.Client', 
  chat_request: 'ChatCreate',
  pre_description: str,
  post_description: str,
  version: int,
  ) -> Chat:
  '''Create a click document in firebase.
  :note: this does not validate that the click if valid
  '''
  now = int(time.time())
  chat = Chat(
    click_id=chat_request.click_id,
    text=chat_request.text,
    pre_description=pre_description,
    post_description=post_description,
    version=version,
    created_at=now,
    updated_at=now,
  )
  _, chat_ref = db.collection('Chats').add(chat.model_dump())
  chat.chat_id = chat_ref.id
  return chat

def upgrade_click_description_version(db: 'firestore.Client', click_id: str, new_description: str) -> Click:
  '''Upgrade the version of a click.
  :param click_id: id of the click
  :param new_description: new description
  :return: the updated click
  '''
  now = int(time.time())
  click_ref = db.collection('Clicks').document(click_id)
  click_doc = click_ref.get()
  if not click_doc.exists:
    raise ValueError(f'Click with id {click_id} does not exist')
  click = click_to_pydantic(click_doc, click_id)
  try:
    click_ref.update({
      'description': new_description,
      'version': click.version + 1,
      'updated_at': now,
    })
  except Exception as e:
    raise ValueError(f'Failed to upgrade click version: {e}')
  click = fetch_click_by_id(db, click_id)
  return click

def fetch_chats_for_click(db: 'firestore.Client', click_id: str, limit: int = 10) -> List[Chat]:
  '''Fetch all chats in order for a given click.
  '''
  fb_query = db.collection('Chats')\
    .where('click_id', '==', click_id)\
    .order_by('created_at', direction=firestore.Query.DESCENDING)\
    .limit(limit)
  chats: List[Chat] = []
  for fb_chat in fb_query.stream():
    chat = chat_to_pydantic(fb_chat, fb_chat.id)
    chats.append(chat)
  return chats

def fetch_item_by_id(db: 'firestore.Client', item_id: str) -> Item:
  '''Fetch an item document by id.
  '''
  fb_item = db.collection('Items').document(item_id).get()
  if not fb_item.exists:
    raise ValueError(f'Item with id {item_id} does not exist')
  return item_to_pydantic(fb_item, item_id)

def fetch_items_for_click(db: 'firestore.Client', click_id: str, click_version: int, limit: int = 10) -> List[Item]:
  '''Fetch all items (search results) for a given click.
  :param click_id: id of the click
  :param click_version: version of the click
  :param limit: maximum number of items to return
  :return: list of items
  '''
  fb_query = db.collection('Items')\
    .where('click_id', '==', click_id)\
    .where('version', '==', click_version)\
    .order_by('created_at', direction=firestore.Query.DESCENDING)\
    .limit(limit)
  items: List[Item] = []
  for fb_item in fb_query.stream():
    item = item_to_pydantic(fb_item, fb_item.id)
    items.append(item)
  return items

def search_items_for_click(
  db: 'firestore.Client', 
  api_key: str, 
  click_id: str,
  image_url: str,
  click_version: int,
  limit: int = 50,
) -> List[Item]:
  '''Search for items in the click
  :note: this saves documents to firebase
  :param api_key: api key for serpapi
  :param click_id: id of the click
  :param image_url: url of the image
  :param click_version: version of the click
  :param limit: maximum number of items to return
  :return: list of items
  '''
  params = {
    "api_key": api_key,
    "engine": "google_lens",
    "url": image_url,
  }
  items: List[Item] = []
  try:
    search = GoogleSearch(params)
    results = search.get_dict()
    now = int(time.time())
    if 'visual_matches' in results:
      count = 0
      for match in results['visual_matches']:
        # Make sure critical fields are present
        if (('title' not in match) or 
            ('link' not in match) or 
            ('source' not in match) or
            ('price' not in match)):
          continue
        # Ignore items that are not in stock
        if not match.get('in_stock', False):
          continue
        count += 1
        # Create the item
        match: Dict[str, Any] = match
        item = Item(
          click_id=click_id,
          title=match['title'],
          link=match['link'],
          source=match['source'],
          source_icon=match.get('source_icon', None),
          price_value=match['price']['extracted_value'],
          price_currency=match['price']['currency'],
          thumbnail=match.get('thumbnail', None),
          in_stock=match.get('in_stock', False),
          is_favorite=False,
          version=click_version,
          created_at=now,
          updated_at=now,
        )
        _, item_ref = db.collection('Items').add(item.model_dump())
        item.item_id = item_ref.id
        items.append(item)
        # Stop if we have enough items
        if count >= limit:
          print(f'Found {count} items for click {click_id}. Stopping.')
          break
  except Exception as e:
    print(f'Error searching for items: {e}')
  return items

def search_items_for_text(
  db: 'firestore.Client', 
  api_key: str, 
  click_id: str,
  search_text: str,
  click_version: int,
  limit: int = 50,
) -> List[Item]:
  '''Search for items using updated text
  :note: this saves documents to firebase
  :param api_key: api key for serpapi
  :param click_id: id of the click
  :param limit: maximum number of items to return
  :return: list of items
  '''
  params = {
    "api_key": api_key,
    "engine": "google_shopping",
    "q": search_text,
    "google_domain": "google.com"
  }
  items: List[Item] = []
  try:
    search = GoogleSearch(params)
    results = search.get_dict()
    now = int(time.time())
    if 'shopping_results' in results:
      count = 0
      for match in results['shopping_results']:
        # Make sure critical fields are present
        if (('title' not in match) or
            ('product_link' not in match) or
            ('source' not in match) or
            ('extracted_price' not in match)):
          continue
        # Create the item
        match: Dict[str, Any] = match
        item = Item(
          click_id=click_id,
          title=match['title'],
          link=match['product_link'],
          source=match['source'],
          source_icon=match.get('source_icon', None),
          price_value=match['extracted_price'],
          price_currency='$',
          thumbnail=match.get('thumbnail', None),
          in_stock=True,
          is_favorite=False,
          version=click_version,
          created_at=now,
          updated_at=now,
        )
        _, item_ref = db.collection('Items').add(item.model_dump())
        item.item_id = item_ref.id
        items.append(item)
        # Stop if we have enough items
        if count >= limit:
          print(f'Found {count} items for click {click_id}. Stopping.')
          break
  except Exception as e:
    print(f'Error searching for items: {e}')
  return items

def favorite_item(db: 'firestore.Client', item_id: str) -> Item:
  '''Create a favorite document in firebase.
  '''
  now = int(time.time())
  fb_item_ref = db.collection('Items').document(item_id)
  fb_item = fb_item_ref.get()
  if not fb_item.exists:
    raise ValueError(f'Item with id {item_id} does not exist')
  try:
    fb_item_ref.update({'is_favorite': True, 'updated_at': now})
  except Exception as e:
    raise ValueError(f'Failed to favorite item: {e}')
  item = item_to_pydantic(fb_item, item_id)
  return item

def unfavorite_item(db: 'firestore.Client', item_id: str) -> Item:
  '''Unfavorite an item.
  '''
  now = int(time.time())
  fb_item_ref = db.collection('Items').document(item_id)
  fb_item = fb_item_ref.get()
  if not fb_item.exists:
    raise ValueError(f'Item with id {item_id} does not exist')
  try:
    fb_item_ref.update({'is_favorite': False, 'updated_at': now})
  except Exception as e:
    raise ValueError(f'Failed to unfavorite item: {e}')
  item = item_to_pydantic(fb_item, item_id)
  return item

def fetch_favorite_items_for_click(db: 'firestore.Client', click_id: str, limit: int = 10) -> List[Item]:
  '''Fetch favorites for a given click.
  :note: fetch items from any version
  :param click_id: id of the click
  :param limit: maximum number of items to return
  :return: list of favorite items
  '''
  fb_query = db.collection('Items')\
    .where('click_id', '==', click_id)\
    .where('is_favorite', '==', True)\
    .order_by('created_at', direction=firestore.Query.DESCENDING)\
    .limit(limit)
  items: List[Item] = []
  for fb_item in fb_query.stream():
    item = item_to_pydantic(fb_item, fb_item.id)
    items.append(item)
  return items

def fetch_recent_clicks_by_user(db: 'firestore.Client', user_id: str, limit: int = 10) -> List[Click]:
  '''Fetch recent clicks for a given user.
  :param user_id: id of the user
  :param limit: maximum number of clicks to return
  :return: list of clicks
  '''
  fb_query = db.collection('Clicks')\
    .where('user_id', '==', user_id)\
    .order_by('created_at', direction=firestore.Query.DESCENDING)\
    .limit(limit)
  clicks: List[Click] = []
  for fb_click in fb_query.stream():
    click = click_to_pydantic(fb_click, fb_click.id)
    clicks.append(click)
  return clicks

def update_is_processed_for_click(db: 'firestore.Client', click_id: str, is_processed: bool) -> Click:
  '''Update the is_processed field for a click.
  :param click_id: id of the click
  '''
  now = int(time.time())
  try:
    fb_click_ref = db.collection('Clicks').document(click_id)
    fb_click_ref.update({'is_processed': is_processed, 'updated_at': now})
  except Exception as e:
    raise ValueError(f'Failed to update is_processed for click {click_id}: {e}')
  click = fetch_click_by_id(db, click_id)
  return click
