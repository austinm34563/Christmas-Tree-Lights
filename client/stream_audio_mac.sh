#!/bin/bash

# Mac → Pi audio streaming
ffmpeg \
    -f avfoundation -i ":BlackHole 2ch" \
    -ac 2 -ar 44100 -f s16le \
    -acodec pcm_s16le \
    tcp://raspberrypi.local:5005

