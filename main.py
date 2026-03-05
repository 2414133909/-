"""
main.py — 问卷星快填 CLI 入口

用法示例：
    python main.py https://www.wjx.cn/vm/xxxxxxx.aspx
    python main.py https://www.wjx.cn/vm/xxxxxxx.aspx --count 5
    python main.py https://www.wjx.cn/vm/xxxxxxx.aspx --count 3 --show
    python main.py https://www.wjx.cn/vm/xxxxxxx.aspx --count 2 --interval 5
"""

import argparse
import sys

from wjx_filler import fill_batch


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wjx-filler",
        description="问卷星自动快填工具 — 自动识别题型并随机作答后提交",
    )
    parser.add_argument("url", help="问卷星问卷链接（https://www.wjx.cn/...）")
    parser.add_argument(
        "--count", "-n",
        type=int,
        default=1,
        metavar="N",
        help="填写次数（默认 1）",
    )
    parser.add_argument(
        "--interval", "-i",
        type=float,
        default=2.0,
        metavar="SEC",
        help="每次提交后的等待秒数（默认 2）",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="显示浏览器窗口（非无头模式，便于调试）",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.count < 1:
        parser.error("--count 必须 ≥ 1")

    print(f"问卷星快填 启动")
    print(f"  URL    : {args.url}")
    print(f"  次数   : {args.count}")
    print(f"  间隔   : {args.interval} 秒")
    print(f"  无头   : {'否（可见浏览器）' if args.show else '是'}")
    print()

    ok = fill_batch(
        url=args.url,
        count=args.count,
        headless=not args.show,
        interval=args.interval,
    )

    print()
    print(f"完成：共提交 {ok}/{args.count} 次")
    return 0 if ok > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
