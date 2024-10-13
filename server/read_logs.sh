#!/bin/bash

# Check for the -c option
while getopts ":c" opt; do
  case $opt in
    c)
      # Wipe the output log
      > output/output.log
      echo "Output log wiped."
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      exit 1
      ;;
  esac
done

tail -f output/output.log
