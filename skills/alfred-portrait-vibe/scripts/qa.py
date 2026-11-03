#!/usr/bin/env python3
"""成片闸门：从产物里重新量一遍，不达标就报红退出。

用法:
  python3 qa.py 成片.mp4 plan.json [--anchor 3 42] [--size 1080x1920] [--fps 30] [-o qa]

检查项（每项 PASS / WARN / FAIL）:
  规格    分辨率、帧率是否等于 --size / --fps（不给则只报告不判定）
  时长    实际时长 vs plan.duration，偏差 > --tol 秒报红（默认 0.15）
  音轨    有没有音频流；纯字幕片用 --silent 显式声明
  黑帧    非预期黑场（默认 > 0.10s 且像素 < 10% 判黑）
  削波    音频峰值 >= -0.1 dBFS 报红（可 --no-audio 跳过）
  出图    每屏 80% 处一帧拼联络表；--anchor 的屏给前后帧

plan.json 接受两种镜头表：
  {"duration": 128.4, "screens": [{"n":1,"t":0.0,"dur":3.2}, ...]}
  {"duration": 128.4, "shots":   [{"shotId":"s1","timelineStart":0.0,"duration":3.2}, ...]}

退出码: 0 全部通过（允许 WARN）；1 存在 FAIL。闸门脚本不允许"看起来成功"。
只依赖 ffmpeg/ffprobe；有 Pillow 则联络表带标签，没有则退回 ffmpeg tile。
"""
import argparse, json, os, re, subprocess, sys


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def probe(path):
    r = run(["ffprobe", "-v", "error", "-show_entries",
             "format=duration:stream=codec_type,width,height,r_frame_rate,avg_frame_rate,channels",
             "-of", "json", path])
    if r.returncode != 0:
        sys.exit(f"ffprobe 读不了这个文件: {path}\n{r.stderr.strip()}")
    return json.loads(r.stdout)


def parse_rate(s):
    if not s or s == "0/0":
        return None
    if "/" in s:
        n, d = s.split("/")
        return float(n) / float(d) if float(d) else None
    return float(s)


def shots_from_plan(P):
    """归一成 [(编号, 起点秒, 时长秒)]"""
    out = []
    if "screens" in P:
        for s in P["screens"]:
            out.append((s.get("n", len(out) + 1), float(s["t"]), float(s["dur"])))
    elif "shots" in P:
        for i, s in enumerate(P["shots"]):
            start = s.get("timelineStart", s.get("t", 0.0))
            dur = s.get("duration", s.get("dur"))
            if dur is None and s.get("timelineEnd") is not None:
                dur = float(s["timelineEnd"]) - float(start)
            out.append((s.get("shotId", i + 1), float(start), float(dur)))
    else:
        sys.exit("plan.json 里既没有 screens 也没有 shots")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("plan")
    ap.add_argument("--anchor", nargs="*", default=[], help="需要检查切点的屏编号/ID")
    ap.add_argument("--size", default=None, help="期望分辨率，如 1080x1920")
    ap.add_argument("--fps", type=float, default=None, help="期望帧率，如 30")
    ap.add_argument("--tol", type=float, default=0.15, help="时长允许偏差秒（默认 0.15）")
    ap.add_argument("--silent", action="store_true", help="纯字幕片，无音轨属正常")
    ap.add_argument("--no-audio", action="store_true", help="跳过音频削波检查")
    ap.add_argument("-o", "--out", default="qa")
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    P = json.load(open(a.plan, encoding="utf-8"))
    shots = shots_from_plan(P)
    pr = probe(a.video)

    v = next((s for s in pr["streams"] if s["codec_type"] == "video"), None)
    au = next((s for s in pr["streams"] if s["codec_type"] == "audio"), None)
    if v is None:
        sys.exit("没有视频流")

    dur = float(pr["format"]["duration"])
    fps = parse_rate(v.get("avg_frame_rate")) or parse_rate(v.get("r_frame_rate"))
    res = []

    def add(level, name, msg):
        res.append((level, name, msg))

    # 规格
    if a.size:
        want = a.size.lower().replace("×", "x").replace("*", "x")
        got = f"{v.get('width')}x{v.get('height')}"
        (add("PASS", "规格", f"{got}") if got == want
         else add("FAIL", "规格", f"分辨率 {got}，期望 {want}"))
    else:
        add("INFO", "规格", f"{v.get('width')}x{v.get('height')} @ {fps:.3f}fps" if fps else "帧率未知")
    if a.fps and fps:
        (add("PASS", "帧率", f"{fps:.3f}") if abs(fps - a.fps) < 0.01
         else add("FAIL", "帧率", f"{fps:.3f}fps，期望 {a.fps}"))

    # 时长
    planned = P.get("duration")
    if planned is None:
        planned = sum(d for _, _, d in shots)
    diff = dur - float(planned)
    if abs(diff) <= a.tol:
        add("PASS", "时长", f"{dur:.3f}s，计划 {float(planned):.3f}s，差 {diff:+.3f}s")
    else:
        add("FAIL", "时长", f"{dur:.3f}s，计划 {float(planned):.3f}s，差 {diff:+.3f}s（容差 {a.tol}s）")

    # 音轨
    if a.silent:
        add("PASS", "音轨", "声明为纯字幕片" + ("（实际有音轨）" if au else ""))
    elif au is None:
        add("FAIL", "音轨", "没有音频流；若确为纯字幕片，加 --silent")
    else:
        add("PASS", "音轨", f"{au.get('channels', '?')} 声道")

    # 黑帧
    r = run(["ffmpeg", "-v", "info", "-i", a.video, "-an",
             "-vf", "blackdetect=d=0.10:pix_th=0.10", "-f", "null", "-"])
    blacks = re.findall(r"black_start:([\d.]+)\s+black_end:([\d.]+)\s+black_duration:([\d.]+)", r.stderr)
    if blacks:
        spans = "; ".join(f"{float(s):.2f}–{float(e):.2f}s" for s, e, _ in blacks[:6])
        add("FAIL", "黑帧", f"{len(blacks)} 段非预期黑场: {spans}")
    else:
        add("PASS", "黑帧", "无 ≥0.10s 黑场")

    # 削波
    if au is not None and not a.no_audio:
        r = run(["ffmpeg", "-v", "info", "-i", a.video, "-af", "astats=metadata=1:reset=0",
                 "-vn", "-f", "null", "-"])
        peaks = re.findall(r"Peak level dB:\s*(-?[\d.]+|-inf)", r.stderr)
        nums = [float(p) for p in peaks if p not in ("-inf",)]
        if nums:
            peak = max(nums)
            (add("FAIL", "削波", f"峰值 {peak:.2f} dBFS，已达削波线") if peak >= -0.1
             else add("PASS", "削波", f"峰值 {peak:.2f} dBFS"))
        else:
            add("WARN", "削波", "读到峰值，请人工确认")

    # 出图
    def grab(t, f, w=480):
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0, t):.3f}", "-i", a.video,
             "-frames:v", "1", "-vf", f"scale={w}:-1", f])

    cells, skipped = [], 0
    for n, t, d in shots:
        tt = t + d * 0.8
        if tt >= dur - 0.05:
            skipped += 1
            continue
        f = os.path.join(a.out, f"screen{str(n).zfill(2)}.png")
        grab(tt, f)
        cells.append((f"{n} · {tt:.1f}s", f))
    for n in a.anchor:
        hit = [s for s in shots if str(s[0]) == str(n)]
        if not hit:
            add("WARN", "锚点", f"plan 里没有编号 {n}")
            continue
        t0 = hit[0][1]
        if t0 >= dur:
            continue
        grab(t0 - 1 / 30, os.path.join(a.out, f"anchor{n}-before.png"), 640)
        grab(t0 + 1 / 30, os.path.join(a.out, f"anchor{n}-after.png"), 640)

    sheets = 0
    try:
        from PIL import Image, ImageDraw
        W, H, C = 480, 270, 6
        for k in range(0, len(cells), 24):
            part = cells[k:k + 24]
            rows = (len(part) + C - 1) // C
            sheet = Image.new("RGB", (W * C, (H + 22) * rows), (30, 30, 30))
            d = ImageDraw.Draw(sheet)
            for i, (lab, f) in enumerate(part):
                x, y = (i % C) * W, (i // C) * (H + 22)
                sheet.paste(Image.open(f).resize((W, H)), (x, y + 22))
                d.text((x + 6, y + 5), lab, fill=(255, 255, 255))
            sheet.save(os.path.join(a.out, f"sheet-{k // 24 + 1}.jpg"), quality=85)
            sheets += 1
    except ImportError:
        for k in range(0, len(cells), 24):
            part = [f for _, f in cells[k:k + 24]]
            if not part:
                continue
            inputs = sum((["-i", f] for f in part), [])
            run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex",
                 f"{''.join(f'[{i}:v]' for i in range(len(part)))}concat=n={len(part)}:v=1:a=0,tile=6x4",
                 "-frames:v", "1", os.path.join(a.out, f"sheet-{k // 24 + 1}.jpg")])
            sheets += 1
    add("INFO", "出图", f"{len(cells)} 屏帧 + {sheets} 张联络表"
        + (f"，{skipped} 屏超出时长已跳过（对的是预览片？）" if skipped else "")
        + f" -> {a.out}/")

    order = {"FAIL": 0, "WARN": 1, "PASS": 2, "INFO": 3}
    res.sort(key=lambda x: order[x[0]])
    w = max(len(n) for _, n, _ in res)
    for lv, name, msg in res:
        print(f"[{lv}] {name.ljust(w)}  {msg}")
    fails = sum(1 for lv, _, _ in res if lv == "FAIL")
    warns = sum(1 for lv, _, _ in res if lv == "WARN")
    print()
    if fails:
        print(f"闸门未过：{fails} 项 FAIL" + (f"，{warns} 项 WARN" if warns else ""))
        sys.exit(1)
    print("闸门通过" + (f"（{warns} 项 WARN 需人工确认）" if warns else ""))
    print("机器过检 ≠ 可以交片：联络表要逐张看，锚点前后帧要逐对看。")


if __name__ == "__main__":
    main()
