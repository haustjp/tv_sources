from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
from urllib import parse
from logging.handlers import TimedRotatingFileHandler
from logging import Logger
from typing import Union, List
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
is_check_url_available = bool(False)
isTestSpeed = bool(False)
timeout: int = int(5)
hdkeyword = ['高清', '超清', 'hd', '4k']


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


def get_numbers(text):
    pattern = re.compile(r'\d+')
    match = pattern.search(text)
    if match:
        number = match.group()
        return int(number)
    else:
        return 0


def query_by_province(province, prev_url=None, page=None, code=None):
    query_result = {}
    headers = {}
    response: Response = None
    curr_url = 'http://tonkiang.us/hoteliptv.php'
    if page is None:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
            'Referer': f'http://tonkiang.us/hoteliptv.php',
            'Cookie': 'REFERER=15239974; ckip1=110.72.82.168%7C110.72.81.102%7C113.118.47.23%7C14.155.189.170%7C112.114.137.112%7C61.134.241.142%7C61.138.128.226%7C113.64.145.231; ckip2=183.153.89.133%7C218.88.103.176%7C58.48.199.92%7C222.141.135.44%7C171.109.211.31%7C118.79.112.201%7C118.113.235.79%7C223.10.39.217; _ga=GA1.1.1545478787.1715258144; HstCfa4853344=1715258161531; HstCmu4853344=1715258161531; HstCnv4853344=1; HstCns4853344=1; REFERER2=NzDbAr2aNbjcIO0O0O; REFERER1=MzjbMryaNbTcUO0O0O; HstCla4853344=1715258167679; HstPn4853344=2; HstPt4853344=2; _ga_JNMLRB3QLF=GS1.1.1715258144.1.1.1715258176.0.0.0',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {'saerch': province, 'Submit': None}
        response = requests.post(curr_url, data=data, headers=headers)
    else:
        curr_url = f'http://tonkiang.us/hoteliptv.php?page={page}&pv={parse.quote(province)}&code={code}'
        referer = 'http://tonkiang.us/hoteliptv.php'
        if prev_url is not None:
            referer = prev_url

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
            'Referer': referer,
            'Cookie': 'REFERER=15239974; ckip1=110.72.82.168%7C110.72.81.102%7C113.118.47.23%7C14.155.189.170%7C112.114.137.112%7C61.134.241.142%7C61.138.128.226%7C113.64.145.231; ckip2=183.153.89.133%7C218.88.103.176%7C58.48.199.92%7C222.141.135.44%7C171.109.211.31%7C118.79.112.201%7C118.113.235.79%7C223.10.39.217; _ga=GA1.1.1545478787.1715258144; HstCfa4853344=1715258161531; HstCmu4853344=1715258161531; HstCnv4853344=1; HstCns4853344=1; REFERER2=NzDbAr2aNbjcIO0O0O; REFERER1=MzjbMryaNbTcUO0O0O; HstCla4853344=1715258167679; HstPn4853344=2; HstPt4853344=2; _ga_JNMLRB3QLF=GS1.1.1715258144.1.1.1715258176.0.0.0'
        }

        response = requests.get(curr_url, headers=headers)

    html = response.text
    if html is None or len(html) == 0:
        return query_result
    bs = BeautifulSoup(html, 'html.parser')
    pagers = bs.select('a[href^="?page="]')

    if pagers and len(pagers) > 0:
        href = pagers[0].attrs['href']
        parsed_url = urlparse(href)
        query_params = parse_qs(parsed_url.query)
        code = query_params['code'][0]
        query_result['url'] = href
        query_result['code'] = code

    tables = bs.select('div[class="tables"]')
    logger.info(f'{province}_tables长度：{len(tables)}')
    sources = []

    for table in tables:
        results = table.select('div[class="result"]')
        for result in results:
            channel = result.find('div', class_='channel')
            if channel:
                ip_port = channel.b.text.strip()
                active_tag = result.find('div', style='float: right; ')
                active_text = active_tag.text.replace("\n", "").strip()
                number_tag = result.find('div', style='float: left').b
                number_tag_text = number_tag.text.replace("\n", "").strip()
                if active_text != '暂时失效':
                    active_day = get_numbers(active_text)
                    channel_number = get_numbers(number_tag_text)
                    logger.info(
                        f'{province}-status：{active_text},channel：{ip_port},num：{channel_number}')
                    sources.append(
                        {'ip_port': ip_port, 'active_day': active_day, 'channel_number': channel_number})

    query_result['sources'] = sources
    query_result['prev_url'] = curr_url
    # logger.info(
    #     f'{province}可用直播组:{json.dumps(query_result,ensure_ascii=False)}')

    return query_result


def get_html_source(host_url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
        'Referer': f'http://tonkiang.us/hotellist.html?s={host_url}&Submit=+&y=y',
        'Cookie': '_ga=GA1.1.543562100.1714962214; HstCfa4853344=1714962215577; HstCmu4853344=1714962215577; HstCla4853344=1714971113698; HstPn4853344=1; HstPt4853344=8; HstCnv4853344=2; HstCns4853344=3; _ga_JNMLRB3QLF=GS1.1.1714971113.2.1.1714971547.0.0.0'
    }

    response = requests.get(
        f'http://tonkiang.us/alllist.php?s={host_url}&c=false&y=y', headers=headers)

    html = response.text

    return html


def get_channel_sources(html, province_name=None, host_url=None):
    try:
        bs = BeautifulSoup(html, 'html.parser')

        # 获取直播源名称
        channel_name = 'data'
        channel_results = bs.select('div[class="result"]')

        if channel_results is not None and len(channel_results) > 0:
            channel_name = channel_results[0].b.text.replace(':', '_')

        tables = bs.select('div[class="tables"]')
        logger.info(f'{province_name}-{host_url}-直播源_tables长度：{len(tables)}')

        sources = []

        for table in tables:
            results = table.select('div[class="result"]')
            #  logger.info(f'channels长度：{len(results)}')
            for result in results:
                channels = result.select('.channel')
                if channels is None or len(channels) <= 0:
                    continue
                name = str(channels[0].div.text.replace('\n', ''))
                # logger.info(f'channel_name：{name}')
                m3u8 = result.select('.m3u8')[0]
                url = str(m3u8.select('td')[1].text.strip())
                # logger.info(f'channel_url：{url}')
                ishdchannel = check_hd_channel(name)

                sources.append({
                    'name': name,
                    'url': url,
                    'ishdchannel': ishdchannel
                })
        # logger.info(f'{channel_name}:{json.dumps(sources,ensure_ascii=False)}')
        return channel_name, sources
    except:
        logger.info(f'{province_name}-{host_url}-获取直播源出错')
        return None, None


def sort_key(item):
    num = re.sub('\D', '', item['name'])
    if num is None or len(num) == 0:
        num = '0'
    return item['name'], int(num)


def build_channel_sources(channel_sources):
    source_types = {'全部': [], '央视频道': [], '卫视频道': [], '高清频道': [], '其他频道': []}

    if channel_sources and len(channel_sources) > 0:
        for channel_source in channel_sources:
            if channel_source['ishdchannel']:
                # channel_source_copy = copy.deepcopy(channel_source)
                source_types['高清频道'].append(channel_source)
            else:
                channel_source['name'] = build_channel_name(
                    channel_source['name'])
                if ('CCTV' in channel_source['name'] or 'CGTN' in channel_source['name']):
                    source_types['央视频道'].append(channel_source)
                elif '卫视' in channel_source['name']:
                    source_types['卫视频道'].append(channel_source)
                else:
                    source_types['其他频道'].append(channel_source)

            source_types['全部'].append(channel_source)
    return source_types


def build_channel_name(name):
    if name:
        # 删除特定文字
        name = name.replace("cctv", "CCTV")
        name = name.replace("中央", "CCTV")
        name = name.replace("央视", "CCTV")
        name = name.replace("高清", "")
        name = name.replace("超高", "")
        name = name.replace("HD", "")
        name = name.replace("标清", "")
        name = name.replace("频道", "")
        name = name.replace("-", "")
        name = name.replace(" ", "")
        name = name.replace("PLUS", "+")
        name = name.replace("＋", "+")
        name = name.replace("(", "")
        name = name.replace(")", "")
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


def build_json_file(channel_name, dict_sources):  # 保存json数据
    if dict_sources is not None and len(dict_sources) > 0:
        have_channel = False
        for key, value in dict_sources.items():
            for item in value:
                have_channel = True
        if have_channel:
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
            with open(f"sources/{channel_name}.m3u8", "w", encoding='utf-8') as file:
                file.write(m3u8_string)


def get_channel_sources_by_province(province):
    province_name = province['province_name']
    province_code = province['province_code']
    query_result = query_by_province(province_name)

    if query_result is None or not 'sources' in query_result.keys():
        return

    sources = query_result['sources']

    if sources is None or len(sources) == 0:
        return
    province_channel_sources = []
    for source in query_result['sources']:
        html = get_html_source(source['ip_port'])
        channel_name, channel_sources = get_channel_sources(html)
        if channel_sources is None:
            continue
        # channel_sources = check_url_available(province, channel_sources)
        province_channel_sources.extend(channel_sources)

    dict_sources = build_channel_sources(province_channel_sources)
    build_json_file(province_code, dict_sources)
    build_txt_file(province_code, dict_sources)
    build_m3u8_file(province_code, dict_sources)


def get_channel_sources_by_province1(province):
    result_source = []
    province_name = province['province_name']
    province_code = province['province_code']
    prev_url = None
    page = None
    code = None
    for i in range(1, 4):
        query_result = query_by_province(
            province_name, prev_url, page, code)
        if query_result is None or len(query_result.keys()) == 0:
            continue
        prev_url = query_result['prev_url']
        page = i+1
        code = query_result['code']
        result_source.extend(query_result['sources'])

    if result_source is None or len(result_source) == 0:
        return
    result_source = sorted(
        result_source, key=lambda x: (-x['active_day'], x['channel_number']), reverse=True)

    if len(result_source) > 7:
        result_source = result_source[0:7]

    province_channel_sources = []
    for source in result_source:
        html = get_html_source(source['ip_port'])
        channel_name, channel_sources = get_channel_sources(
            html, province_name, source['ip_port'])
        if channel_sources is None:
            continue
        channel_sources = check_url_available(province, channel_sources)
        province_channel_sources.extend(channel_sources)

    dict_sources = build_channel_sources(province_channel_sources)
    build_json_file(province_code, dict_sources)
    build_txt_file(province_code, dict_sources)
    build_m3u8_file(province_code, dict_sources)


def check_url_available(province, sources):
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
                                f"{province['province_name']}-可用-{i['name']}-{i['url']}")
                            available_sources.append(i)
                        else:
                            logger.info(
                                f"{province['province_name']}-不可用-{i['name']}-{i['url']}")
                        break
                else:
                    if netloc in timeout_host.keys():
                        del timeout_host[netloc]

                    logger.info(
                        f"{province['province_name']}-可用-{i['name']}-{i['url']}")
                    available_sources.append(i)
            else:
                logger.info(
                    f"{province['province_name']}-不可用-{i['name']}-{i['url']}")
        except requests.exceptions.Timeout:
            if netloc in timeout_host.keys():
                timeout_host[netloc] += 1
            else:
                timeout_host[netloc] = 1
            logger.error(
                f"{province['province_name']}-{i['name']}-{i['url']}-请求超时，超时时间设置为{timeout}秒")
        except requests.exceptions.RequestException as ex:
            logger.error(
                f"{province['province_name']}-出错-{i['name']}-{i['url']}{ex}")
        except Exception as ex:
            logger.error(
                f"{province['province_name']}-出错-{i['name']}-{i['url']}{ex}")
    return available_sources


def get_signal_sources(host_url):
    html = get_html_source(host_url)
    channel_name, channel_sources = get_channel_sources(html)
    province = {'province_name': channel_name}
    channel_sources = check_url_available(province, channel_sources)
    dict_sources = build_channel_sources(channel_sources)
    build_json_file(channel_name, dict_sources)
    build_txt_file(channel_name, dict_sources)
    build_m3u8_file(channel_name, dict_sources)


def check_hd_channel(channel_name):
    channel_name = channel_name.lower()
    for keyword in hdkeyword:
        if keyword in channel_name:
            return True
    return False


def check_test(url):
    # ll是电视直播源的链接列表
    ll = ['http://113.66.209.46:88/hls/215575592/index.m3u8']
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36'}
    se = requests.Session()

    for i in ll:
        try:
            res = se.get(i, headers=headers, timeout=timeout, stream=True)
            if res.status_code == 200:
                # 多获取的视频数据进行5秒钟限制
                start_time = time.time()
                test_total_size = 1*1024*1024
                total_size = 0
                for content in res.iter_content(chunk_size=1*1024*1024):
                    # 这里的chunk_size是1MB，每次读取1MB测试视频流
                    # 如果能获取视频流，则输出读取的时间以及链接
                    if content:
                        file_size = len(content)
                        total_size += file_size
                        end_time = time.time()
                        response_time = (end_time - start_time) * 1
                        # print(f"{test_counter}文件大小：{file_size} 字节")
                        # print(f"{test_counter}下载耗时：{response_time} s")
                        download_speed = total_size / response_time / 1024
                        # print(f"下载速度：{download_speed:.3f} kB/s")
                        # 将速率从kB/s转换为MB/s并限制在1~100之间
                        normalized_speed = min(
                            max(download_speed / 1024, 0.001), 100)
                        print(
                            f"标准化后的速率：{normalized_speed:.3f} MB/s")
                        if total_size >= test_total_size:
                            break

        except Exception as ex:
            # 无法连接并超时的情况下输出“X”
            logger.error(f'出错-{ex}')
            print(f'X\t{i}')


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


if __name__ == "__main__":
    host_url = '182.148.14.215:8888'
    argv = sys.argv[1:]
    config = None
    province_dict_list: List[dict[str, str]] = []
    province_dict: dict[str, str] = {}
    try:
        opts, args = getopt.getopt(argv, "hi:o:")
    except getopt.GetoptError:
        print('test.py -i <input province> -o <output file>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('test.py -i <input province> -o <output file>')
            sys.exit()
        elif opt in ("-i"):
            province_dict["province_name"] = arg
        elif opt in ("-o"):
            province_dict["province_code"] = f'{arg}_iptv'
    province_dict_list.append(province_dict)

    with open(config_path, 'r', encoding='utf-8') as file:
        config = json.load(file)
    if 'timeout' in config:
        timeout = int(config['timeout'])
    if 'isCheckUrlAvailable' in config:
        is_check_url_available = config['isCheckUrlAvailable']
    if 'isTestSpeed' in config:
        isTestSpeed = config['isTestSpeed']
    logger = init_logger(config['logPath'])

    for province in province_dict_list:
        get_channel_sources_by_province1(province)
        logger.info(f'{province["province_name"]}-直播源抓取结束')
    # exit(0)

    # for province in province_dict:

    #     result_source = []
    #     province_name = province['province_name']
    #     province_code = province['province_code']
    #     prev_url = None
    #     page = None
    #     code = None
    #     for i in range(1, 3):
    #         query_result = query_by_province(
    #             province_name, prev_url, page, code)
    #         if query_result is None or len(query_result.keys()) == 0:
    #             continue
    #         prev_url = query_result['prev_url']
    #         page = i+1
    #         code = query_result['code']
    #         result_source.extend(query_result['sources'])
    #     result_source = sorted(
    #         result_source, key=lambda x: (x['active_day'], x['channel_number']), reverse=True)
    # exit(0)

    # get_signal_sources(host_url)
