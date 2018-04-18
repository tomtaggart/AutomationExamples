#!/bin/sh

chromedriver_pids=($(ps -ef | grep chromedriver | awk '{print $2}' | grep -v grep))
chrome_pids=($(ps -ef | grep Chrome | awk '{print $2}' | grep -v grep))

for i in "${chrome_pids[@]}"
  do
    :
    kill $i
  done
  
for i in "${chromedriver_pids[@]}"
  do
    :
    kill $i
  done

shutdown -r now
