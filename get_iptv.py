from logging.handlers import TimedRotatingFileHandler
from logging import Logger
from requests import Response
from urllib.parse import urlparse, parse_qs
from urllib import parse
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
is_check_url_available = bool(False)
timeout: int = int(5)
isTestSpeed = bool(False)
onlyHd = bool(False)
localUrl: str = None


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
    if localUrl is None or len(localUrl) == 0:
        return sources

    url = localUrl
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
                    source['name'] = line.replace(" ", "")

                if line_type == 2:
                    line = line.strip()
                    source['url'] = line
                    line_type = 0
                    sources.append(source)
                    source = {}
    if onlyHd:
        sources = [item for item in sources if '高清' in item['name']]

    return sources


def get_double_list():
    sources = []
    url = 'http://iptv.shabb.cn/Sub?type=m3u'
    response = requests.get(url)

    # 检查请求是否成功
    if response.status_code == 200:
        with open('double.txt', 'wb') as file:
            file.write(response.content)
        logger.info("double-文件下载成功！")
    else:
        logger.error(f"double-下载失败，状态码：{response.status_code}")
        return sources

    # 逐行读取文件
    line_index: int = 0
    line_type = 0

    with open('double.txt', 'r', encoding='utf-8') as file:
        source = {}
        for line in file:
            if line.strip() == "":
                continue
            line_index = line_index+1
            if line_index > 1:
                line_type = line_type+1
                if line_type == 1:
                    line = line.strip().removeprefix('#EXTINF:-1 ,')
                    source['name'] = line.replace(" ", "")

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
            'name': channel_name.replace(" ", ""),
            'url': timeshift_url
        })
    if onlyHd:
        sources = [item for item in sources if '高清' in item['name']]

    return sources


def build_channel_name(name):
    if name:
        # 删除特定文字
        name = name.replace("cctv", "CCTV")
        name = name.replace("中央", "CCTV")
        name = name.replace("央视", "CCTV")
        name = name.replace("测试", "")
        name = name.replace("超高", "高清")
        name = name.replace("超清", "高清")
        name = name.replace("HD", "高清")
        name = name.replace("标清", "")
        name = name.replace("频道", "")
        name = name.replace("-", "")
        name = name.replace(" ", "")
        name = name.replace("PLUS", "+")
        name = name.replace("＋", "+")
        name = name.replace("(", "")
        name = name.replace(")", "")
        name = name.replace("测试", "")
        name = re.sub(r"CCTV(\d+)台", r"CCTV\1&", name)
        name = re.sub(r'\d+', lambda x: x.group() + '&', name)
        name = name.replace("CCTV1综合", "CCTV1&")
        name = name.replace("CCTV2财经", "CCTV2&")
        name = name.replace("CCTV3综艺", "CCTV3&")
        name = name.replace("CCTV4国际", "CCTV4&")
        name = name.replace("CCTV4中文国际", "CCTV4&")
        name = name.replace("CCTV4欧洲", "CCTV4&")
        name = name.replace("CCTV5体育", "CCTV5&")
        name = name.replace("CCTV6电影", "CCTV6&")
        name = name.replace("CCTV7军事", "CCTV7&")
        name = name.replace("CCTV7军农", "CCTV7&")
        name = name.replace("CCTV7农业", "CCTV7&")
        name = name.replace("CCTV7国防军事", "CCTV7&")
        name = name.replace("CCTV8电视剧", "CCTV8&")
        name = name.replace("CCTV9记录", "CCTV9&")
        name = name.replace("CCTV9纪录", "CCTV9&")
        name = name.replace("CCTV10科教", "CCTV10&")
        name = name.replace("CCTV11戏曲", "CCTV11&")
        name = name.replace("CCTV12社会与法", "CCTV12&")
        name = name.replace("CCTV13新闻", "CCTV13&")
        name = name.replace("CCTV新闻", "CCTV13&")
        name = name.replace("CCTV14少儿", "CCTV14&")
        name = name.replace("CCTV15音乐", "CCTV15&")
        name = name.replace("CCTV16奥林匹克", "CCTV16&")
        name = name.replace("CCTV17农业农村", "CCTV17&")
        name = name.replace("CCTV17农业", "CCTV17&")
        name = name.replace("CCTV5+体育赛视", "CCTV5+&")
        name = name.replace("CCTV5+体育赛事", "CCTV5+&")
        name = name.replace("CCTV5+体育", "CCTV5+&")
        if "CCTV-1&" in name or "CCTV1&" in name:
            if "高清" in name:
                name = "CCTV-1 综合 高清"
            else:
                name = "CCTV-1 综合"

        if "CCTV-2&" in name or "CCTV2&" in name:
            if "高清" in name:
                name = "CCTV-2 财经 高清"
            else:
                name = "CCTV-2 财经"

        if "CCTV-3&" in name or "CCTV3&" in name:
            if "高清" in name:
                name = "CCTV-3 综艺 高清"
            else:
                name = "CCTV-3 综艺"

        if "CCTV-4&" in name or "CCTV4&" in name:
            if "高清" in name:
                name = "CCTV-4 中文国际 高清"
            else:
                name = "CCTV-4 中文国际"

        if ("CCTV-5&" in name or "CCTV5&" in name) and not ("CCTV-5&+" in name or "CCTV5&+" in name):
            if "高清" in name:
                name = "CCTV-5 体育 高清"
            else:
                name = "CCTV-5 体育"
        elif ("CCTV-5&+" in name or "CCTV5&+" in name):
            if "高清" in name:
                name = "CCTV-5+ 体育赛事 高清"
            else:
                name = "CCTV-5+ 体育赛事"

        if "CCTV-6&" in name or "CCTV6&" in name:
            if "高清" in name:
                name = "CCTV-6 电影 高清"
            else:
                name = "CCTV-6 电影"

        if "CCTV-7&" in name or "CCTV7&" in name:
            if "高清" in name:
                name = "CCTV-7 军事农业 高清"
            else:
                name = "CCTV-7 军事农业"

        if "CCTV-8&" in name or "CCTV8&" in name:
            if "高清" in name:
                name = "CCTV-8 电视剧 高清"
            else:
                name = "CCTV-8 电视剧"

        if "CCTV-9&" in name or "CCTV9&" in name:
            if "高清" in name:
                name = "CCTV-9 纪录 高清"
            else:
                name = "CCTV-9 纪录"

        if "CCTV-10&" in name or "CCTV10&" in name:
            if "高清" in name:
                name = "CCTV-10 科教 高清"
            else:
                name = "CCTV-10 科教"

        if "CCTV-11&" in name or "CCTV11&" in name:
            if "高清" in name:
                name = "CCTV-11 戏曲 高清"
            else:
                name = "CCTV-11 戏曲"

        if "CCTV-12&" in name or "CCTV12&" in name:
            if "高清" in name:
                name = "CCTV-12 社会与法 高清"
            else:
                name = "CCTV-12 社会与法"

        if "CCTV-13&" in name or "CCTV13&" in name:
            if "高清" in name:
                name = "CCTV-13 新闻 高清"
            else:
                name = "CCTV-13 新闻"

        if "CCTV-14&" in name or "CCTV14&" in name:
            if "高清" in name:
                name = "CCTV-14 少儿 高清"
            else:
                name = "CCTV-14 少儿"

        if "CCTV-15&" in name or "CCTV15&" in name:
            if "高清" in name:
                name = "CCTV-15 音乐 高清"
            else:
                name = "CCTV-15 音乐"

        if "CCTV-16&" in name or "CCTV16&" in name:
            if "高清" in name:
                name = "CCTV-16 奥林匹克 高清"
            else:
                name = "CCTV-16 奥林匹克"

        if "CCTV-17&" in name or "CCTV17&" in name:
            if "高清" in name:
                name = "CCTV-17 农业农村 高清"
            else:
                name = "CCTV-17 农业农村"
    return name


def build_channel_name_hd(name):
    name = re.sub(r'高清', '', name)
    name = re.findall(r'(CCTV\d+\+)', name)
    return name


def build_channel_sources(channel_sources):
    # new_key_value = {'a': 1}
    # original_dict = {**new_key_value, **original_dict}
    source_types = {
        '央视频道': [],
        '卫视频道': [],
        '高清频道': [],
        '其他频道': []}
    if onlyHd:
        source_types = {
            '央视频道': [],
            '卫视频道': [],
            '其他频道': []}

    if channel_sources and len(channel_sources) > 0:
        for channel_source in channel_sources:
            if onlyHd:
                channel_source['name'] = build_channel_name_hd(
                    channel_source['name'])
            else:
                channel_source['name'] = build_channel_name(
                    channel_source['name'])
            # channel_source_copy = copy.deepcopy(channel_source)
            # source_types['全部'].append(channel_source_copy)

            if '高清' in channel_source['name'] and not onlyHd:
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


def check_url_available(source_name, sources):
    if not is_check_url_available:
        return sources

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36'}
    se = requests.Session()
    available_sources = []
    timeout_host: dict[str, int] = {}
    for i in sources:
        try:
            parsed_url = urlparse(i['url'])
            netloc = parsed_url.netloc
            if netloc in timeout_host.keys() and timeout_host[netloc] > 10:
                continue
            res = se.get(i['url'], headers=headers,
                         timeout=timeout, stream=True)
            if res.status_code == 200:
                if isTestSpeed:
                    for content in res.iter_content(chunk_size=1*1024*1024):
                        if content and len(content) > 0:
                            if netloc in timeout_host.keys():
                                del timeout_host[netloc]

                            logger.info(
                                f"{source_name}-可用-{i['name']}-{i['url']}")
                            available_sources.append(i)
                        else:
                            logger.info(
                                f"{source_name}-不可用-{i['name']}-{i['url']}")
                        break
                else:
                    if netloc in timeout_host.keys():
                        del timeout_host[netloc]

                    logger.info(
                        f"{source_name}-可用-{i['name']}-{i['url']}")
                    available_sources.append(i)
            else:
                logger.info(
                    f"{source_name}-不可用-{i['name']}-{i['url']}")
        except requests.exceptions.Timeout:
            if netloc in timeout_host.keys():
                timeout_host[netloc] += 1
            else:
                timeout_host[netloc] = 1
            logger.error(
                f"{source_name}-{i['name']}-{i['url']}-请求超时，超时时间设置为{timeout}秒")
        except requests.exceptions.RequestException as ex:
            logger.error(
                f"{source_name}-出错-{i['name']}-{i['url']}{ex}")
        except Exception as ex:
            logger.error(
                f"{source_name}-出错-{i['name']}-{i['url']}{ex}")
    return available_sources


if __name__ == "__main__":
    province_code = 'guangdong'
    host_url = '120.87.11.25'
    config = None
    onlyHd = False
    with open(config_path, 'r', encoding='utf-8') as file:
        config = json.load(file)
    if 'authUrl' in config:
        authUrl = str(config['authUrl'])
    if 'timeout' in config:
        timeout = int(config['timeout'])
    if 'isCheckUrlAvailable' in config:
        is_check_url_available = bool(config['isCheckUrlAvailable'])
    if 'isTestSpeed' in config:
        isTestSpeed = bool(config['isTestSpeed'])
    if 'onlyHd' in config:
        onlyHd = bool(config['onlyHd'])
    if 'localUrl' in config:
        localUrl = str(config['localUrl'])

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
