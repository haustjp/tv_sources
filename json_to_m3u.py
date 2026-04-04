import argparse
import json
from pathlib import Path


DEFAULT_HEADER = (
    '#EXTM3U x-tvg-url="https://epg.zsdc.eu.org/t.xml.gz" '
    'catchup="append" '
    'catchup-source="?playseek=${(b)yyyyMMddHHmmss}-${(e)yyyyMMddHHmmss}"'
)
DEFAULT_LOGO_PREFIX = "https://gh-proxy.org/https://github.com/fanmingming/live/blob/main/tv/"


def clean_attr(value: str) -> str:
    return str(value).replace('"', "'").replace("\n", " ").replace("\r", " ").strip()


def clean_text(value: str) -> str:
    return str(value).replace("\n", " ").replace("\r", " ").strip()


def load_header_from_template(template_path: Path) -> str:
    for line in template_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if line.startswith("#EXTM3U"):
            return line
    return DEFAULT_HEADER


def make_logo_url(channel: dict, tvg_name: str) -> str:
    icon = clean_attr(channel.get("icon", ""))
    if icon:
        return icon
    name_for_logo = tvg_name or clean_attr(channel.get("itemTitle", ""))
    return f"{DEFAULT_LOGO_PREFIX}{name_for_logo}.png"


def json_to_m3u(input_json: Path, output_m3u: Path, header: str) -> int:
    data = json.loads(input_json.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Input JSON must be a list of groups.")

    lines = [header]
    channel_count = 0

    for group in data:
        group_title = clean_attr(group.get("channel_type_title", ""))
        channels = group.get("channel_list", [])
        if not isinstance(channels, list):
            continue

        for channel in channels:
            if not isinstance(channel, dict):
                continue

            url = clean_text(channel.get("url", ""))
            if not url:
                continue

            tvg_id = clean_attr(channel.get("itemId") or channel.get("url_id") or "")
            tvg_name = clean_attr(channel.get("tvg-name") or channel.get("logo") or channel.get("itemTitle") or "")
            title = clean_text(channel.get("itemTitle") or tvg_name or "")
            tvg_logo = make_logo_url(channel, tvg_name)

            extinf = (
                f'#EXTINF:-1 tvg-id="{tvg_id}" tvg-name="{tvg_name}" '
                f'tvg-logo="{tvg_logo}" group-title="{group_title}",{title}'
            )
            lines.append(extinf)
            lines.append(url)
            channel_count += 1

    output_m3u.parent.mkdir(parents=True, exist_ok=True)
    output_m3u.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return channel_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert grouped channel JSON to M3U.")
    parser.add_argument("-i", "--input", required=True, help="Input grouped JSON file path")
    parser.add_argument("-o", "--output", required=True, help="Output m3u file path")
    parser.add_argument(
        "-t",
        "--template",
        help="Template m3u path, reads its #EXTM3U line (e.g. sources/guangdong.m3u)",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    template_path = Path(args.template) if args.template else None

    if template_path and template_path.exists():
        header = load_header_from_template(template_path)
    else:
        header = DEFAULT_HEADER

    count = json_to_m3u(input_path, output_path, header)
    print(f"Generated {count} channels -> {output_path}")


if __name__ == "__main__":
    main()
