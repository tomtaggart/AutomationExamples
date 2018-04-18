#!/bin/sh

log_files=($(ls /Users/test/PythonLogs | grep -e "[log|LOG]"))

#set -x
for i in "${log_files[@]}"
  do
    :
    [ -w $i ] || $(chmod 664 /Users/test/PythonLogs/$i)
  done
#set +x