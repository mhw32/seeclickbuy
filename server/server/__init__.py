import os
os.environ['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = 'YES'
os.environ['OMP_NUM_THREADS'] = '1'

import multiprocessing
multiprocessing.set_start_method('spawn', force=True)

# Addresses error: `WARNING:kombu.connection:No hostname was supplied. Reverting to default 'localhost'`
# https://stackoverflow.com/questions/68167239/celery-no-hostname-was-supplied-reverting-to-default-localhost
from .worker import app as celery_app

__all__ = ['celery_app']
