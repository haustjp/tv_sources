# 每3天的23:50分清理一次日志
50 23 */3 * * rm -rf /scripts/logs/*.log

# IPTV自动抓取脚本
30 0 * * * sh /scripts/custom/auto_run_iptv.sh >>/scripts/logs/auto_run_iptv.log 2>&1
