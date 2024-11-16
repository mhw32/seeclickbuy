#!/bin/bash

celery -A server.worker worker --loglevel=DEBUG --concurrency 1 --pool solo
