#!/bin/sh

gitPath='/scripts/tv_sources'

function initTvSources() {
    ## 克隆tv_sources仓库
    if [ 1 -gt 0 ]; then
        if [ ! -d "$gitPath" ]; then
            echo "未检查到gitPath仓库脚本，初始化下载相关脚本..."
            git clone -b master https://github.com/haustjp/tv_sources.git $gitPath
        else
            echo "更新tv_sources脚本相关文件..."
            git -C $gitPath remote set-url origin https://github.com/haustjp/tv_sources.git
            git -C $gitPath reset --hard
            git -C $gitPath pull origin master --rebase
        fi
    fi

    if [ $hh -eq 11 ] || [ $hh -eq 23 ] || [ ! -f "/root/tv_sources.lock" ]; then
        pip3 install -r /scripts/tv_sources/requirements.txt
        echo '' >/root/tv_sources.lock
    else
        echo "本次不执行安装tv_sources依赖，跳过..."
    fi
     cp -rf /scripts/tv_sources/auto_run_iptv.sh /scripts/custom/auto_run_iptv.sh
}

initTvSources
