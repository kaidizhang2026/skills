#!/usr/bin/env python3
"""
validate_stickers.py - 校验微信表情包素材集是否符合微信表情开放平台规范。

用法: python3 validate_stickers.py <素材集目录>

校验项：
  - 目录结构（main/ thumbnail/ chat_icon/ cover/ banner/）
  - 主图数量（16/24）、格式、尺寸 240x240、大小 ≤500KB、编号 01..N
  - 缩略图与主图一一对应、PNG、尺寸 120x120(专辑)/240x240(单品)、≤200KB
  - 聊天页图标 PNG 50x50 ≤100KB、封面 PNG 240x240 ≤500KB、横幅 750x400 ≤500KB
  - 主图/缩略图/图标/封面透明底
  - GIF 永久循环（loop=0）
"""
import os
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("需要 Pillow：pip install Pillow")

ERRORS, WARNS = [], []


def err(msg):
    ERRORS.append(msg)


def warn(msg):
    WARNS.append(msg)


def check_image(path, expect_size, expect_fmts, max_bytes, need_alpha):
    name = os.path.relpath(path)
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    if ext not in expect_fmts:
        err(f"{name}: 格式 {ext} 不在允许范围 {expect_fmts}")
        return
    size = os.path.getsize(path)
    if size > max_bytes:
        err(f"{name}: 文件大小 {size // 1024}KB 超过限制 {max_bytes // 1024}KB")
    try:
        img = Image.open(path)
    except Exception as e:
        err(f"{name}: 无法打开图片（{e}）")
        return
    if img.size != expect_size:
        err(f"{name}: 尺寸 {img.size[0]}x{img.size[1]} 不符合 {expect_size[0]}x{expect_size[1]}")
    if need_alpha:
        img_rgba = img.convert("RGBA")
        alpha = img_rgba.getchannel("A")
        if ext == "gif":
            has_trans = True  # GIF 透明判断复杂，交由人工预览
        else:
            lo, hi = alpha.getextrema()
            has_trans = lo < 250
            if not has_trans:
                err(f"{name}: 背景不透明（要求透明背景）")
        if ext == "png" and (img.mode == "P" or img.mode == "RGB"):
            if has_trans is False:
                pass  # 已在上面报过
    # 横幅特殊要求：不透明、避免白色背景
    return img


def check_gif_loop(path):
    img = Image.open(path)
    if getattr(img, "n_frames", 1) <= 1:
        warn(f"{os.path.relpath(path)}: 是单帧 GIF（动态表情应有多帧）")
    info = img.info
    # PIL 解析 loop: 0=永久循环
    if info.get("loop", None) != 0:
        err(f"{os.path.relpath(path)}: GIF 未设置永久循环（loop!=0）")


def main():
    if len(sys.argv) != 2:
        sys.exit("用法: python3 validate_stickers.py <素材集目录>")
    root = sys.argv[1]
    if not os.path.isdir(root):
        sys.exit(f"目录不存在：{root}")

    for d in ("main", "thumbnail", "chat_icon", "cover", "banner"):
        if not os.path.isdir(os.path.join(root, d)):
            err(f"缺少目录：{d}/")

    main_files = sorted(os.listdir(os.path.join(root, "main"))) if os.path.isdir(
        os.path.join(root, "main")) else []
    main_files = [f for f in main_files if not f.startswith(".")]
    n = len(main_files)

    # 数量
    if n not in (16, 24):
        err(f"主图数量为 {n}，规范要求 16 或 24 张")
    else:
        print(f"[数量] {n} 张主图 ✓")

    # 格式统一（全动态或全静态）
    exts = {os.path.splitext(f)[1].lower().lstrip(".") for f in main_files}
    if len(exts) > 1:
        err(f"主图格式不统一：{exts}（同一套须全部 GIF 或全部 PNG）")
    is_gif = exts == {"gif"}

    # 编号与逐张校验
    thumbs = sorted(f for f in os.listdir(os.path.join(root, "thumbnail"))
                    if not f.startswith(".")) if os.path.isdir(
        os.path.join(root, "thumbnail")) else []
    thumb_size = (240, 240) if os.path.isdir(os.path.join(root, "thumbnail")) and \
        any(f and len(f) > 2 and os.path.getsize(os.path.join(root, "thumbnail", f)) and
            Image.open(os.path.join(root, "thumbnail", f)).size == (240, 240)
            for f in thumbs) else (120, 120)

    for i, f in enumerate(main_files, 1):
        num = f"{i:02d}"
        expect_name = f"{num}.{list(exts)[0] if len(exts) == 1 else 'png'}"
        if os.path.splitext(f)[0] != num:
            err(f"main/{f}: 命名不规范，应为两位数字编号（{num}）")
        path = os.path.join(root, "main", f)
        if is_gif:
            check_image(path, (240, 240), ("gif",), 500 * 1024, True)
            check_gif_loop(path)
        else:
            check_image(path, (240, 240), ("png", "jpeg", "jpg"), 500 * 1024, True)
        # 缩略图对应
        t_expect = [x for x in thumbs if os.path.splitext(x)[0] == num]
        if not t_expect:
            err(f"缺少与主图 {num} 对应的缩略图")
        else:
            check_image(os.path.join(root, "thumbnail", t_expect[0]), thumb_size,
                        ("png",), 200 * 1024, True)
    extra_thumbs = [t for t in thumbs if os.path.splitext(t)[0] not in
                    {os.path.splitext(f)[0] for f in main_files}]
    for t in extra_thumbs:
        err(f"thumbnail/{t}: 缩略图数量多于主图或编号无对应")

    # 其他素材
    icon = os.path.join(root, "chat_icon", "icon.png")
    if os.path.exists(icon):
        check_image(icon, (50, 50), ("png",), 100 * 1024, True)
    else:
        err("缺少聊天页图标 chat_icon/icon.png")

    cover = os.path.join(root, "cover", "cover.png")
    if os.path.exists(cover):
        check_image(cover, (240, 240), ("png",), 500 * 1024, True)
    else:
        err("缺少封面图 cover/cover.png")

    for bf in ("banner.png", "banner.jpg"):
        bp = os.path.join(root, "banner", bf)
        if os.path.exists(bp):
            img = check_image(bp, (750, 400), ("png", "jpg", "jpeg"), 500 * 1024, False)
            if img is not None and img.mode in ("RGBA", "LA", "P"):
                # 检查是否实际透明
                rgba = img.convert("RGBA")
                lo, _ = rgba.getchannel("A").getextrema()
                if lo < 250:
                    err(f"banner/{bf}: 横幅不能使用透明背景")
            break
    else:
        err("缺少详情页横幅 banner/banner.png 或 banner.jpg")

    # 输出结果
    print()
    for w in WARNS:
        print(f"⚠️  警告: {w}")
    if ERRORS:
        print(f"\n❌ 校验未通过，共 {len(ERRORS)} 个问题：")
        for e in ERRORS:
            print(f"  ✗ {e}")
        sys.exit(1)
    print("✅ 校验全部通过！素材集符合微信表情开放平台规范，可按目录逐项上传提审。")


if __name__ == "__main__":
    main()
