import numpy as np
import numpy.typing as npt
from PIL import Image
from os.path import join, realpath, dirname

def get_base_dir() -> str:
  return realpath(dirname(__file__))

def get_checkpoints_dir() -> str:
  return join(get_base_dir(), '../checkpoints')

def load_image(image: str) -> npt.NDArray:
  '''Read the image into a NumPy array.
  :param image: Path to an image
  '''
  im_pil = Image.open(image).convert('RGB')
  im = np.asarray(im_pil)
  return im
