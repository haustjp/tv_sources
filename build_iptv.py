import os
import re
import json


def read_channel_sources_form_txt(filePath: str):
    dict_sources = []
    with open(filePath, 'r', encoding='utf-8') as file:
        for line in file:
            if line is None or len(line) == 0:
                continue
            line = line.strip()
            items = line.split(',')
            if len(items) != 2:
                continue
            dict_sources.append(
                {'name': items[0], 'url': items[1], 'ishdchannel': True})

    return dict_sources


def build_channel_sources(channel_sources):
    source_types = {
        # '全部': [],
        '央视频道': [],
        '卫视频道': [],
        '其他频道': []
    }

    if channel_sources and len(channel_sources) > 0:
        for channel_source in channel_sources:
            channel_source['name'] = build_channel_name(channel_source['name'])
            # source_types['全部'].append(channel_source)
            if ('CCTV' in channel_source['name'] or 'CGTN' in channel_source['name']):
                source_types['央视频道'].append(channel_source)
            elif '卫视' in channel_source['name']:
                source_types['卫视频道'].append(channel_source)
            else:
                source_types['其他频道'].append(channel_source)

        for key, value in source_types.items():
            source_types[key] = sorted(
                value, key=lambda x: extract_number(x["name"]))

    return source_types


def build_channel_name(name):
    if name:
        # 删除特定文字
        name = name.replace("cctv", "CCTV")
        name = name.replace("中央", "CCTV")
        name = name.replace("央视", "CCTV")
        # name = name.replace("高清", "")
        # name = name.replace("超高", "")
        # name = name.replace("HD", "")
        # name = name.replace("标清", "")
        # name = name.replace("频道", "")
        name = name.replace("-", "")
        name = name.replace(" ", "")
        name = name.replace("PLUS", "+")
        name = name.replace("＋", "+")
        name = name.replace("(", "")
        name = name.replace(")", "")
        # name = re.sub(r"CCTV(\d+)台", r"CCTV\1", name)
        # name = name.replace("CCTV1综合", "CCTV1")
        # name = name.replace("CCTV2财经", "CCTV2")
        # name = name.replace("CCTV3综艺", "CCTV3")
        # name = name.replace("CCTV4国际", "CCTV4")
        # name = name.replace("CCTV4中文国际", "CCTV4")
        # name = name.replace("CCTV4欧洲", "CCTV4")
        # name = name.replace("CCTV5体育", "CCTV5")
        # name = name.replace("CCTV6电影", "CCTV6")
        # name = name.replace("CCTV7军事", "CCTV7")
        # name = name.replace("CCTV7军农", "CCTV7")
        # name = name.replace("CCTV7农业", "CCTV7")
        # name = name.replace("CCTV7国防军事", "CCTV7")
        # name = name.replace("CCTV8电视剧", "CCTV8")
        # name = name.replace("CCTV9记录", "CCTV9")
        # name = name.replace("CCTV9纪录", "CCTV9")
        # name = name.replace("CCTV10科教", "CCTV10")
        # name = name.replace("CCTV11戏曲", "CCTV11")
        # name = name.replace("CCTV12社会与法", "CCTV12")
        # name = name.replace("CCTV13新闻", "CCTV13")
        # name = name.replace("CCTV新闻", "CCTV13")
        # name = name.replace("CCTV14少儿", "CCTV14")
        # name = name.replace("CCTV15音乐", "CCTV15")
        # name = name.replace("CCTV16奥林匹克", "CCTV16")
        # name = name.replace("CCTV17农业农村", "CCTV17")
        # name = name.replace("CCTV17农业", "CCTV17")
        # name = name.replace("CCTV5+体育赛视", "CCTV5+")
        # name = name.replace("CCTV5+体育赛事", "CCTV5+")
        # name = name.replace("CCTV5+体育", "CCTV5+")
        name = re.sub(r'北京IPTV', '', name)
        name = re.sub(r'高清', '', name)
        name = re.sub(r'-', '', name)
        name = name.replace('福建东南卫视', '东南卫视')
        # 使用正则表达式去掉中括号及其内容
        if '[' in name:
            name = re.sub(r'\[.*\]', '', name)
            # 去掉可能存在的多余空格
            name = name.strip()
        if 'CCTV' in name and contains_digit(name):
            result = re.findall(r'(CCTV\d+\+?)', name)
            name = ''.join(result)
    return name


def extract_number(channel):
    # 提取字符串中的数字部分，如果没有数字则返回一个较小的值
    numbers = ''.join(filter(str.isdigit, channel))
    return int(numbers) if numbers else 9999  # 如果没有数字，返回 9999


def contains_digit(s):
    return bool(re.search(r'\d', s))


def build_json_file(channel_name, dict_sources):  # 保存json数据
    if dict_sources is not None and len(dict_sources) > 0:
        json_string = json.dumps(dict_sources, ensure_ascii=False)
        if len(json_string):
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


def build_m3u8_file(channel_name, dict_sources):  # 保存m3u8数据
    if dict_sources is not None and len(dict_sources) > 0:
        m3u8_string = '#EXTM3U x-tvg-url="https://epg.zsdc.eu.org/t.xml.gz" catchup="append" catchup-source="?playseek=${(b)yyyyMMddHHmmss}-${(e)yyyyMMddHHmmss}"\n'
        have_channel = False
        for key, value in dict_sources.items():
            for item in value:
                have_channel = True
                m3u8_string += f'#EXTINF:-1 tvg-id="{item["name"]}" tvg-name="{item["name"]}" tvg-logo="https://epg.112114.xyz/logo/{item["name"]}.png" group-title="{key}",{item["name"]}\n{item["url"]}\n'
        if have_channel:
            if not os.path.exists('sources'):
                os.mkdir('sources')
            with open(f"sources/{channel_name}.m3u", "w", encoding='utf-8') as file:
                file.write(m3u8_string)


if __name__ == "__main__":
    channel_data = None
    dict_sources = []
    if not os.path.exists('sources'):
        os.mkdir('sources')
    dict_sources = read_channel_sources_form_txt(
        'D:\\iptvcheck\\live\\bjyd_20250223103700\\bjyd_20250223103700.txt')

    source_types = build_channel_sources(dict_sources)

    build_json_file('chinaunionm', source_types)
    build_txt_file('chinaunionm', source_types)
    build_m3u8_file('chinaunionm', source_types)
