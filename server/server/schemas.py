from typing import Optional, List, Tuple
from pydantic import BaseModel
from firebase_admin import firestore

class ClickCreate(BaseModel):
  base64_image: str
  click: Optional[Tuple[int, int]] = None
  selection: Optional[Tuple[int, int, int, int]] = None
  user_id: Optional[str] = None
  channel: Optional[str] = None

class ClickUpdate(BaseModel):
  image_url: str
  image_size: Tuple[int, int]
  bbox: Tuple[int, int, int, int]
  segm: List[int]
  description: Optional[str] = None
  masked_url: str
  masked_size: Tuple[int, int]

class Click(BaseModel):
  '''Firebase object for clicks.
  :param click_id: id of the click
  :param image_url: url of the image
  :param image_size: size of the image (width, height)
  :param click: click coordinates
  :param selection: selection coordinates
  :param user_id: id of the user
  :param masked_url: url of the masked image
  :param masked_size: size of the masked image (width, height)
  :param bbox: bounding box coordinates
  :param segm: segmentation mask
  :param description: description of the click
  :param created_at: creation timestamp
  :param updated_at: update timestamp
  '''
  click_id: Optional[str] = None
  image_url: Optional[str] = None
  image_size: Optional[Tuple[int, int]] = None
  click: Optional[Tuple[int, int]] = None
  selection: Optional[Tuple[int, int, int, int]] = None
  user_id: Optional[str] = None
  masked_url: Optional[str] = None
  masked_size: Optional[Tuple[int, int]] = None
  bbox: Optional[Tuple[int, int, int, int]] = None
  segm: Optional[List[int]] = None
  description: Optional[str] = None
  channel: Optional[str] = None
  version: Optional[int] = 1
  is_processed: bool = False
  created_at: int
  updated_at: int

class ChatCreate(BaseModel):
  click_id: str
  text: str

class Chat(BaseModel):
  '''Firebase for a chat.
  :param chat_id: id of the chat
  :param click_id: id of the click
  :param text: text of the chat
  :param pre_description: description of the click before the chat
  :param post_description: description of the click after the chat
  :param created_at: creation timestamp
  :param updated_at: update timestamp
  '''
  chat_id: Optional[str] = None
  click_id: str
  text: str
  pre_description: str
  post_description: str
  created_at: int
  updated_at: int

class Item(BaseModel):
  '''Firebase for a retrieved item.
  :param item_id: id of the item
  :param click_id: id of the click
  :param price_usd: price of the item in USD
  :param image_url: url of the item image
  :param item_url: url of the item
  :param source: store/distribution/channel of the item
  :param name: name of the item
  :param description: description of the item
  :param channel: store/distribution/channel of the item
  :param is_favorite: whether the item is a favorite
  :param created_at: creation timestamp
  :param updated_at: update timestamp
  '''
  item_id: Optional[str] = None
  click_id: str
  title: str
  link: str
  source: str
  source_icon: Optional[str] = None
  price_value: float
  price_currency: str
  thumbnail: Optional[str] = None
  in_stock: bool
  is_favorite: bool = False
  version: Optional[int] = 1
  created_at: int
  updated_at: int

def click_to_pydantic(fb_click: 'firestore.DocumentSnapshot', click_id: str) -> Click:
  fb_click_dict = fb_click.to_dict()
  click = Click.model_validate(fb_click_dict)
  click.click_id = click_id
  return click

def chat_to_pydantic(fb_chat: 'firestore.DocumentSnapshot', chat_id: str) -> Chat:
  fb_chat_dict = fb_chat.to_dict()
  chat = Chat.model_validate(fb_chat_dict)
  chat.chat_id = chat_id
  return chat

def item_to_pydantic(fb_item: 'firestore.DocumentSnapshot', item_id: str) -> Item:
  fb_item_dict = fb_item.to_dict()
  item = Item.model_validate(fb_item_dict)
  item.item_id = item_id
  return item
