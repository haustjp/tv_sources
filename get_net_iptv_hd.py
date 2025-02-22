import os
import time
import string
import re
import sys
import urllib.parse
import requests
import json
import zipfile
import base64
import hashlib
import random
import xxtea
from html import unescape
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad


def download(url, output):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(output, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
    except Exception as e:
        print(e)


def base64_decode(s):
    decoded_bytes = base64.b64decode(s)
    decoded_str = decoded_bytes.decode('utf-8', errors='replace')
    escaped_str = unescape(decoded_str)
    return urllib.parse.unquote(escaped_str)


def remove_ip_from_url(url):
    first_slash_index = url.find('/', url.find('://') + 3)
    if first_slash_index != -1:
        domain_start = url.find('://') + 3
        domain = url[domain_start:first_slash_index]
        if '.' in domain and not all(part.isdigit() for part in domain.split('.')):
            return url
        return url[:domain_start] + url[first_slash_index + 1:]
    return url


def get_random_string():
    characters = string.ascii_uppercase + string.digits
    random_string = ''.join(random.choices(characters, k=32))
    return random_string


def get_account_info():
    account_infos = []
    try:
        response = requests.get(
            "https://raw.githubusercontent.com/isw866/iptv/refs/heads/main/ipv6-fmm.m3u")
        response.raise_for_status()
        content = response.text
        lines = content.splitlines()
        for line in lines:
            if "accountinfo=" in line:
                start_index = line.find("accountinfo=") + len("accountinfo=")
                end_index = line.find("&", start_index)
                if end_index == -1:
                    end_index = len(line)
                _accountinfo = line[start_index:end_index]
                parts = _accountinfo.split('%7E')
                if len(parts) >= 4:
                    accountinfo = '%7E'.join(parts[4:]).replace('%2CEND', '')
                    print(f"ACCOUNTINFO：{accountinfo}")
                    account_infos.append({"ACCOUNTINFO": accountinfo})
                    break
        if not account_infos:
            print("获取AccountInfo失败")
        return account_infos
    except Exception as e:
        print(e)
        return []


def get_stb_id():
    stb_ids = []
    try:
        download("http://api.y977.com/iptv.txt.zip", '/tmp/iptv.zip')
        with zipfile.ZipFile('/tmp/iptv.zip', 'r') as zip_ref:
            zip_ref.extract('iptv.txt', '/tmp/', "xfflchVCWG9941".encode())
        with open('/tmp/iptv.txt', 'r', encoding='utf-8') as f:
            content = f.read()
        match = re.search(r'stbId=([^&]+)', content)
        if match:
            stb_id = match.group(1)
            print(f"STBID：{stb_id}")
            stb_ids.append({"STBID": stb_id})
        else:
            print("获取stbId失败")
    except Exception as e:
        print(e)
    return stb_ids


def get_xizang_tv():
    xizang_tvs = []
    try:
        data = {
            "json": '{"appId":"dc36548f-2dae-457e-ae68-45b2d1081973","cardgroups":"LIVECAST"}'
        }
        response = requests.post(
            'https://api.vtibet.cn/xizangmobileinf/rest/xz/cardgroups', data=data)
        response.raise_for_status()
        xizang_tv = json.loads(response.text)[
            "cardgroups"][0]["cards"][0]["video"]["url_hd"]
        if xizang_tv:
            print(f"XIZANGTV：{xizang_tv}")
            xizang_tvs.append({"XIZANGTV": xizang_tv})
        else:
            print("西藏获取失败")
    except Exception as e:
        print(e)
    return xizang_tvs


def get_xinjiang_tv():
    xinjiang_tvs = []
    try:
        timestamp = str(int(time.time() * 1000))
        sign_str = f"@#@$AXdm123%)(ds{timestamp}api/TVLiveV100/TVChannelList"
        sign = hashlib.md5(sign_str.encode()).hexdigest()
        response = requests.get(
            f"https://slstapi.xjtvs.com.cn/api/TVLiveV100/TVChannelList?type=1&stamp={timestamp}&sign={sign}&json=true")
        response.raise_for_status()
        xinjiang_tv = json.loads(response.text)["data"][0]["PlayStreamUrl"]
        if xinjiang_tv:
            print(f"XINJIANGTV：{xinjiang_tv}")
            xinjiang_tvs.append({"XINJIANGTV": xinjiang_tv})
        else:
            print("新疆获取失败")
    except Exception as e:
        print(e)
    return xinjiang_tvs


def get_shanxi_tv():
    shanxi_tvs = []
    try:
        headers = {
            "api-o0": "method=GET, timings=true, timeout=300000, rejectUnauthorized=false, followRedirect=true",
            "api-u": "https://dyhhplus.sxrtv.com/apiv4.5/api/m3u8_notoken?channelid=q8RVWgs&site=53"
        }
        response = requests.post(
            'https://web-proxy.apifox.cn/api/v1/request', headers=headers)
        response.raise_for_status()
        shanxi_tv = json.loads(response.text)["data"]["address"]
        if shanxi_tv:
            print(f"SHANXITV：{shanxi_tv}")
            shanxi_tvs.append({"SHANXITV": shanxi_tv})
        else:
            print("山西获取失败")
    except Exception as e:
        print(e)
    return shanxi_tvs


def get_shaanxi_tv():
    shaanxi_tvs = []
    try:
        headers = {
            "api-o0": "method=GET, timings=true, timeout=300000, rejectUnauthorized=false, followRedirect=true",
            "api-u": "https://toutiao.cnwest.com/static/v1/group/stream.js"
        }
        response = requests.post(
            'https://web-proxy.apifox.cn/api/v1/request', headers=headers)
        response.raise_for_status()
        content = response.text
        sTV = re.search(r'var sTV="([^"]+)', content)
        sRadio = re.search(r'var sRadio="([^"]+)', content)
        if sTV is None or sRadio is None:
            print("提取sTV/sRadio失败")
        else:
            sTV = sTV.group(1)
            sRadio = sRadio.group(1)
            key = sTV[:16].encode('utf-8')
            iv = sRadio[:16].encode('utf-8')
            mapTV = sTV[16:]
            try:
                ciphertext = base64.b64decode(mapTV)
                try:
                    cipher = AES.new(key, AES.MODE_CBC, iv)
                    decrypted = cipher.decrypt(ciphertext)
                    decrypted_text = decrypted.rstrip(b'\x00').decode('utf-8')
                    data = json.loads(decrypted_text)
                    shaanxi_tv = data["sxbc"]["star"]["m3u8"]
                    if shaanxi_tv:
                        print(f"SHAANXITV：{shaanxi_tv}")
                        shaanxi_tvs.append({"SHAANXITV": shaanxi_tv})
                    else:
                        print("陕西获取失败")
                except Exception as e:
                    print(e)
            except Exception as e:
                print(e)
    except Exception as e:
        print(e)
    return shaanxi_tvs


def get_neimenggu_tv():
    neimenggu_tvs = []
    try:
        headers = {
            "api-o0": "method=GET, timings=true, timeout=300000, rejectUnauthorized=false, followRedirect=true",
            "api-u": "https://api-bt.nmtv.cn/index/moduleList?page=1&relationId=38&sourceType=channel"
        }
        response = requests.post(
            'https://web-proxy.apifox.cn/api/v1/request', headers=headers)
        response.raise_for_status()
        content = response.text.strip('"')
        key = "5b28bae827e651b3"
        decrypted_text = xxtea.decrypt(content, key)
        data = json.loads(decrypted_text)
        neimenggu_tv = data["data"][3]["contentList"][0]["data"]["broadcast"]["streamUrl"]
        if neimenggu_tv:
            print(f"NEIMENGGUTV：{neimenggu_tv}")
            neimenggu_tvs.append({"NEIMENGGUTV": neimenggu_tv})
        else:
            print("内蒙古获取失败")
    except Exception as e:
        print(e)
    return neimenggu_tvs


def get_ningxia_tv():
    ningxia_tvs = []
    session = requests.Session()
    retry_strategy = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount('https://', adapter)
    try:
        headers = {
            "Referer": "https://www.nxtv.com.cn/tv/ws/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0"
        }
        response = session.get(
            "https://www.nxtv.com.cn/m2o/channel/channel_info.php?id=6", headers=headers, timeout=10)
        response.raise_for_status()
        ningxia_tv = json.loads(response.text)[0]["channel_stream"][0]["m3u8"]
        if ningxia_tv:
            print(f"NINGXIATV：{ningxia_tv}")
            ningxia_tvs.append({"NINGXIATV": ningxia_tv})
        else:
            print("宁夏获取失败")
    except Exception as e:
        print(e)
    return ningxia_tvs


def get_henan_tv():
    henan_tvs = []
    try:
        timestamp = str(int(time.time()))
        sign_str = "6ca114a836ac7d73" + str(timestamp)
        sha256_hash = hashlib.sha256()
        sha256_hash.update(sign_str.encode('utf-8'))
        sign = sha256_hash.hexdigest()
        headers = {
            "Referer": "https://static.hntv.tv/",
            "timestamp": timestamp,
            "sign": sign
        }
        response = requests.get(
            "https://pubmod.hntv.tv/program/getAuth/channel/channelIds/1/145", headers=headers)
        response.raise_for_status()
        henan_tv = json.loads(response.text)[0]["video_streams"][0]
        response = requests.get(henan_tv)
        response.raise_for_status()
        content = response.text
        lines = content.splitlines()
        for line in lines:
            if line.startswith("http"):
                henan_tv = remove_ip_from_url(line)
                break
        if henan_tv:
            print(f"HENANTV：{henan_tv}")
            henan_tvs.append({"HENANTV": henan_tv})
        else:
            print("河南获取失败")
    except Exception as e:
        print(e)
    return henan_tvs


def get_beijing_tv():
    gids = [
        ("573ib1kp5nk92irinpumbo9krlb", "BEIJINGTV"),
        ("54db6gi5vfj8r8q1e6r89imd64s", "BEIJINGWY"),
        ("53bn9rlalq08lmb8nf8iadoph0b", "BEIJINGKJ"),
        ("50mqo8t4n4e8gtarqr3orj9l93v", "BEIJINGYS"),
        ("50e335k9dq488lb7jo44olp71f5", "BEIJINGCJ"),
        ("50j015rjrei9vmp3h8upblr41jf", "BEIJINGSH"),
        ("53gpt1ephlp86eor6ahtkg5b2hf", "BEIJINGXW"),
        ("55skfjq618b9kcq9tfjr5qllb7r", "BEIJINGSR")
    ]
    beijing_tvs = []
    for gid, placeholder in gids:
        timestamp = str(int(time.time()))
        sign_str = f"{gid}151{timestamp}TtJSg@2g*$K4PjUH"
        sign = hashlib.md5(sign_str.encode()).hexdigest()[:8]
        try:
            headers = {
                "Referer": "https://www.btime.com/"
            }
            response = requests.get(
                f"https://pc.api.btime.com/video/play?id={gid}&type_id=151&timestamp={timestamp}&sign={sign}", headers=headers)
            response.raise_for_status()
            stream_url = json.loads(response.text)[
                "data"]["video_stream"][0]["stream_url"]
            beijing_tv = base64_decode(base64_decode(stream_url[::-1]))
            if beijing_tv:
                print(f"{placeholder}：{beijing_tv}")
                beijing_tvs.append({placeholder: beijing_tv})
            else:
                print("北京获取失败")
        except Exception as e:
            print(e)
    return beijing_tvs


def update_data(data_list):
    template_path = '/www/wwwroot/IPTV/_iptv'
    output_path = '/www/wwwroot/IPTV/iptv.m3u'
    if os.path.exists(template_path):
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        for info in data_list:
            for placeholder, value in info.items():
                template_content = template_content.replace(
                    f'{{{placeholder}}}', value or '')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(template_content)
        print("数据更新完成")
    else:
        print("模版文件不存在")


def update_m3u8(m3u8_list):
    for info in m3u8_list:
        for placeholder, value in info.items():
            output_path = f'/www/wwwroot/IPTV/{placeholder}.m3u8'
            content = f'#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1600000\n{value}'
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            except Exception as e:
                print(e)


def main():

    data_list = []
    print("正在获取AccountInfo...")
    data_list.extend(get_account_info())

    print("正在获取stbId...")
    # data_list.extend(get_stb_id())
    data_list.append({"STBID": get_random_string()})

    m3u8_list = []
    print("获取新疆数据中...")
    m3u8_list.extend(get_xinjiang_tv())

    print("获取山西数据中...")
    m3u8_list.extend(get_shanxi_tv())

    print("获取陕西数据中...")
    m3u8_list.extend(get_shaanxi_tv())

    print("获取内蒙古数据中...")
    m3u8_list.extend(get_neimenggu_tv())

    print("获取西藏数据中...")
    m3u8_list.extend(get_xizang_tv())

    print("获取宁夏数据中...")
    m3u8_list.extend(get_ningxia_tv())

    print("获取河南数据中...")
    m3u8_list.extend(get_henan_tv())

    print("获取北京数据中...")
    m3u8_list.extend(get_beijing_tv())

    print("正在更新数据中...")
    update_data(data_list)
    update_m3u8(m3u8_list)

    try:
        os.remove('/tmp/iptv.txt')
        os.remove('/tmp/iptv.zip')
    except FileNotFoundError:
        pass


if __name__ == "__main__":
    os.chdir(os.path.dirname(__file__))
    main()
