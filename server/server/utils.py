import io
import cv2
import time
import base64
import requests
from os.path import join
from PIL import Image
from typing import List, Optional
import numpy as np
import numpy.typing as npt
from firebase_admin import storage

def download_image(url: str, cache_dir: str, filename: str) -> str:
  '''Download an image from a URL and save it to the cache directory.
  :param url: The URL of the image to download
  :param cache_dir: The directory to save the image to
  :param filename: The filename to save the image as
  :return: The path to the downloaded image
  '''
  response = requests.get(url)
  image_path = join(cache_dir, filename)
  with open(image_path, 'wb') as f:
    f.write(response.content)
  return image_path

def tick() -> int:
  '''Get the current time in seconds.'''
  return int(time.time())

def upload_file_to_firebase(file_path: str, blob_path: str) -> str:
  '''Upload a file to firebase.
  :param file_path:
  :param blob_path: Desired blob path
  '''
  bucket = storage.bucket()
  blob = bucket.blob(blob_path)
  blob.upload_from_filename(file_path)
  blob.make_public()

  return blob.public_url

def binary_mask_to_coco_format(mask: npt.NDArray) -> List[List[int]]:
  '''Convert a binary mask to COCO segmentation format.
  :param mask: A 2D numpy array where the object is represented by 1s and the background by 0s.
  :return segmentation: list of contours
  '''
  # Ensure binary mask is binary (0 or 1)
  mask = mask.astype(np.uint8)
  # Find contours in the binary mask
  contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
  segmentations = []
  for contour in contours:
      # Flatten the contour array and convert it to a list of points
      segmentation = contour.flatten().tolist()
      segmentation = [int(round(x)) for x in segmentation]  # quantize
      segmentations.append(segmentation)
  return segmentations

def coco_format_to_binary_mask(paths: List[List[int]], image_width: int, image_height: int) -> npt.NDArray:
  '''Convert a COCO segmentation mask back to a binary mask.
  :return mask: h x w shape
  '''
  # Create an empty binary mask
  mask = np.zeros((image_height, image_width), dtype=np.uint8)
  # Iterate over each segmentation contour
  for path in paths:
      # Convert the list of points back to the contour format (Nx1x2) required by OpenCV
      contour = np.array(path, dtype=np.int32).reshape(-1, 1, 2)
      # Draw the contour on the mask with the value 1
      cv2.drawContours(mask, [contour], -1, color=1, thickness=cv2.FILLED)
  return mask

def round_bbox(bbox: List[float]) -> List[int]:
  '''Round a bounding box to the nearest integer.
  '''
  return [int(round(x)) for x in bbox]

def binary_mask_to_bbox(mask: npt.NDArray) -> Optional[List[float]]:
  '''Convert a binary mask to a bounding box
  :param np.ndarray:
  :return x1, y1, x2, y2:
  '''
  mask = mask.astype(int)  # binary - 0/1 mask
  # Check if mask is empty (all zeros)
  if not np.any(mask):
    return None
  # Find non-zero elements directly
  rows = np.any(mask, axis=1)
  cols = np.any(mask, axis=0)
  # Find the minimum and maximum coordinates
  y_min, y_max = np.where(rows)[0][[0, -1]]
  x_min, x_max = np.where(cols)[0][[0, -1]]
  # Return the bounding box coordinates, +1 to make it inclusive
  bbox = [x_min, y_min, x_max + 1, y_max + 1]
  return bbox

def create_masked_image(image: npt.NDArray, mask: npt.NDArray, out_path: str) -> str:
  '''Create a masked image and save it to the cache directory.
  :param image: The image to mask (H, W, C)
  :param mask: The mask to apply to the image (H, W) - binary mask
  :param out_path: The path to save the masked image to
  :return: The path to the masked image
  '''
  # Convert mask to 3 channels to match image dimensions (H, W, C)
  if len(mask.shape) == 2:  # If mask is single channel (H, W), make it (H, W, 1)
    mask = np.repeat(mask[:, :, np.newaxis], 3, axis=2)
  # Ensure the mask is binary (0 or 255), adjust based on your mask's values
  mask = (mask > 0).astype(np.uint8) * 255
  # Create a 4-channel mask where the fourth channel is 0 for transparency
  alpha_channel = (mask[..., 0] > 0).astype(np.uint8) * 255  # Alpha channel based on the mask
  # Add the alpha channel to the image to make it fully transparent where mask == 0
  masked_image = np.dstack([image[:, :, :3], alpha_channel])  # Combine RGB + Alpha
  masked_image[mask[..., 0] == 0] = [0, 0, 0, 0]
  # Convert image and mask to PIL format for cropping and saving
  masked_pil = Image.fromarray(masked_image, 'RGBA')
  # Crop the image to the bounding box
  cropped_pil = masked_pil.crop(binary_mask_to_bbox(mask[..., 0]))
  # Save the cropped and masked image
  cropped_pil.save(out_path, 'PNG')
  return out_path

def standardize_text(text: str) -> str:
  '''Standardize text by removing leading and trailing whitespace.'''
  return text.strip()

def decode_base64_to_image(base64_string: str) -> 'Image.Image':
  '''Decode a base64 string to an image.
  :param base64_string: The base64 string to decode
  :return: The decoded image
  '''
  image_data = base64.b64decode(base64_string)
  return Image.open(io.BytesIO(image_data))

def encode_image_to_base64(image: 'Image.Image') -> str:
  '''Encode an image to a base64 string.
  :param image: The image to encode
  :return: The encoded image
  '''
  buffered = io.BytesIO()
  image.save(buffered, format="PNG")
  image_bytes = buffered.getvalue()
  base64_string = base64.b64encode(image_bytes).decode("utf-8")
  return base64_string
