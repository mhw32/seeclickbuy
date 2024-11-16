#!/bin/bash
apt-get update -y
apt-get install build-essential python3-dev -y
apt-get install vim -y
apt-get install redis-server -y
apt-get install screen -y
apt-get install git-lfs -y

# Start redis 
service redis-server start

# Install ngrok
curl -sSL https://ngrok-agent.s3.amazonaws.com/ngrok.asc \
  | tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null \
  && echo "deb https://ngrok-agent.s3.amazonaws.com buster main" \
  | tee /etc/apt/sources.list.d/ngrok.list \
  && apt update \
  && apt install ngrok
