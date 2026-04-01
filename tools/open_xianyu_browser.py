from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import load_settings
from crawler.xianyu_browser import XianyuBrowserCrawler


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Open a local Xianyu browser session for login or slider verification.'
    )
    parser.add_argument(
        '--url',
        default=None,
        help='Optional URL to open after the browser starts.',
    )
    parser.add_argument(
        '--wait-seconds',
        type=float,
        default=0,
        help='Keep the browser open for N seconds before saving state and closing.',
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = load_settings()
    crawler = XianyuBrowserCrawler(settings)
    try:
        page = crawler._ensure_page()
        target_url = args.url or settings.xianyu_browser_start_url
        if target_url:
            page.goto(target_url, wait_until='domcontentloaded')
        if args.wait_seconds > 0:
            print(
                f'[INFO] Browser session is open for {args.wait_seconds} seconds. '
                'Finish login or slider verification now.'
            )
            page.wait_for_timeout(int(args.wait_seconds * 1000))
        else:
            input('[INFO] Browser session is ready. Press Enter after login/verification is complete...')
    finally:
        crawler.close()
        print('[INFO] Browser state saved. You can now run the local collector job.')


if __name__ == '__main__':
    main()
