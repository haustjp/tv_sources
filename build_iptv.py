import re
import json


def build_channel_sources(channel_sources):
    source_types = {'全部': [], '央视频道': [], '卫视频道': [], '高清频道': [], '其他频道': []}

    if channel_sources and len(channel_sources) > 0:
        for channel_source in channel_sources:
            source_types['全部'].append(channel_source)
            # channel_source['name'] = build_channel_name(channel_source['name'])
            if ('CCTV' in channel_source['name'] or 'CGTN' in channel_source['name']) and not channel_source['ishdchannel']:
                source_types['央视频道'].append(channel_source)
            elif '卫视' in channel_source['name'] and not channel_source['ishdchannel']:
                source_types['卫视频道'].append(channel_source)
            elif not channel_source['ishdchannel']:
                source_types['其他频道'].append(channel_source)
            else:
                source_types['高清频道'].append(channel_source)

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


def build_m3u8_file(channel_name, dict_sources):  # 保存m3u8数据
    if dict_sources is not None and len(dict_sources) > 0:
        m3u8_string = '#EXTM3U\n'
        for key, value in dict_sources.items():
            for item in value:
                m3u8_string += f"#EXTINF:-1 group-title=\"{key}\",{item['name']}\n{item['url']}\n"

        with open(f"sources/{channel_name}.m3u8", "w", encoding='utf-8') as file:
            file.write(m3u8_string)


if __name__ == "__main__":
    channel_data = None
    dict_sources = []
    with open('C:\\Users\\HXM\\Desktop\\Wireshark\\batch.json', 'r', encoding='utf-8') as file:
        channel_data = json.load(file)

    if channel_data:
        channel_list = channel_data['channellist']
        if channel_list and len(channel_list) > 0:
            for channel in channel_list:
                channelname = str(channel['channelname'])
                channelurl = str(channel['channelurl']).split('|')[1]
                ishdchannel = channel['ishdchannel']
                ishdchannel = False
                if ishdchannel == '2' or '高清' in channelname:
                    ishdchannel = True

                dict_sources.append(
                    {'name': channelname, 'url': channelurl, 'ishdchannel': ishdchannel})
    source_types = build_channel_sources(dict_sources)

    build_json_file('chinaunionm', source_types)
    build_txt_file('chinaunionm', source_types)
    build_m3u8_file('chinaunionm', source_types)
