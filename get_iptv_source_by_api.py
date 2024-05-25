import os
import re
import sys
import json
import copy
import logging
import requests
import platform
from urllib import parse
from logging import Logger
from logging.handlers import TimedRotatingFileHandler

logger: Logger = None
config_path = os.environ.get('API_CONFIG_PATH')
appkey = os.environ.get('APP_KEY')


def test():
    key_word = '%2Fiptv%2Flive%2Fzh_cn.js%20%2Bcountry%3A%22CN%22%20%2Bsubdivisions%3A%22guangdong%22'

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
        'Referer': f'https://www.zoomeye.org/searchResult?q={key_word}',
        'Cookie': '__jsluid_s=6ecf48969682cfdc15275c2ca827f7ab; BMAP_SECKEY=1QgzU5ymsQghq3pY16JrA6aX-ai8gdjb_pOOVUXt9kbGcpQYs9QIRD1JxZhnUyVUJFpRfNAQRZqnOTXhE3MSMVBRSJ84nxXRu1VHspkCM0puf3pPg6UtnNPm2wF15HCMM6ZMD1FeEmJP-McY56lljtsmkdQbVUYcm4Z-mxj9DvM14j59qfplUBWs8dDdeblg; SECKEY_ABVK=j/VvC3OiYQfyy+dD4PSYtA9SUJkvsO7yLHbLphpYugU%3D'
    }

    response = requests.get(
        f'https://www.zoomeye.org/api/search?q={key_word}&page=1&pageSize=20&t=v4%2Bv6%2Bweb', headers=headers)

    json_string = response.text

    data = json.loads(json_string)

    matches = data['matches']

    # if matches is None or len(matches):

    iptv_urls = []

    for matche in matches:
        ip = matche['ip']
        port = matche['portinfo']['port']
        service = matche['portinfo']['service']
        iptv_urls.append(
            f'{service}://{ip}:{port}/iptv/live/1000.json?key=txiptv')

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }

    sources = []

    for iptv_url in iptv_urls[:3]:
        try:
            response = requests.get(iptv_url, headers=headers, timeout=6)
            iptv_json_string = response.text
            iptv_datas = json.loads(iptv_json_string)
            print(f'{iptv_url}')
            for iptv_data in iptv_datas['data']:
                iptv_data['url'] = f"{iptv_url.replace('/iptv/live/1000.json?key=txiptv','')}{iptv_data['url']}"
                sources.extend(iptv_datas['data'])

        except:
            continue

    new_sources = []
    tmp_urls = []
    source_types = []

    for source in sources:
        if source['url'] not in tmp_urls:
            new_sources.append(source)
            tmp_urls.append(source['url'])
            source_type = {'type': source['type'],
                           'typename': source['typename']}
            if source_type not in source_types:
                source_types.append(source_type)

    source_types = sorted(source_types, key=lambda x: x['type'])

    grouped_items = {}

    for source_type in source_types:
        data_tmps = filter(lambda x: x['type'] ==
                           source_type['type'], new_sources)
        data_tmps = sorted(data_tmps, key=lambda x: x['chid'])
        grouped_items[source_type['type']] = data_tmps

    # 获取直播源名称
    path = 'apisources'
    channel_name = f'{path}/data'

    os.makedirs(path, exist_ok=True)

    sources = new_sources

    if sources is not None and len(sources) > 0:
        # 保存json数据
        json_string = json.dumps(sources, ensure_ascii=False)
        with open(f"{channel_name}.json", "w", encoding='utf-8') as file:
            file.write(json_string)

        # 保存txt数据
        txt_string = ''
        for source in sources:
            txt_string += f"{source['name']},{source['url']}\n"

        with open(f"{channel_name}.txt", "w", encoding='utf-8') as file:
            file.write(txt_string)

        # 保存m3u8数据
        m3u8_string = '#EXTM3U\n'
        for source in sources:
            m3u8_string += f"#EXTINF:-1 ,{source['name']}\n{source['url']}\n"

        with open(f"{channel_name}.m3u8", "w", encoding='utf-8') as file:
            file.write(m3u8_string)


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


def read_config(configPath: str):
    config = None
    with open(configPath, 'r', encoding='utf-8') as file:
        config = json.load(file)
    return config


def query_source_by_keyword(keyword: str):
    iptv_urls = []

    headers = {
        'Host': 'www.zoomeye.org',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:108.0) Gecko/20100101 Firefox/108.0',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
        'Accept-Encoding': 'gzip, deflate, br',
        # 'Cube-Authorization': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VybmFtZSI6ImIwNmRiZTIwNjBmMSIsImVtYWlsIjoiaGF1c3RoeUBnbWFpbC5jb20iLCJleHAiOjE3MTY3Mjg1NDcuMH0.EFVokZoo3XFmexgej9JBIB4uSkC0qnMyDj5OGlbJ-TE',
        'Connection': 'keep-alive',
        'Referer': f'https://www.zoomeye.org/searchResult?q={keyword}',
        'Cookie': '__jsluid_s=2dab5521061999688bbd2dff7d4bc624',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache'
    }

    response = requests.get(
        f'https://www.zoomeye.org/api/search?q={keyword}&page=1&pageSize=20&t=v4%2Bv6%2Bweb', headers=headers)

    json_string = response.text
    if json_string is None or len(json_string) <= 0:
        return iptv_urls

    data = json.loads(json_string)
    matches = data['matches']

    if matches is None or len(matches) <= 0:
        return iptv_urls

    for matche in matches:
        ip = matche['ip']
        port = matche['portinfo']['port']
        service = matche['portinfo']['service']
        iptv_urls.append(
            f'{service}://{ip}:{port}/iptv/live/1000.json?key=txiptv')

    return iptv_urls


def query_channel(url, province_name):
    sources = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    try:
        response = requests.get(url, headers=headers, timeout=6)
        json_string = response.text
        datas = json.loads(json_string)
        logger.info(f'{province_name}-{url}')
        for iptv_data in datas['data']:
            item_url = iptv_data['url']
            if item_url.startswith('rtp') or item_url.startswith('udp'):
                continue
            if item_url.startswith('http'):
                iptv_data['url'] = item_url
            else:
                iptv_data['url'] = f"{url.replace('/iptv/live/1000.json?key=txiptv','')}{iptv_data['url']}"
            sources.append(iptv_data)
    except Exception as ex:
        return sources
        # logger.error(f"{url}-出错-{ex}")
    return sources


def build_channel_sources(channel_sources):
    source_types = {'全部': [], '央视频道': [], '卫视频道': [], '高清频道': [], '其他频道': []}

    if channel_sources and len(channel_sources) > 0:
        for channel_source in channel_sources:
            channel_source_copy = copy.deepcopy(channel_source)
            channel_source_copy['name'] = channel_source_copy['name'].replace(
                "(", "").replace(")", "").replace("测试", "")
            source_types['全部'].append(channel_source_copy)
            channel_source['name'] = build_channel_name(
                channel_source['name'])
            if 'ishdchannel' in channel_source and channel_source['ishdchannel']:
                source_types['高清频道'].append(channel_source)
            if ('CCTV' in channel_source['name'] or 'CGTN' in channel_source['name']):
                source_types['央视频道'].append(channel_source)
            elif '卫视' in channel_source['name']:
                source_types['卫视频道'].append(channel_source)
            else:
                source_types['其他频道'].append(channel_source)

    return source_types


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


def build_json_file(channel_name, dict_sources, path: str):  # 保存json数据
    if dict_sources is not None and len(dict_sources) > 0:
        have_channel = False
        for key, value in dict_sources.items():
            for item in value:
                have_channel = True
        if have_channel:
            json_string = json.dumps(dict_sources, ensure_ascii=False)
            with open(f"{path}/{channel_name}.json", "w", encoding='utf-8') as file:
                file.write(json_string)


def build_txt_file(channel_name, dict_sources, path: str):  # 保存txt数据
    if dict_sources is not None and len(dict_sources) > 0:
        txt_string = ''
        for key, value in dict_sources.items():
            txt_string += f'{key},#genre#\n'
            for item in value:
                txt_string += f"{item['name']},{item['url']}\n"
        if len(txt_string) > 0:
            with open(f"{path}/{channel_name}.txt", "w", encoding='utf-8') as file:
                file.write(txt_string)


def build_m3u8_file(channel_name, dict_sources, path: str):  # 保存m3u8数据
    if dict_sources is not None and len(dict_sources) > 0:
        m3u8_string = '#EXTM3U\n'
        have_channel = False
        for key, value in dict_sources.items():
            for item in value:
                have_channel = True
                m3u8_string += f"#EXTINF:-1 group-title=\"{key}\",{item['name']}\n{item['url']}\n"
        if have_channel:
            with open(f"{path}/{channel_name}.m3u8", "w", encoding='utf-8') as file:
                file.write(m3u8_string)


def get_channel_sources_by_province(keyword, province, path):
    sources = []
    province_name = province['province_name']
    province_code = province['province_code']
    query_code = parse.quote(province_name)
    keyword = keyword.replace('guangdong', query_code)

    urls = query_source_by_keyword(keyword)

    if urls is None or len(urls) <= 0:
        return sources

    for url in urls:
        channel_items = query_channel(url, province_name)
        if channel_items is not None and len(channel_items) > 0:
            sources.extend(channel_items)

    if sources is not None and len(sources) > 0:
        dict_sources = build_channel_sources(sources)
        build_json_file(province_code, dict_sources, path)
        build_txt_file(province_code, dict_sources, path)
        build_m3u8_file(province_code, dict_sources, path)


if __name__ == "__main__":
    path = 'apisources'
    province_code = 'guangdong'

    config = read_config(config_path)
    if config is None or 'logPath' not in config:
        exit(0)

    logger = init_logger(config['logPath'])

    if 'path' in config and len(config['path']) > 0:
        path = str(config['path'])

    key_word = '%2Fiptv%2Flive%2Fzh_cn.js%20%2Bcountry%3A%22CN%22%20%2Bsubdivisions%3A%22guangdong%22'
    if 'keyword' in config and len(config['keyword']) > 0:
        key_word = config['keyword']
    province_map = read_config('config/province_map.json')
    province_dict: dict[str, str] = {}
    province_dict["province_name"] = '湖南'
    province_dict["province_code"] = f'{"hunan".lower()}_iptv'
    get_channel_sources_by_province(key_word, province_dict, path)
    exit(0)
    for key, value in province_map.items():
        province_dict: dict[str, str] = {}
        province_dict["province_name"] = key
        province_dict["province_code"] = f'{value.lower()}_iptv'
        get_channel_sources_by_province(key_word, province_dict, path)
