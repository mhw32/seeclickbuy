#!/bin/bash

if command -v git-lfs &> /dev/null
then
  git-lfs pull  # Download the checkpoints
else
  echo "GIT-LFS not installed. Please run `apt-get install git-lfs`."
  exit 1
fi

if command -v nvidia-smi &> /dev/null
then
  # Initialize conda (needed in non-interactive scripts)
  eval "$(conda shell.bash hook)"

  # Create the conda environment
  conda create -n seeclickbuy python=3.10 -y;

  # Activate the conda environment
  conda activate seeclickbuy

  # Install PyTorch and other dependencies
  conda install pytorch==2.4.1 torchvision==0.19.1 pytorch-cuda=12.4 -c pytorch -c nvidia

  # Install ai/ requirements
  cd ai
  pip install -r requirements.txt;  # Install ai/ requirements
  pip install -e .                  # install this package
  git clone https://github.com/facebookresearch/segment-anything-2.git
  cd segment-anything-2
  pip install -e .                  # Install SAM2
  export PYTHONPATH="$PYTHONPATH:/src/segment-anything-2"
  cd ..

  # Install server/ requirements
  cd server
  pip install -r requirements.txt   # Install server/ requirements
  pip install -e .
  cd ..
else
  echo "No GPU found. You must have a GPU to install this package."
  exit 1
fi
