import os
import re
import json
from urllib.parse import urlparse

def extract_channel_id(url):
    """
    使用 urllib.parse 解析 URL，精准提取 channel_id
    从路径最后一段提取： 12345_0.smil → 提取 12345
    """
    try:
        # 解析 URL，拿到路径部分
        parsed = urlparse(url)
        path = parsed.path
        
        # 获取路径最后一段（文件名）
        filename = path.strip("/").split("/")[-2]
        
        # 按下划线分割，取第一部分就是 channel_id
        if "_" in filename:
            channel_id = filename.split("_")[0]
            return channel_id
        else:
            channel_id = filename.split(".")[0]
            return channel_id
    except:
        pass
    
    return None

def m3u_to_json_with_channel_id(m3u_file_path, output_path="./sources/m3u_with_channel_id.json"):
    """M3U转JSON并自动提取url中的channel_id"""

    result = []
    with open(m3u_file_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    
    # 匹配M3U的EXTINF行
    inf_pattern = re.compile(
        r'#EXTINF:-1\s+tvg-id="(?P<tvg_id>.*?)"\s+tvg-name="(?P<tvg_name>.*?)"\s+group-title="(?P<group_title>.*?)",(?P<name>.*?)'
    )

    for i, line in enumerate(lines):
        if line.startswith("#EXTINF") and i + 1 < len(lines):
            match = inf_pattern.match(line)
            if match:
                channel_info = match.groupdict()
                play_url = lines[i + 1]
                channel_info["url"] = play_url
                # 自动提取channel_id，无则为None
                channel_info["channel_id"] = extract_channel_id(play_url)
                result.append(channel_info)

    # 写入JSON文件
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=4)
    print(f"整合完成，文件已保存至：{output_path}")
    return result

# 测试：传入含SMIL地址的M3U内容
if __name__ == "__main__":
    os.chdir(os.path.dirname(__file__))
    m3u_to_json_with_channel_id('./online/广东联通重修版.m3u')