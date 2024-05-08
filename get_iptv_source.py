from bs4 import BeautifulSoup
import json
import requests
import re


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


def get_channel_sources(html):
    bs = BeautifulSoup(html, 'html.parser')

    # 获取直播源名称
    channel_name = 'data'
    channel_results = bs.select('div[class="result"]')

    if channel_results is not None and len(channel_results) > 0:
        channel_name = channel_results[0].b.text.replace(':', '_')

    tables = bs.select('div[class="tables"]')
    print(f'tables长度：{len(tables)}')

    sources = []

    for table in tables:
        results = table.select('div[class="result"]')
        # print(f'channels长度：{len(results)}')
        for result in results:
            channels = result.select('.channel')
            if channels is None or len(channels) <= 0:
                continue
            name = channels[0].div.text.replace('\n', '')
            print(f'channel_name：{name}')
            m3u8 = result.select('.m3u8')[0]
            url = m3u8.select('td')[1].text.strip()
            print(f'channel_url：{url}')

            sources.append({
                'name': name,
                'url': url
            })

    return channel_name, sources


def sort_key(item):
    num = re.sub('\D', '', item['name'])
    if num is None or len(num) == 0:
        num = '0'
    return item['name'], int(num)


def build_channel_sources(channel_sources):
    source_types = {'央视频道': [], '卫视频道': [], '其他频道': []}

    if channel_sources and len(channel_sources) > 0:
        for channel_source in channel_sources:
            channel_source['name'] = build_channel_name(channel_source['name'])
            if 'CCTV' in channel_source['name'] or 'CGTN' in channel_source['name']:
                source_types['央视频道'].append(channel_source)
            elif '卫视' in channel_source['name']:
                source_types['卫视频道'].append(channel_source)
            else:
                source_types['其他频道'].append(channel_source)
    # for key, value in source_types.items():
    #     source_types[key] = sorted(value, key=sort_key)
    #     # sorted(value, key=lambda x: x['name'])

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

        with open(f"sources/{channel_name}.txt", "w", encoding='utf-8') as file:
            file.write(txt_string)


def build_m3u8_file(channel_name, sources):  # 保存m3u8数据
    if dict_sources is not None and len(dict_sources) > 0:
        m3u8_string = '#EXTM3U\n'
        for key, value in dict_sources.items():
            for item in value:
                m3u8_string += f"#EXTINF:-1 group-title=\"{key}\",{item['name']}\n{item['url']}\n"

        with open(f"sources/{channel_name}.m3u8", "w", encoding='utf-8') as file:
            file.write(m3u8_string)


if __name__ == "__main__":
    host_url = '221.220.108.96:4000'
    html = get_html_source(host_url)
    channel_name, channel_sources = get_channel_sources(html)
    dict_sources = build_channel_sources(channel_sources)
    build_json_file(channel_name, dict_sources)
    build_txt_file(channel_name, dict_sources)
    build_m3u8_file(channel_name, dict_sources)
