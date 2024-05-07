import json
import requests

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
    iptv_urls.append(f'{service}://{ip}:{port}/iptv/live/1000.json?key=txiptv')


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
        for iptv_data in  iptv_datas['data']:
            iptv_data['url']= f"{iptv_url.replace('/iptv/live/1000.json?key=txiptv','')}{iptv_data['url']}"
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
        source_type = {'type': source['type'], 'typename': source['typename']}
        if source_type not in source_types:
            source_types.append(source_type)

source_types = sorted(source_types, key=lambda x: x['type'])

grouped_items = {}

for source_type in source_types:
    data_tmps = filter(lambda x: x['type'] == source_type['type'], new_sources)
    data_tmps = sorted(data_tmps, key=lambda x: x['chid'])
    grouped_items[source_type['type']] = data_tmps

# 获取直播源名称
channel_name = 'data'

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
