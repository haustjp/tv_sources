from bs4 import BeautifulSoup
import json
import requests

host_url = '221.220.108.96:4000'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
    'Referer': f'http://tonkiang.us/hotellist.html?s={host_url}&Submit=+&y=y',
    'Cookie': '_ga=GA1.1.543562100.1714962214; HstCfa4853344=1714962215577; HstCmu4853344=1714962215577; HstCla4853344=1714971113698; HstPn4853344=1; HstPt4853344=8; HstCnv4853344=2; HstCns4853344=3; _ga_JNMLRB3QLF=GS1.1.1714971113.2.1.1714971547.0.0.0'
}

response = requests.get(
    f'http://tonkiang.us/alllist.php?s={host_url}&c=false&y=y', headers=headers)
# print(response.text)
html = response.text
# file = open(r'test.html', 'rb')
# html = file.read()
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
    print(f'channels长度：{len(results)}')
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

if sources is not None and len(sources) > 0:
    # 保存json数据
    json_string = json.dumps(sources, ensure_ascii=False)
    with open(f"sources/{channel_name}.json", "w", encoding='utf-8') as file:
        file.write(json_string)

    # 保存txt数据
    txt_string = ''
    for source in sources:
        txt_string += f"{source['name']},{source['url']}\n"

    with open(f"sources/{channel_name}.txt", "w", encoding='utf-8') as file:
        file.write(txt_string)

    # 保存m3u8数据
    m3u8_string = '#EXTM3U\n'
    for source in sources:
        m3u8_string += f"#EXTINF:-1 ,{source['name']}\n{source['url']}\n"

    with open(f"sources/{channel_name}.m3u8", "w", encoding='utf-8') as file:
        file.write(m3u8_string)
