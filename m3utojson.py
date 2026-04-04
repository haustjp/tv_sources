import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlparse
from collections import OrderedDict


URL_PATTERN = re.compile(r"https?://\S+")
MEDIA_SUFFIXES = (".m3u8", ".ts", ".mp4", ".flv", ".mpd")


def extract_id_from_url(url: str) -> str:
    segments = [seg for seg in urlparse(url).path.split("/") if seg]
    if not segments:
        return ""

    segment = segments[-1]
    # Most IPTV URLs end with a fixed media file (for example 01.m3u8).
    # If that happens, use the previous path segment as the id source.
    if segment.lower().endswith(MEDIA_SUFFIXES) and len(segments) >= 2:
        segment = segments[-2]

    if "_" in segment:
        return segment.split("_", 1)[0]
    return segment


def extract_group_from_extinf(line: str) -> str:
    marker = 'group-title="'
    start = line.find(marker)
    if start == -1:
        return "Ungrouped"

    start += len(marker)
    comma_pos = line.find(",", start)
    quote_pos = line.find('"', start)

    if quote_pos != -1 and (comma_pos == -1 or quote_pos < comma_pos):
        group = line[start:quote_pos].strip()
        return group or "Ungrouped"

    if comma_pos != -1:
        group = line[start:comma_pos].strip()
        return group or "Ungrouped"

    group = line[start:].strip()
    return group or "Ungrouped"


def extract_attr_value(line: str, attr: str) -> str:
    marker = f'{attr}="'
    start = line.find(marker)
    if start == -1:
        return ""

    start += len(marker)
    comma_pos = line.find(",", start)
    quote_pos = line.find('"', start)

    if quote_pos != -1 and (comma_pos == -1 or quote_pos < comma_pos):
        return line[start:quote_pos].strip()
    if comma_pos != -1:
        return line[start:comma_pos].strip()
    return line[start:].strip()


def parse_extinf_line(line: str) -> tuple[str, str]:
    _, _, payload = line.partition(",")
    payload = payload.strip()
    url_match = URL_PATTERN.search(payload)
    if not url_match:
        return payload, ""

    name = payload[: url_match.start()].strip()
    url = url_match.group(0).strip()
    return name, url


def build_channel_type_code(index: int) -> str:
    return f"m3u_group_{index:03d}"


def convert_m3u_to_json(input_path: Path, output_path: Path) -> list[dict]:
    lines = input_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    grouped: OrderedDict[str, list[dict]] = OrderedDict()

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line.startswith("#EXTINF"):
            i += 1
            continue

        group = extract_group_from_extinf(line)
        tvg_id = extract_attr_value(line, "tvg-id")
        tvg_name = extract_attr_value(line, "tvg-name")
        name, url = parse_extinf_line(line)

        if not url:
            j = i + 1
            while j < len(lines):
                candidate = lines[j].strip()
                if not candidate:
                    j += 1
                    continue
                if candidate.startswith("#EXTINF"):
                    break
                if URL_PATTERN.match(candidate):
                    url = candidate
                    break
                j += 1
            i = j

        if name and url:
            url_id = extract_id_from_url(url)
            channels = grouped.setdefault(group, [])
            item_id = tvg_id or f"{len(grouped):03d}{len(channels) + 1:06d}"
            grouped.setdefault(group, []).append(
                {
                    "itemId": item_id,
                    "itemTitle": name,
                    "dataLink": "",
                    "icon": "",
                    "hwcode": url_id,
                    "url": url,
                    "url_id": url_id,
                    "logo": name,
                    "tvg-name": tvg_name or name,
                }
            )

        i += 1

    result = []
    for idx, (group, channels) in enumerate(grouped.items(), start=1):
        result.append(
            {
                "channel_type_title": group,
                "channel_type_url": "",
                "channel_type_code": build_channel_type_code(idx),
                "channel_list": channels,
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert M3U file to JSON.")
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        help="Input .m3u file path",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output .json file path (default: same name as input)",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.with_suffix(".json")

    data = convert_m3u_to_json(input_path, output_path)
    print(f"Converted {len(data)} entries -> {output_path}")


if __name__ == "__main__":
    main()
