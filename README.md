# alfred Portrait vibe

Alfred 的个人视频制作技能。收到文案后，先用代码渲染同一个首分镜的四张视觉模板，并提供四个 Breeze TTS2 声音试听；由用户选定画面与声音，再逐步制作成片。

## 制作约定

- 默认 9:16、1080×1920、30fps；保留其他画幅的选择。
- 有价值信息位于居中的 3:4 安全区，左右各留至少 10% 距离。默认安全区为 864×1152，左上角 (108, 384)。按实际平台遮挡进一步调整。
- 四张模板由 HTML/CSS/SVG、Canvas 或 Remotion 代码实际渲染；使用同一首镜、文案和代表性状态，不只换颜色。
- Breeze TTS2 优先：四声同文试听，用户选声后固定音色生成全文。
- 以已确认配音的实际时长与对齐结果确定分镜，不按字数或固定秒数锁定镜头。
- 目标整理与粗分镜自动完成；选图选声、完整配音、精确分镜、样片及全片按约定等待确认。

## 使用流程

| 环节 | 技能完成的工作 | 用户选择 |
| --- | --- | --- |
| 自动准备 | 读文案、核对关键事实、整理粗分镜 | 无需确认 |
| 首轮选型 | 四张代码首镜图 A–D、四个声音 1–4 | 例如“画面 B，声音 3” |
| 完整配音 | 复用选定音色生成全文 | 读音、语速、情绪、停顿 |
| 精确分镜 | 按实际配音安排画面、字幕、动作和逐镜时长 | 确认时间表与表达 |
| 动态样片 | 约 10–20 秒，含真实配音与拟用声音 | 确认构图、动效和音画 |
| 全片与交付 | 全片自检、预览，确认后导出 | 修改或确认交付 |

## 能力范围

知识讲解、真实产品展示、代码动画与生成素材叙事共用一条流程。包含按题材选风格、个人预设、逐笔/关键词同步、真实计算、精简讲解组件、局部缓存与定点验收的制作规则。

按需启用：双语字幕、文献/档案再现、代码合成 BGM 和扩展音效库。

已移出：发布标题、话题、运营复盘及把封面强插到片头。风格和工具库按需参考，不整包导入大型风格库或多套渲染引擎。

## 检查工具

技能自带四个脚本，原则是**从产物里重新量一遍，不靠「检查过了」这句话**。它们不改内容，只报告哪里不合规。

| 脚本 | 作用 | 什么时候跑 |
| --- | --- | --- |
| `qa.py` | 成片闸门：分辨率、帧率、时长、音轨、黑帧、削波逐项判定，并出联络表和锚点前后帧 | 第 7 步样片、第 8 步全片 |
| `density.py` | 文案体检：字/秒、句/分、句长、口播腔、车轱辘话 | 第 3 步文案定稿后 |
| `beats.py` | 拍点、小节线、每小节响度 | 只有选了 B5 配乐时 |
| `bgm.py` | 纯 numpy 合成配乐，76–78 BPM 小调 | 只有选了 B5 且无现成配乐时 |

```bash
# 成片闸门：有 FAIL 时退出码为 1，不许交片
python skills/alfred-portrait-vibe/scripts/qa.py final.mp4 plan.json \
  --size 1080x1920 --fps 30 --anchor 3 12 27 -o qa

# 文案体检（film=稀疏字幕片，dense=高密度解说）
python skills/alfred-portrait-vibe/scripts/density.py 字幕.txt --duration 128 --genre film
```

依赖 `ffmpeg`/`ffprobe` 与 `numpy`；`density.py` 只用标准库。缺少依赖时如实说明缺口，不假装跑过。

阈值、报红规则和已知陷阱见[量化闸门](skills/alfred-portrait-vibe/references/gates.md)与[毛病对照表](skills/alfred-portrait-vibe/references/pitfalls.md)。

> **`beats.py` 的已知陷阱**：自动检测的偏好中心在 120 BPM，77 BPM 的配乐会被判成 154 BPM，小节线随之全部翻倍。自己用 `bgm.py` 合成的配乐**必须**用 `--bpm` 指定；看到 >140 或 <90 的警告要复核。

## 安装到 Codex

将本仓库中的 `skills/alfred-portrait-vibe` 文件夹复制到 `$CODEX_HOME/skills/alfred-portrait-vibe`；未设置 `CODEX_HOME` 时使用用户目录下的 `.codex/skills/alfred-portrait-vibe`。新会话中调用：

```text
$alfred-portrait-vibe
这是我的文案：……
```

## 安装到 WorkBuddy

复制到 `~/.workbuddy-ai/skills/alfred-portrait-vibe`（用户级，所有项目可用），或项目内的 `.workbuddy-ai/skills/alfred-portrait-vibe`（仅该项目）。新会话中提到「alfred Portrait vibe」或给出文案要求做视频即触发。

这是技能指令包，不捆绑浏览器、渲染引擎、模型权重、付费服务账户或第三方完整组件库。实际制片使用当前环境可用工具；Breeze 服务缺失时报告具体缺口，不擅自更换配音引擎，也不以文字说明冒充真实试听。

## 文件结构

```text
skills/alfred-portrait-vibe/
  SKILL.md
  agents/openai.yaml
  references/
    visual-design.md
    explainers.md
    product.md
    generated-media.md
    production.md
    gates.md          量化闸门：阈值与报红规则
    pitfalls.md       毛病对照表与实测陷阱
  scripts/
    qa.py             成片闸门
    density.py        文案体检
    beats.py          拍点分析
    bgm.py            配乐合成
```

完整流程见 [SKILL.md](skills/alfred-portrait-vibe/SKILL.md)，Breeze 接入说明见 [生成素材指南](skills/alfred-portrait-vibe/references/generated-media.md)。

## 更新记录

**v1.1.0**（2026-11-03）

- 新增 `scripts/` 工具层与两节参考（量化闸门、毛病对照表），接入第 7/8 步确认节点。
- 重写成片自检：原版只打印 `ok`，不判定规格与时长；现为逐项 PASS/FAIL，有 FAIL 退出码 1。
- 修 `beats.py` 八度错误：77 BPM 被检测为 154 BPM，小节线翻倍。
- 修 `production.md` 中指向不存在的 `sfx-source.py` 的引用。
- 移除音乐驱动的时间表工具：本技能的路线是配音驱动，两种排片方式并存会造成路线混乱。

**v1.0.0** 初版：四图四声选型、个人风格预设、按配音定时、逐步确认。

## 参考来源

本技能结合用户逐轮确定的制作要求，提炼以下工具与项目的方法；没有捆绑其完整源码、媒体素材或模型：

- Hypit：导演统筹、语义事件与素材组织。
- video-shotcraft：真实产品素材、镜头语言与声音设计。
- vibe-knowledge-film：概念可视化与因果讲解。
- [Remotion](https://www.remotion.dev/docs/)：帧驱动动画、可编辑工程与预览/导出。
- [andyhuo520/vibe-knowledge](https://github.com/andyhuo520/vibe-knowledge)：风格组织、个人预设和讲解组件思路。
- [xiazhuo123456789/vibe-knowledge-video](https://github.com/xiazhuo123456789/vibe-knowledge-video)：讲解设计、数值纪律和关键帧验收。
- [liangdabiao/whiteboard-teacher-video](https://github.com/liangdabiao/whiteboard-teacher-video)：逐笔、关键词同步及局部复用思路。
- [Breeze TTS2](https://github.com/breezeblue-ai/breeze-tts) 与 [官方 API](https://docs.breezeblue.ai/)：声音设计、保存选声和配音定时。

第三方代码、媒体、模型及服务仍遵循各自许可和条款；需要直接复用时查看实际资源授权。当前仓库提供制作指令与方法整合，尚未以完整视频验证所有组合能力。
