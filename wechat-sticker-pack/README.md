# wechat-sticker-pack 微信表情包技能

依据[微信表情开放平台](https://sticker.weixin.qq.com)官方《微信表情制作规范》《微信作品审核标准》制作的通用 AI Agent 技能（Skill），可在支持 SKILL.md 规范的智能体（如 WorkBuddy、Claude Code 等）中使用。

## 功能

- **创意策划**：规划表情数量（16/24 张）、动/静态、主题角色与表情清单
- **图片规范适配**：主图 240×240、缩略图 120×120、聊天页图标 50×50、封面 240×240、详情页横幅 750×400，自动压缩至平台大小限制
- **合规校验**：一键校验素材数量、格式、尺寸、大小、编号命名、一一对应关系、GIF 永久循环、透明底等
- **提审指引**：产出符合平台上传目录结构的素材集，附注册与提审流程

## 目录结构

```
wechat-sticker-pack/
├── SKILL.md                          # 技能入口（工作流程 + 规范速查表）
├── references/
│   └── wechat-sticker-spec.md        # 微信表情开放平台完整官方规范
└── scripts/
    ├── process_stickers.py           # 素材规范处理（缩放/抠底/压缩/目录生成）
    └── validate_stickers.py          # 平台规范合规校验
```

## 使用方法

1. 将本目录安装到智能体的技能目录（如 `~/.workbuddy/skills/` 或 `.claude/skills/`）。
2. 对智能体说："帮我做一套微信表情包"，或提供已有素材图要求"处理成微信表情包规范格式"。
3. 处理完成后用校验脚本确认合规：

```bash
python3 scripts/process_stickers.py --src <源图目录> --out <输出目录> --mode album --format png --autocut white
python3 scripts/validate_stickers.py <输出目录>
```

## 依赖

- Python 3.8+，Pillow（`pip install Pillow`）

## 核心规范速查

| 素材 | 数量 | 格式 | 尺寸 | 大小 |
|---|---|---|---|---|
| 表情主图 | 16/24 张 | GIF/PNG | 240×240 | ≤500KB |
| 缩略图 | 与主图对应 | PNG | 120×120（专辑） | ≤200KB |
| 聊天页图标 | 1 张 | PNG | 50×50 | ≤100KB |
| 封面图 | 1 张 | PNG | 240×240 | ≤500KB |
| 详情页横幅 | 1 张 | PNG/JPEG | 750×400 | ≤500KB |
| 赞赏引导图（可选） | 1 张 | PNG | 750×560 | — |
| 赞赏致谢图（可选） | 1 张 | PNG | 750×750 | — |
