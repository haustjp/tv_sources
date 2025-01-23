from logging.handlers import TimedRotatingFileHandler
from logging import Logger
from requests import Response
import json
import requests
import re
import os
import sys
import getopt
import time
import logging
import platform
import copy


logger: Logger = None
config_path = os.environ.get('CONFIG_PATH')
authUrl: str = None
host_url: str = '120.87.11.25:33200'
all_channels_url: str = 'http://120.87.12.38:8083/epg/api/custom/getAllChannel.json'


def get_os():
    os_name = os.name
    if os_name == 'nt':
        return 'Windows'
    elif os_name == 'posix':
        if 'darwin' in platform.system().lower():
            return 'macOS'
        else:
            return 'Linux'
    else:
        return 'Unknown'


def init_logger(logPath: str):
    # 日志输入文件
    # handler = logging.FileHandler(logPath, 'a', 'utf-8')
    folder_name = os.path.dirname(logPath)
    os.makedirs(folder_name, exist_ok=True)
    handler = TimedRotatingFileHandler(
        logPath, when='D', backupCount=7, encoding='utf-8')
    logging.basicConfig(handlers=[handler], level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(thread)d - %(message)s')
    logger = logging.getLogger(__name__)

    if get_os() != "Linux":
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(thread)d - %(message)s')
        streamHandler = logging.StreamHandler(sys.stdout)
        streamHandler.setFormatter(formatter)
        # logger.addHandler(handler)
        logger.addHandler(streamHandler)

    return logger


def get_all_channels():
    headers = {
        'host': '120.87.12.38:8083',
        'User-Agent': 'okhttp/3.10.0',
        'Content-Type': f'application/json'
    }
    response = requests.get(all_channels_url, headers=headers)
    all_channels_data = response.json()
    if not os.path.exists('sources'):
        os.mkdir('sources')
    with open('sources/all_channels_data.json', 'w', encoding='UTF-8') as f:
        json.dump(all_channels_data, f, ensure_ascii=False)

    if all_channels_data['status'] != '200' or 'channels' not in all_channels_data:
        logger.error('错误：无法获取频道列表或频道列表格式错误')
        sys.exit(1)

    # 提取频道代码
    channel_codes = [channel['params']['hwcode'] for channel in all_channels_data['channels']
                     if 'params' in channel and 'hwcode' in channel['params']]
    channel_codes_str = ','.join(channel_codes)

    channels_data = all_channels_data['channels']

    return channels_data, channel_codes_str


def get_access_token():
    # 获取访问令牌
    headers = {
        'User-Agent': 'okhttp/3.10.0',
        'Content-Type': f'application/json'
    }
    token_response = requests.get(authUrl, headers=headers)
    access_token = token_response.json().get('access_token')

    if not access_token:
        logger.error('错误：未能获取有效的 access token')
        sys.exit(1)

    return access_token


def get_channel_list(access_token: str, channel_codes_str: str):
    # 使用访问令牌请求数据
    headers = {
        'Authorization': access_token,
        'User-Agent': 'okhttp/3.10.0',
        'Connection': 'Keep-Alive',
        'Content-Type': 'application/json;charset=utf-8'
    }
    data = json.dumps({"channelcodes": channel_codes_str})
    # 请修改此处IP，确保与鉴权URL的IP一致
    response = requests.post(
        "http://120.87.11.25:33200/EPG/interEpg/channellist/batch", headers=headers, data=data)

    channel_list_response = response.json()

    if not channel_list_response:
        logger.error('错误：返回的数据为空')
        sys.exit(1)

    if not channel_list_response.get('channellist'):
        logger.error('错误：channellist 数据为空')
        sys.exit(1)
    if not os.path.exists('sources'):
        os.mkdir('sources')
    # 保存响应数据到文件
    with open('sources/channel_list_data.json', 'w', encoding='UTF-8') as f:
        json.dump(channel_list_response, f, ensure_ascii=False)

    return channel_list_response['channellist']


def get_local_list():
    sources = []
    url = 'https://mi.azzf.eu.org/iptv/guangdong.m3u8'
    response = requests.get(url)

    # 检查请求是否成功
    if response.status_code == 200:
        with open('guangdong.txt', 'wb') as file:
            file.write(response.content)
        logger.info("文件下载成功！")
    else:
        logger.error(f"下载失败，状态码：{response.status_code}")
        return sources

    # 逐行读取文件
    line_index: int = 0
    line_type = 0

    with open('guangdong.txt', 'r', encoding='utf-8') as file:
        source = {}
        for line in file:
            if line.strip() == "":
                continue
            line_index = line_index+1
            if line_index > 1:
                line_type = line_type+1
                if line_type == 1:
                    line = line.strip().removeprefix('#EXTINF:-1 ,')
                    source['name'] = line

                if line_type == 2:
                    line = line.strip()
                    source['url'] = line
                    line_type = 0
                    sources.append(source)
                    source = {}

    return sources


def build_channel_info(channel_list_data, all_channels_data):
    sources = []
    for item in channel_list_data:
        hwcode = item['channelcode']
        channel_info = next((ch for ch in all_channels_data if ch['params'].get(
            'hwcode') == hwcode), None)
        if not channel_info:
            continue

        channel_name = channel_info['title']
        timeshift_url = item['timeshifturl']
        sources.append({
            'name': channel_name,
            'url': timeshift_url
        })

    return sources


def build_channel_name(name):
    if name:
        # 删除特定文字
        name = name.replace("cctv", "CCTV")
        name = name.replace("中央", "CCTV")
        name = name.replace("央视", "CCTV")
        name = name.replace("高清", "")
        name = name.replace("超高", "")
        name = name.replace("超清", "")
        name = name.replace("HD", "")
        name = name.replace("标清", "")
        name = name.replace("频道", "")
        name = name.replace("-", "")
        name = name.replace(" ", "")
        name = name.replace("PLUS", "+")
        name = name.replace("＋", "+")
        name = name.replace("(", "")
        name = name.replace(")", "")
        name = name.replace("测试", "")
        name = re.sub(r"CCTV(\d+)台", r"CCTV\1", name)
        name = name.replace("CCTV1综合", "CCTV1")
        name = name.replace("CCTV2财经", "CCTV2")
        name = name.replace("CCTV3综艺", "CCTV3")
        name = name.replace("CCTV4国际", "CCTV4")
        name = name.replace("CCTV4中文国际", "CCTV4")
        name = name.replace("CCTV4欧洲", "CCTV4")
        name = name.replace("CCTV5体育", "CCTV5")
        name = name.replace("CCTV6电影", "CCTV6")
        name = name.replace("CCTV7军事", "CCTV7")
        name = name.replace("CCTV7军农", "CCTV7")
        name = name.replace("CCTV7农业", "CCTV7")
        name = name.replace("CCTV7国防军事", "CCTV7")
        name = name.replace("CCTV8电视剧", "CCTV8")
        name = name.replace("CCTV9记录", "CCTV9")
        name = name.replace("CCTV9纪录", "CCTV9")
        name = name.replace("CCTV10科教", "CCTV10")
        name = name.replace("CCTV11戏曲", "CCTV11")
        name = name.replace("CCTV12社会与法", "CCTV12")
        name = name.replace("CCTV13新闻", "CCTV13")
        name = name.replace("CCTV新闻", "CCTV13")
        name = name.replace("CCTV14少儿", "CCTV14")
        name = name.replace("CCTV15音乐", "CCTV15")
        name = name.replace("CCTV16奥林匹克", "CCTV16")
        name = name.replace("CCTV17农业农村", "CCTV17")
        name = name.replace("CCTV17农业", "CCTV17")
        name = name.replace("CCTV5+体育赛视", "CCTV5+")
        name = name.replace("CCTV5+体育赛事", "CCTV5+")
        name = name.replace("CCTV5+体育", "CCTV5+")
    return name


def build_channel_sources(channel_sources):
    source_types = {'全部': [], '央视频道': [], '卫视频道': [], '高清频道': [], '其他频道': []}

    if channel_sources and len(channel_sources) > 0:
        for channel_source in channel_sources:
            channel_source_copy = copy.deepcopy(channel_source)
            channel_source_copy['name'] = channel_source_copy['name'].replace(
                "(", "").replace(")", "").replace("测试", "")
            source_types['全部'].append(channel_source_copy)
            # channel_source['name'] = build_channel_name(channel_source['name'])
            if '高清' in channel_source['name']:
                source_types['高清频道'].append(channel_source)
            if ('CCTV' in channel_source['name'] or 'CGTN' in channel_source['name']):
                source_types['央视频道'].append(channel_source)
            elif '卫视' in channel_source['name']:
                source_types['卫视频道'].append(channel_source)
            else:
                source_types['其他频道'].append(channel_source)

    return source_types


def build_json_file(channel_name, dict_sources):  # 保存json数据
    if dict_sources is not None and len(dict_sources) > 0:
        have_channel = False
        for key, value in dict_sources.items():
            for item in value:
                have_channel = True
        if have_channel:
            if not os.path.exists('sources'):
                os.mkdir('sources')
            json_string = json.dumps(dict_sources, ensure_ascii=False)
            with open(f"sources/{channel_name}.json", "w", encoding='utf-8') as file:
                file.write(json_string)


def build_txt_file(channel_name, dict_sources):  # 保存txt数据
    if dict_sources is not None and len(dict_sources) > 0:
        txt_string = ''
        for key, value in dict_sources.items():
            txt_string += f'{key},#genre#\n'
            for item in value:
                txt_string += f"{item['name']},{item['url']}\n"
        if len(txt_string) > 0:
            if not os.path.exists('sources'):
                os.mkdir('sources')
            with open(f"sources/{channel_name}.txt", "w", encoding='utf-8') as file:
                file.write(txt_string)


def build_m3u8_file(channel_name, dict_sources):  # 保存m3u8数据
    if dict_sources is not None and len(dict_sources) > 0:
        m3u8_string = '#EXTM3U\n'
        have_channel = False
        for key, value in dict_sources.items():
            for item in value:
                have_channel = True
                m3u8_string += f"#EXTINF:-1 group-title=\"{key}\",{item['name']}\n{item['url']}\n"
        if have_channel:
            if not os.path.exists('sources'):
                os.mkdir('sources')
            with open(f"sources/{channel_name}.m3u8", "w", encoding='utf-8') as file:
                file.write(m3u8_string)


if __name__ == "__main__":
    province_code = 'guangdong'
    host_url = '120.87.11.25'
    config = None
    with open(config_path, 'r', encoding='utf-8') as file:
        config = json.load(file)
    if 'authUrl' in config:
        authUrl = str(config['authUrl'])

    logger = init_logger(config['logPath'])

    channels_data, channel_codes_str = get_all_channels()

    access_token = get_access_token()

    channels_list = get_channel_list(access_token, channel_codes_str)

    channels_sources = build_channel_info(channels_list, channels_data)

    local_sources = get_local_list()

    channels_sources.extend(local_sources)

    dict_sources = build_channel_sources(channels_sources)

    build_json_file(province_code, dict_sources)
    build_txt_file(province_code, dict_sources)
    build_m3u8_file(province_code, dict_sources)
