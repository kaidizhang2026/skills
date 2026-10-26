#!/usr/bin/env python3
"""
process_stickers.py - 将源图片处理为符合微信表情开放平台规范的素材集。

输出目录结构：
  main/      主图 01.png / 01.gif ...（240x240, 动态GIF ≤500KB 或 静态PNG ≤500KB）
  thumbnail/ 缩略图 01.png ...（专辑 120x120 / 单图 240x240, ≤200KB）
  chat_icon/ 聊天页图标 icon.png（50x50, ≤100KB）
  cover/     封面图 cover.png（240x240, ≤500KB）
  banner/    详情页横幅 banner.png（750x400, ≤500KB, 不透明白背景）

用法:
  python3 process_stickers.py --src ./src_images --out ./sticker-set \
      --mode album --format png --autocut white

参数:
  --src     源图目录（主图素材，按文件名排序编号）
  --out     输出目录
  --mode    album=表情专辑（缩略图120x120）/ single=单图表情（缩略图240x240）
  --format  png=静态主图 / gif=动态主图（gif 模式要求源图为 GIF 动图）
  --autocut 可选：去除指定纯色背景，如 white / #ffffff / #f0f0f0（默认关闭）
  --banner-bg 横幅背景色，默认 #F6D55C（活泼黄，避免白色）
"""
import argparse
import os
import shutil
import sys

try:
    from PIL import Image, ImageSequence
except ImportError:
    sys.exit("需要 Pillow：pip install Pillow")

TARGETS = {
    "main": (240, 240),
    "chat_icon": (50, 50),
    "cover": (240, 240),
    "banner": (750, 400),
}
MAX_SIZES = {"main": 500 * 1024, "thumbnail": 200 * 1024,
             "chat_icon": 100 * 1024, "cover": 500 * 1024, "banner": 500 * 1024}


def parse_color(s):
    s = s.strip().lstrip("#")
    if len(s) == 6:
        return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))
    named = {"white": (255, 255, 255), "black": (0, 0, 0)}
    return named.get(s.lower())


def remove_flat_bg(img, color, tolerance=28):
    """将接近 color 的纯色背景像素转为透明（含抗锯齿边缘按距离渐变）。"""
    img = img.convert("RGBA")
    px = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            dist = max(abs(r - color[0]), abs(g - color[1]), abs(b - color[2]))
            if dist <= tolerance:
                px[x, y] = (r, g, b, 0)
            elif dist <= tolerance * 2:
                px[x, y] = (r, g, b, int(255 * (dist - tolerance) / tolerance))
    return img


def fit_canvas(img, size):
    """等比缩放并居中放置到透明画布，不拉伸变形。"""
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    ratio = min(size[0] / img.width, size[1] / img.height)
    new_size = (max(1, int(img.width * ratio)), max(1, int(img.height * ratio)))
    resized = img.convert("RGBA").resize(new_size, Image.LANCZOS)
    canvas.paste(resized, ((size[0] - new_size[0]) // 2, (size[1] - new_size[1]) // 2),
                 resized)
    return canvas


def save_png_under_limit(img, path, limit):
    """保存 PNG，超限则逐级降低色彩数压缩。"""
    for colors in (256, 128, 64, 32):
        out = img
        if colors < 256:
            alpha = img.getchannel("A")
            quant = img.convert("RGB").quantize(colors=colors, method=Image.MEDIANCUT)
            out = quant.convert("RGBA")
            out.putalpha(alpha)
        out.save(path, "PNG", optimize=True)
        if os.path.getsize(path) <= limit:
            return
    # 最后兜底：直接保留最后结果（极端情况提示用户手工处理）


def load_gif_frames(path):
    img = Image.open(path)
    frames, durations = [], []
    for f in ImageSequence.Iterator(img):
        rgba = f.convert("RGBA")
        dur = f.info.get("duration", 100)
        frames.append(rgba)
        durations.append(dur if dur and dur > 10 else 100)
    return frames, durations


def save_gif_under_limit(frames, durations, path, limit, max_side=240):
    """GIF 超 500KB 时依次：降色板 → 抽帧 → 缩小尺寸，直到满足限制。"""
    for colors in (256, 128, 64):
        for keep in (1, 2, 3):  # 每隔 keep 帧取 1 帧
            sel = frames[::keep]
            sel_d = durations[::keep]
            for scale in (1.0, 0.75):
                cur = [f if scale == 1.0 else f.resize(
                    (int(f.width * scale), int(f.height * scale)), Image.LANCZOS)
                    for f in sel]
                # 统一到 240x240 画布
                fitted = [fit_canvas(f, (max_side, max_side)) if f.size != (max_side, max_side)
                          else f for f in cur]
                fitted[0].save(path, "GIF", save_all=True, append_images=fitted[1:],
                               duration=sel_d, loop=0, transparency=0,
                               disposal=2)
                if os.path.getsize(path) <= limit:
                    return
    # 仍超限则保留最后结果，由校验脚本提示


def make_banner(src_imgs, path):
    """用前 4 张表情形象拼贴出 750x400 横幅（无文字、非白色背景）。"""
    banner = Image.new("RGBA", TARGETS["banner"], (246, 213, 92, 255))  # 活泼黄底
    positions = [(60, 90, 260), (300, 60, 300), (470, 120, 240), (180, 200, 180)]
    for i, (x, y, h) in enumerate(positions[:min(4, len(src_imgs))]):
        img = src_imgs[i].convert("RGBA")
        ratio = h / img.height
        img = img.resize((int(img.width * ratio), h), Image.LANCZOS)
        banner.alpha_composite(img, (x, y))
    banner.convert("RGB").save(path, "PNG", optimize=True)
    if os.path.getsize(path) > MAX_SIZES["banner"]:
        banner.convert("RGB").save(path, "JPEG", quality=85)


def main():
    ap = argparse.ArgumentParser(description="微信表情包规范素材生成工具")
    ap.add_argument("--src", required=True, help="源图目录")
    ap.add_argument("--out", required=True, help="输出目录")
    ap.add_argument("--mode", choices=["album", "single"], default="album")
    ap.add_argument("--format", choices=["png", "gif"], default="png", dest="fmt")
    ap.add_argument("--autocut", default=None, help="去除纯色背景，如 white 或 #RRGGBB")
    ap.add_argument("--banner-bg", default="#F6D55C")
    args = ap.parse_args()

    src_dir = os.path.abspath(args.src)
    out_dir = os.path.abspath(args.out)
    exts = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")
    files = sorted(f for f in os.listdir(src_dir) if f.lower().endswith(exts))
    if not files:
        sys.exit(f"源目录没有图片：{src_dir}")
    n = len(files)
    if n not in (16, 24) and args.mode == "album":
        print(f"[警告] 专辑主图数量为 {n}（规范要求 16 或 24），请补齐或删减源图。")

    for d in ("main", "thumbnail", "chat_icon", "cover", "banner"):
        os.makedirs(os.path.join(out_dir, d), exist_ok=True)

    cut = parse_color(args.autocut) if args.autocut else None
    thumb_size = TARGETS["thumbnail"] if args.mode == "single" else (120, 120)

    static_cache = []  # 供横幅/封面/图标复用
    for idx, fname in enumerate(files, 1):
        num = f"{idx:02d}"
        src_path = os.path.join(src_dir, fname)
        if args.fmt == "gif" and fname.lower().endswith(".gif"):
            frames, durs = load_gif_frames(src_path)
            if cut:
                frames = [remove_flat_bg(f, cut) for f in frames]
            fitted = [fit_canvas(f, (240, 240)) for f in frames]
            main_path = os.path.join(out_dir, "main", f"{num}.gif")
            save_gif_under_limit(fitted, durs, main_path, MAX_SIZES["main"])
            key = fitted[len(fitted) // 2]  # 中间帧做缩略图
            print(f"[主图] {num}.gif  {os.path.getsize(main_path) // 1024}KB  {len(fitted)}帧")
        else:
            img = Image.open(src_path)
            if cut:
                img = remove_flat_bg(img, cut)
            fitted = fit_canvas(img, (240, 240))
            main_path = os.path.join(out_dir, "main", f"{num}.png")
            save_png_under_limit(fitted, main_path, MAX_SIZES["main"])
            key = fitted
            print(f"[主图] {num}.png  {os.path.getsize(main_path) // 1024}KB")

        # 缩略图（关键帧，无白描边，透明底）
        thumb = fit_canvas(key, thumb_size)
        thumb_path = os.path.join(out_dir, "thumbnail", f"{num}.png")
        save_png_under_limit(thumb, thumb_path, MAX_SIZES["thumbnail"])
        static_cache.append(key)

    # 聊天页图标：取第 1 张（建议用户替换为角色头部正面像）
    icon = fit_canvas(static_cache[0], (50, 50))
    icon_path = os.path.join(out_dir, "chat_icon", "icon.png")
    save_png_under_limit(icon, icon_path, MAX_SIZES["chat_icon"])

    # 封面：取第 1 张
    cover = fit_canvas(static_cache[0], (240, 240))
    cover_path = os.path.join(out_dir, "cover", "cover.png")
    save_png_under_limit(cover, cover_path, MAX_SIZES["cover"])

    # 横幅拼贴
    banner_path = os.path.join(out_dir, "banner", "banner.png")
    make_banner(static_cache, banner_path)

    print(f"\n完成 ✅ 素材集输出到：{out_dir}")
    print("下一步：python3 validate_stickers.py " + out_dir)


if __name__ == "__main__":
    main()
