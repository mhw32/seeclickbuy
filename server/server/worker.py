from os import environ as env
from dotenv import load_dotenv
from celery import Celery

from .tasks import click_task

load_dotenv()  # Loads all the project specific environment 

# Initialize a celery application
assert env.get('BROKER_URL') is not None, 'Broker URL is not defined'
app = Celery('tasks', broker=env.get('BROKER_URL'), broker_connection_retry_on_startup=False) 
print(f'Initialized celery with broker: {app.conf.broker_url}')

# Set wait time to 24 hours so we don't reassign tasks ever
app.conf.broker_transport_options = {'visibility_timeout': 86400} 
app.conf.broker_connection_retry = True
app.conf.broker_connection_max_retries = 5  # Retry 5 times
app.conf.broker_connection_retry_interval = 10  # Retry every 10 seconds

app.autodiscover_tasks(['server.tasks'])
