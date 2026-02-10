from logging.handlers import TimedRotatingFileHandler
from logging import Logger
from urllib.parse import urlparse, urlunparse
import json
import requests
import re
import os
import sys
import logging
import platform
import subprocess
import concurrent.futures


logger: Logger = None
config_path = os.environ.get('CONFIG_PATH')
authUrl: str = None
host_url: str = '120.87.11.25:33200'
all_channels_url: str = 'http://120.87.12.38:8083/epg/api/custom/getAllChannel.json'
channelIndex_url: str = 'http://120.87.12.38:8083/epg/api/custom/channelIndex.json'
is_check_url_available = bool(False)
timeout: int = int(5)
isTestSpeed = bool(False)
onlyHd = bool(False)
localUrl: str = None
forver_auth_info: str = None

headers = {
    'host': '120.87.12.38:8083',
    'User-Agent': 'okhttp/3.10.0',
    'Content-Type': f'application/json'
}


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


def get_channelIndex(useRemote: bool = False):
    file_path = 'sources/channelIndex.json'
    channel_index_data = None
    target_item_list = []
    all_channel_list = []
    all_channel_params = []

    if useRemote:
        response = requests.get(channelIndex_url, headers=headers)
        channel_index_data = response.json()
        if not os.path.exists('sources'):
            os.mkdir('sources')
        with open(file_path, 'w', encoding='UTF-8') as f:
            json.dump(channel_index_data, f, ensure_ascii=False)

    with open(file_path, "r", encoding="utf-8") as f:
        channel_index_data = json.load(f)

    if channel_index_data is not None:
        area_datas_list = channel_index_data.get("areaDatas", [])
        target_obj_list = [
            item for item in area_datas_list if item.get("areaCode") == "1"]
        if target_obj_list is not None and len(target_obj_list) > 0:
            for obj in target_obj_list:
                target_item_list.extend(obj.get("items", []))

    # 遍历处理频道分类
    for target_item in target_item_list:
        biz_items = []
        biz_path = target_item.get("dataLink", None)
        biz_item_code = target_item.get("itemCode", None)
        biz_item_title = target_item.get("itemTitle", None)
        channel_list = {
            "channel_type_title": biz_item_title,
            "channel_type_url": biz_path,
            "channel_type_code": biz_item_code,
            "channel_list": [],
        }
        if biz_path is None:
            continue
        biz_data = None
        response = requests.get(url=biz_path, headers=headers, timeout=10)
        if response.status_code == 200:
            biz_data = response.json()
            # with open(f'sources/{biz_item_code}.json', 'w', encoding='UTF-8') as f:
            #     json.dump(biz_data, f, ensure_ascii=False)

        if biz_data is not None:
            for obj in biz_data.get("areaDatas", []):
                biz_items.extend(obj.get("items", []))
            # logger.info(
            #     f'{biz_item_code}_items-{json.dumps(biz_items, ensure_ascii=False)}')

        # 处理分类下频道
        for item in biz_items:
            dataLink = item.get('dataLink', None)
            itemCode = item.get('itemCode', None)
            itemTitle = item.get('itemTitle', None)

            target_item = [
                item for item in all_channel_params if item.get("itemId") == itemCode]

            if target_item and len(target_item) > 0:
                channel_list["channel_list"].append(target_item[0])
                continue

            response = requests.get(
                url=dataLink, headers=headers, timeout=10)
            if response.status_code == 200:
                res_json = response.json()
                hwcode = res_json.get("channel", {}).get(
                    "params", {}).get("hwcode")
                if hwcode:
                    channel_item = {
                        "itemId": itemCode,
                        "itemTitle": itemTitle,
                        "dataLink": dataLink,
                        "hwcode": hwcode
                    }
                    all_channel_params.append(channel_item)
                    channel_list["channel_list"].append(channel_item)

        # with open(f'sources/{biz_item_code}_hwcode.json', 'w', encoding='UTF-8') as f:
        #     json.dump(channel_list, f, ensure_ascii=False)
        # logger.info(
        #     f'hwcode_list-{json.dumps(channel_list, ensure_ascii=False)}')

        all_channel_list.append(channel_list)

    with open(f'sources/all_channel_list.json', 'w', encoding='UTF-8') as f:
        json.dump(all_channel_list, f, ensure_ascii=False)

    # 提取频道代码
    channel_codes = [item.get(
        "hwcode") for obj in all_channel_list for item in obj.get("channel_list", [])]

    # 去重
    channel_codes = list(set(channel_codes))

    return channel_codes, all_channel_list


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


def get_channel_list(access_token: str, channel_codes: list):
    # 使用访问令牌请求数据
    headers = {
        'Authorization': access_token,
        'User-Agent': 'okhttp/3.10.0',
        'Connection': 'Keep-Alive',
        'Content-Type': 'application/json;charset=utf-8'
    }

    batch_size = 50
    channel_list = []
    for i in range(0, len(channel_codes), batch_size):
        batch = channel_codes[i:i+batch_size]
        channel_codes_str = ','.join(batch)
        data = json.dumps({"channelcodes": channel_codes_str})
        # 请修改此处IP，确保与鉴权URL的IP一致
        response = requests.post(
            "http://120.87.11.25:33200/EPG/interEpg/channellist/batch", headers=headers, data=data)
        if response.status_code == 200:
            channel_list_response = response.json()

            if channel_list_response and channel_list_response.get('channellist'):
                channel_list.extend(channel_list_response['channellist'])

    if not os.path.exists('sources'):
        os.mkdir('sources')
    # 保存响应数据到文件
    with open('sources/channel_list_data.json', 'w', encoding='UTF-8') as f:
        json.dump(channel_list, f, ensure_ascii=False)

    return channel_list


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


def build_channel_info(channel_url_list, all_channels_data):
    for channel_data in all_channels_data:
        channel_list = channel_data.get('channel_list', [])
        for channel in channel_list:
            code = channel.get('hwcode', None)
            itemTitle = channel.get('itemTitle', None)
            if code:
                channel_url = [item for item in channel_url_list if item.get(
                    "channelcode") == code]
                if channel_url and len(channel_url) > 0:
                    channel['url'] = build_forver_url_auth(
                        channel_url[0]['timeshifturl'])
                    channel['logo'] = build_channel_logo_name(itemTitle)
                    channel['tvg-name'] = build_channel_name(itemTitle)

    return all_channels_data


def build_forver_url_auth(url: str):
    if forver_auth_info is not None and len(forver_auth_info) <= 0:
        return url

    parsed = urlparse(url)
    path_parts = parsed.path.strip('/').split('/')
    if path_parts:
        path_parts = path_parts[:-1]

    new_parsed = urlparse(forver_auth_info)
    new_path_parts = new_parsed.path.strip('/').split('/')
    if new_path_parts:
        path_parts.extend(new_path_parts)

    new_path = '/' + '/'.join(path_parts)

    new_parsed = parsed._replace(path=new_path, query=new_parsed.query)

    new_url = urlunparse(new_parsed)

    return new_url


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
            name = "CCTV-1"

        if "CCTV-2&" in name or "CCTV2&" in name:
            name = "CCTV-2"

        if "CCTV-3&" in name or "CCTV3&" in name:
            name = "CCTV-3"

        if "CCTV-4&" in name or "CCTV4&" in name:
            name = "CCTV-4"

        if ("CCTV-5&" in name or "CCTV5&" in name) and not ("CCTV-5&+" in name or "CCTV5&+" in name):
            name = "CCTV-5"

        elif ("CCTV-5&+" in name or "CCTV5&+" in name):
            name = "CCTV-5+"

        if "CCTV-6&" in name or "CCTV6&" in name:
            name = "CCTV-6"

        if "CCTV-7&" in name or "CCTV7&" in name:
            name = "CCTV-7"

        if "CCTV-8&" in name or "CCTV8&" in name:
            name = "CCTV-8"
        if "CCTV-9&" in name or "CCTV9&" in name:
            name = "CCTV-9 "

        if "CCTV-10&" in name or "CCTV10&" in name:
            name = "CCTV-10"

        if "CCTV-11&" in name or "CCTV11&" in name:
            name = "CCTV-11"

        if "CCTV-12&" in name or "CCTV12&" in name:
            name = "CCTV-12"

        if "CCTV-13&" in name or "CCTV13&" in name:
            name = "CCTV-13"

        if "CCTV-14&" in name or "CCTV14&" in name:
            name = "CCTV-14"

        if "CCTV-15&" in name or "CCTV15&" in name:
            name = "CCTV-15"

        if "CCTV-16&" in name or "CCTV16&" in name:
            name = "CCTV-16 "

        if "CCTV-17&" in name or "CCTV17&" in name:
            name = "CCTV-17"

        name = name.replace('&', '').upper()

        if '东南卫视' in name:
            name = '东南卫视'

        if '广东4K' in name:
            name = '广东卫视'
        if '4K' in name:
            name = name.split('4K')[0]

        name = name.replace("高清", "")

    return name


def build_channel_logo_name(name: str):
    if name:
        # 删除特定文字
        if name == 'CCTV-4中文国际':
            t = 1
        name = name.replace("cctv", "CCTV")
        name = name.replace("中央", "CCTV")
        name = name.replace("央视", "CCTV")
        name = name.replace("测试", "")
        name = name.replace("超高清", "")
        name = name.replace("超高", "")
        name = name.replace("超清", "")
        name = name.replace("HD", "")
        name = name.replace("高清", "")
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
        name = name.replace("CCTV4中文国际", "CCTV4")
        name = re.sub(r'\d+', lambda x: x.group() + '&', name)
        name = name.replace("CCTV1综合", "CCTV1&")
        name = name.replace("CCTV2财经", "CCTV2&")
        name = name.replace("CCTV3综艺", "CCTV3&")
        name = name.replace("CCTV4国际", "CCTV4&")
        name = name.replace("CCTV4中文国际", "CCTV4&")
        name = name.replace("CCTV4高清", "CCTV4&")
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
            name = "CCTV1"

        if "CCTV-2&" in name or "CCTV2&" in name:
            name = "CCTV2"

        if "CCTV-3&" in name or "CCTV3&" in name:
            name = "CCTV3"

        if "CCTV-4&" in name or "CCTV4&" in name:
            iname = "CCTV4"

        if ("CCTV-5&" in name or "CCTV5&" in name) and not ("CCTV-5&+" in name or "CCTV5&+" in name):
            name = "CCTV5"
        elif ("CCTV-5&+" in name or "CCTV5&+" in name):
            name = "CCTV5+"

        if "CCTV-6&" in name or "CCTV6&" in name:
            name = "CCTV6"

        if "CCTV-7&" in name or "CCTV7&" in name:
            name = "CCTV7"

        if "CCTV-8&" in name or "CCTV8&" in name:
            name = "CCTV8"

        if "CCTV-9&" in name or "CCTV9&" in name:
            name = "CCTV8"

        if "CCTV-10&" in name or "CCTV10&" in name:
            name = "CCTV10"

        if "CCTV-11&" in name or "CCTV11&" in name:
            name = "CCTV11"

        if "CCTV-12&" in name or "CCTV12&" in name:
            name = "CCTV12"

        if "CCTV-13&" in name or "CCTV13&" in name:
            name = "CCTV13"

        if "CCTV-14&" in name or "CCTV14&" in name:
            name = "CCTV14"

        if "CCTV-15&" in name or "CCTV15&" in name:
            name = "CCTV15"

        if "CCTV-16&" in name or "CCTV16&" in name:
            name = "CCTV16"

        if "CCTV-17&" in name or "CCTV17&" in name:
            name = "CCTV17"

        name = name.replace('&', '').upper()

        if '东南卫视' in name:
            name = '东南卫视'

        if '广东4K' in name:
            name = '广东卫视'
        if '4K' in name:
            name = name.split('4K')[0]

    return name


def build_json_file(channel_name, dict_sources):  # 保存json数据
    if dict_sources is not None and len(dict_sources) > 0:
        if not os.path.exists('sources'):
            os.mkdir('sources')
        json_string = json.dumps(dict_sources, ensure_ascii=False)
        with open(f"sources/{channel_name}.json", "w", encoding='utf-8') as file:
            file.write(json_string)


def build_txt_file(channel_name, dict_sources):  # 保存txt数据
    if dict_sources is not None and len(dict_sources) > 0:
        txt_string = ''
        for dict_source in dict_sources:
            key = dict_source.get('channel_type_title', '')
            value = dict_source.get('channel_list', '')
            txt_string += f'{key},#genre#\n'
            for item in value:
                if item.get('url', None):
                    have_channel = True
                    txt_string += f"{item['itemTitle']},{item['url']}\n"
        if have_channel:
            if not os.path.exists('sources'):
                os.mkdir('sources')
            with open(f"sources/{channel_name}.txt", "w", encoding='utf-8') as file:
                file.write(txt_string)


def build_m3u8_file(channel_name, dict_sources):  # 保存m3u8数据
    if dict_sources is not None and len(dict_sources) > 0:
        m3u8_string = '#EXTM3U x-tvg-url="https://epg.zsdc.eu.org/t.xml.gz" catchup="append" catchup-source="?playseek=${(b)yyyyMMddHHmmss}-${(e)yyyyMMddHHmmss}"\n'
        have_channel = False
        for dict_source in dict_sources:
            key = dict_source.get('channel_type_title', '')
            value = dict_source.get('channel_list', '')
            for item in value:
                if item.get('url', None):
                    have_channel = True
                    m3u8_string += f'#EXTINF:-1 tvg-id="{item["itemId"]}" tvg-name="{item["tvg-name"]}" tvg-logo="https://gh-proxy.org/https://github.com/fanmingming/live/blob/main/tv/{item["logo"]}.png" group-title="{key}",{item["itemTitle"]}\n{item["url"]}\n'
        if have_channel:
            if not os.path.exists('sources'):
                os.mkdir('sources')
            with open(f"sources/{channel_name}.m3u", "w", encoding='utf-8') as file:
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


def check_source_ishd_by_name(channel_sources):
    for channel_source in channel_sources:
        name = channel_source['name']
        channel_source['is_hd'] = False
        if '4K' in name or '超高清' in name or '超清' in name or '高清' in name:
            channel_source['is_hd'] = True


def check_sources_ishd(channel_sources):
    if not channels_sources or len(channels_sources) <= 0:
        return channels_sources
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        tasks = []
        for channel_source in channel_sources:
            if not channel_source['is_hd']:
                future = executor.submit(check_source_ishd, channel_source)
                tasks.append(future)
        for future in concurrent.futures.as_completed(tasks):
            result = future.result()


def check_source_ishd(channel_source):
    if not channel_source or len(channel_source) <= 0:
        return channel_source
    url = channel_source['url']
    width, height = get_video_resolution(url)
    isHd = False
    if width and height and int(height) >= 1080:
        isHd = True

    channel_source['is_hd'] = isHd
    channel_source['resolution'] = f'{width}x{height}'

    logger.info(
        f"{channel_source['name']}-{channel_source['is_hd']}-{channel_source['resolution']}")

    return channel_source


def get_video_resolution(url: str, headers: dict = None) -> str | None:
    """
    Get the resolution of the url by ffprobe
    """
    width = None
    height = None
    try:
        probe_args = [
            'ffprobe',
            '-v', 'error',
            '-headers', ''.join(f'{k}: {v}\r\n' for k,
                                v in headers.items()) if headers else '',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height',
            "-of", 'json',
            url
        ]
        result = subprocess.run(
            probe_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        if result.returncode != 0:
            print("Error:", result.stderr.decode())
            return None

        info = json.loads(result.stdout)
        width = info['streams'][0]['width']
        height = info['streams'][0]['height']

    except Exception as ex:
        print(f'出错-{ex}')

    return width, height


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
    if 'forver_auth_info' in config:
        forver_auth_info = str(config['forver_auth_info'])

    logger = init_logger(config['logPath'])

    channel_codes, all_channel_list = get_channelIndex(True)

    access_token = get_access_token()

    channels_list = get_channel_list(access_token, channel_codes)

    channels_sources = build_channel_info(channels_list, all_channel_list)

    # local_sources = get_local_list()

    # channels_sources.extend(local_sources)

    # check_source_ishd_by_name(channels_sources)
    # check_sources_ishd(channels_sources)

    # dict_sources = build_channel_sources(channels_sources)

    build_json_file(province_code, channels_sources)
    build_txt_file(province_code, channels_sources)
    build_m3u8_file(province_code, channels_sources)
