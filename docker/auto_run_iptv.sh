#!/bin/sh

function main(){
   cd /scripts/tv_sources
   git pull
   python3 get_iptv_source.py -i '广东' -o 'guangdong'
}

function commit(){
    git add .
    git commit -m 'auto'
    git push
}

main

commit