#!/bin/sh

gitPath='/scripts/tv_sources'
hh=$(date +%-H)
mergedListFile="/scripts/docker/merged_list_file.sh"

function initTvSources() {
    ## 克隆tv_sources仓库
    chmod 600 /root/.ssh/id_rsa_oracle
    git config --global user.name "haustjp"
    git config --global user.email "haustjp@gmail.com"

    if [ 1 -gt 0 ]; then
        if [ ! -d "$gitPath" ]; then
            echo "未检查到gitPath仓库脚本，初始化下载相关脚本..."
            chmod 600 /root/.ssh/id_rsa_oracle
            git config --global user.name "haustjp"
            git config --global user.email "haustjp@gmail.com"
            git clone -b master git@github.com:haustjp/tv_sources.git $gitPath
        else
            echo "更新tv_sources脚本相关文件..."
            git -C $gitPath remote set-url origin git@github.com:haustjp/tv_sources.git
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

    # 清理日志
    echo -e "\n# 每3天的23:50分清理一次日志" >>${mergedListFile}
    echo "50 23 */3 * * rm -rf /scripts/logs/*.log" >>${mergedListFile}

    # IPTV自动抓取
    echo -e "\n# IPTV自动抓取脚本" >>${mergedListFile}
    echo "30 0 * * * sh /scripts/custom/auto_run_iptv.sh >>/scripts/logs/auto_run_iptv.log 2>&1" >>${mergedListFile}
}

initTvSources
