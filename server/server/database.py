from os.path import dirname, join
from typing import Optional
from firebase_admin import firestore, credentials, get_app, initialize_app

SERVICE_ACCOUNT_FILE = join(dirname(__file__), 'seeclickbuy.json')
FIREBASE_STORAGE_BUCKET = 'seeclickbuy-a6000.appspot.com'

def get_firebase_client(service_account_file: Optional[str] = SERVICE_ACCOUNT_FILE) -> 'firestore.Client':
  '''Instantiate a firebase client.
  :param service_account_file: path to service account file
  :return: a firebase client
  '''
  firebase_credentials = credentials.Certificate(service_account_file)
  try:
      get_app()
  except ValueError:
      initialize_app(firebase_credentials, {'storageBucket': FIREBASE_STORAGE_BUCKET})
  client = firestore.client()
  return client
