#!/bin/bash

sudo apt install ffmpeg

tar -xvzf overfeat-v04-2.tgz
cd overfeat
python download_weights.py