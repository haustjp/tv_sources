import argparse
import json
from collections import OrderedDict
from pathlib import Path
from urllib.parse import urlparse


MEDIA_SUFFIXES = (".m3u8", ".ts", ".mp4", ".flv", ".mpd")


def id_from_segment(segment: str) -> str:
    value = segment
    if "_" in value:
        value = value.split("_", 1)[0]
    if "." in value:
        value = value.split(".", 1)[0]
    return value


def extract_url_id(url: str) -> str:
    if not url:
        return ""

    segments = [seg for seg in urlparse(url).path.split("/") if seg]
    if not segments:
        return ""

    last = segments[-1]
    last_id = id_from_segment(last)

    if last.lower().endswith(MEDIA_SUFFIXES):
        # For links like .../01.m3u8 use previous segment.
        # For links like .../0125_1.m3u8 keep the current segment id.
        is_generic_tail = (
            last_id.lower() in {"01", "1", "index", "playlist", "chunklist", "master"}
            or (last_id.isdigit() and len(last_id) <= 2)
        )
        if is_generic_tail and len(segments) >= 2:
            return id_from_segment(segments[-2])

    return last_id


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_channel(channel: dict) -> dict:
    result = dict(channel)

    if "itemTitle" not in result:
        result["itemTitle"] = result.get("name", "")
    if "url" not in result:
        result["url"] = ""
    if "url_id" not in result or not result["url_id"]:
        result["url_id"] = extract_url_id(result.get("url", ""))
    if "itemId" not in result:
        chid = result.get("chid")
        result["itemId"] = str(chid) if chid is not None else result["url_id"] or ""
    if "logo" not in result:
        result["logo"] = result.get("itemTitle", "")
    if "tvg-name" not in result:
        result["tvg-name"] = result.get("itemTitle", "")
    if "hwcode" not in result:
        result["hwcode"] = result.get("url_id", "")

    return result


def normalize_groups(data) -> list[dict]:
    # Format A: [{channel_type_title, channel_list, ...}, ...]
    if isinstance(data, list):
        groups = []
        for idx, group in enumerate(data, start=1):
            title = group.get("channel_type_title") or f"group_{idx:03d}"
            channels = [normalize_channel(x) for x in group.get("channel_list", [])]
            groups.append(
                {
                    "channel_type_title": title,
                    "channel_type_url": group.get("channel_type_url", ""),
                    "channel_type_code": group.get("channel_type_code", f"group_{idx:03d}"),
                    "channel_list": channels,
                }
            )
        return groups

    # Format B: {"group_name": [{name,url,...}, ...], ...}
    if isinstance(data, dict):
        groups = []
        for idx, (title, channels) in enumerate(data.items(), start=1):
            if not isinstance(channels, list):
                continue
            groups.append(
                {
                    "channel_type_title": str(title),
                    "channel_type_url": "",
                    "channel_type_code": f"group_{idx:03d}",
                    "channel_list": [normalize_channel(x) for x in channels if isinstance(x, dict)],
                }
            )
        return groups

    raise ValueError("Unsupported JSON format.")


def channel_merge_key(channel: dict) -> str:
    key = channel.get("url_id", "")
    if key:
        return f"url_id:{key}"

    item_id = channel.get("itemId", "")
    if item_id:
        return f"itemId:{item_id}"

    return f"url:{channel.get('url', '')}"


def finalize_channel(channel: dict) -> dict:
    output = dict(channel)
    output.setdefault("itemId", "")
    output.setdefault("itemTitle", "")
    output.setdefault("dataLink", "")
    output.setdefault("icon", "")
    output.setdefault("hwcode", output.get("url_id", ""))
    output.setdefault("url", "")
    output.setdefault("url_id", extract_url_id(output.get("url", "")))
    output.setdefault("logo", output.get("itemTitle", ""))
    output.setdefault("tvg-name", output.get("itemTitle", ""))
    return output


def merge_by_group_and_url_id(base_groups: list[dict], preferred_groups: list[dict]) -> list[dict]:
    merged = OrderedDict()

    # 1) base groups first
    for g in base_groups:
        title = g["channel_type_title"]
        group_meta = {
            "channel_type_title": title,
            "channel_type_url": g.get("channel_type_url", ""),
            "channel_type_code": g.get("channel_type_code", ""),
        }
        channels_map = OrderedDict()
        for channel in g.get("channel_list", []):
            ch = normalize_channel(channel)
            channels_map[channel_merge_key(ch)] = ch
        merged[title] = {"meta": group_meta, "channels": channels_map}

    # 2) preferred groups override by (group + url_id)
    for g in preferred_groups:
        title = g["channel_type_title"]
        if title not in merged:
            merged[title] = {
                "meta": {
                    "channel_type_title": title,
                    "channel_type_url": g.get("channel_type_url", ""),
                    "channel_type_code": g.get("channel_type_code", ""),
                },
                "channels": OrderedDict(),
            }
        else:
            # group-level preference: non-empty preferred fields override
            if g.get("channel_type_url"):
                merged[title]["meta"]["channel_type_url"] = g["channel_type_url"]
            if g.get("channel_type_code"):
                merged[title]["meta"]["channel_type_code"] = g["channel_type_code"]

        channels_map = merged[title]["channels"]
        for channel in g.get("channel_list", []):
            preferred_channel = normalize_channel(channel)
            key = channel_merge_key(preferred_channel)
            if key in channels_map:
                merged_channel = dict(channels_map[key])
                merged_channel.update(preferred_channel)  # preferred wins on conflicts
                channels_map[key] = merged_channel
            else:
                channels_map[key] = preferred_channel

    ordered_titles = []
    seen_titles = set()
    for group in preferred_groups:
        title = group["channel_type_title"]
        if title in merged and title not in seen_titles:
            ordered_titles.append(title)
            seen_titles.add(title)

    for title in merged.keys():
        if title not in seen_titles:
            ordered_titles.append(title)
            seen_titles.add(title)

    result = []
    for title in ordered_titles:
        group = merged[title]
        meta = group["meta"]
        channels = [finalize_channel(c) for c in group["channels"].values()]
        result.append(
            {
                "channel_type_title": meta["channel_type_title"],
                "channel_type_url": meta.get("channel_type_url", ""),
                "channel_type_code": meta.get("channel_type_code", ""),
                "channel_list": channels,
            }
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Merge two channel JSON files by group and url_id, with second file preferred."
    )
    parser.add_argument("-a", "--base", required=True, help="Base JSON file path (e.g., gdlt.json)")
    parser.add_argument(
        "-b",
        "--preferred",
        required=True,
        help="Preferred JSON file path (e.g., guangdong.json), wins on conflicts",
    )
    parser.add_argument("-o", "--output", required=True, help="Output merged JSON file path")
    args = parser.parse_args()

    base_path = Path(args.base)
    preferred_path = Path(args.preferred)
    output_path = Path(args.output)

    base_groups = normalize_groups(read_json(base_path))
    preferred_groups = normalize_groups(read_json(preferred_path))
    merged = merge_by_group_and_url_id(base_groups, preferred_groups)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")

    base_count = sum(len(g["channel_list"]) for g in base_groups)
    preferred_count = sum(len(g["channel_list"]) for g in preferred_groups)
    merged_count = sum(len(g["channel_list"]) for g in merged)
    print(
        f"Merged done: base={base_count}, preferred={preferred_count}, "
        f"output={merged_count}, groups={len(merged)} -> {output_path}"
    )


if __name__ == "__main__":
    main()
