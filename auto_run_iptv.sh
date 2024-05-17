#!/bin/sh

function main(){
   cd /scripts/tv_sources
   python3 get_iptv_source.py
}

function commit(){
    git add .
    git commit -m 'auto'
    git push
}

main

commit