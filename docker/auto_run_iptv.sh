#!/bin/sh

function main(){
   cd /scripts/tv_sources
   git pull
   python3 get_iptv.py
#    python3 get_iptv_source.py -i '北京' -o 'beijing'
#    python3 get_iptv_source.py -i '河南' -o 'henan'
#    python3 get_iptv_source.py -i '四川' -o 'sichuan'
#    python3 get_iptv_source.py -t 'first'
   cp -rf /scripts/tv_sources/sources/* /scripts/iptv/
   rm -rf /scripts/tv_sources/sources/* 
   rm -rf /scripts/tv_sources/guangdong.txt
}

function commit(){
    git add .
    git commit -m 'auto'
    git push
}

main

commit
