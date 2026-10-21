#!/bin/bash
# Lighthouse 12 локально, мобильный и десктопный профиль, только производительность
export CHROME_PATH=/opt/pw-browsers/chromium-1194/chrome-linux/chrome
LH=/tmp/claude-0/-home-claude/97f9dc36-7fb1-518c-96b3-65ea34b0a075/scratchpad/lh/node_modules/.bin/lighthouse
OUT=/home/claude/zabory/notes/raw_sites/lighthouse
while read slug url; do
  for mode in mobile desktop; do
    extra=""; [ "$mode" = desktop ] && extra="--preset=desktop"
    timeout 240 $LH "$url" --quiet $extra --chrome-flags="--headless=new --no-sandbox --proxy-server=http://127.0.0.1:34453" --only-categories=performance --output=json --output-path=$OUT/${slug}_$mode.json >/dev/null 2>&1
    echo "$slug $mode $?"
    sleep 3
  done
done < "$1"
