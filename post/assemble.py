#!/usr/bin/env python3
"""桌面女友短片后期合成：拼接 + 男声画外音 + 逐字字幕(ASS \\k) + 实时波形条。
用法: python post/assemble.py [--skip-sub] [--skip-wave]
依赖: ffmpeg(带 libass)、ComfyUI/output/video/clip*_*.mp4、post/male*.mp3
"""
import json, re, subprocess, sys, glob, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VOD = ROOT / "ComfyUI/output/video"
POST = ROOT / "post"
WORK = POST / "work"
WORK.mkdir(exist_ok=True)

# 每个 clip 的女台词（按出现顺序）；windows 为字幕时间窗(clip内秒)，None=自动检测
CLIP_LINES = {
    "clip1": [("说吧……今天想看什么？", None)],
    "clip2": [("好，等我一下。", (1.6, 3.9))],
    "clip4": [("噔噔～我回来了，老公，怎么样？", (0.75, 4.4))],
    "clip5": [("等等～还有一套。", (0.6, 2.1))],
    "clip6": [("这套呢？", (1.3, 3.2))],
    "clip7": [("机会用完啦。老公想留哪套呢？", (1.2, 4.5))],
}
# 男声画外音：(clip名, clip内偏移秒, 音频文件, 文本) — 位置按剧本时间轴，须避开女主台词段
MALE_LINES = [
    ("clip2", 0.1, "male1.mp3", "想看JK。"),
    ("clip4", 4.5, "male2.mp3", "嗯，不错。"),
    ("clip6", 4.2, "male3.mp3", "这套也好看。"),
]
CLIP_ORDER = ["clip1", "clip2", "clip3", "clip4", "clip5", "clip6", "clip7"]


def sh(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.returncode != 0:
        print("CMD FAIL:", cmd, "\n", r.stderr[-800:])
        sys.exit(1)
    return r.stdout


def find_clip(name):
    hits = sorted(glob.glob(str(VOD / f"{name}_*.mp4")) + glob.glob(str(VOD / f"{name}t_*.mp4")))
    return hits[-1] if hits else None


def duration(f):
    out = sh(f"ffprobe -v error -show_entries format=duration -of csv=p=0 '{f}'")
    return float(out.strip())


def speech_segments(f, min_sil=0.35, thr=-35):
    """silencedetect 取反 → 合并近邻段 → 语音段列表[(start,end)]（按时长降序）"""
    err = subprocess.run(f"ffmpeg -i '{f}' -af silencedetect=noise={thr}dB:d={min_sil} -f null -",
                         shell=True, capture_output=True, text=True).stderr
    sil = [(float(a), float(b)) for a, b in
           re.findall(r"silence_start: ([\d.]+).*?silence_end: ([\d.]+)", err, re.S)]
    dur = duration(f)
    segs, cur = [], 0.0
    for a, b in sil:
        if a - cur > 0.25:
            segs.append([cur, a])
        cur = b
    if dur - cur > 0.25:
        segs.append([cur, dur])
    # 合并间隔 <1.2s 的段（同一句台词中间的停顿）
    merged = []
    for s in segs:
        if merged and s[0] - merged[-1][1] < 1.2:
            merged[-1][1] = s[1]
        else:
            merged.append(s)
    return sorted([tuple(s) for s in merged if s[1] - s[0] > 0.4], key=lambda s: -(s[1] - s[0]))


def cs(t):
    return int(t * 100)  # ASS 厘秒


def build_ass(events, path, w=1280, h=736):
    """events: [(t0,t1,text,who)] who: F/M。逐字出现用 \\k，颜色按说话者。"""
    hdr = f"""[Script Info]
PlayResX: {w}
PlayResY: {h}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: F,Noto Sans CJK SC,36,&H00E8B9F2,&H00E8B9F2,&H80202020,&H00000000,0,0,0,0,100,100,1,0,1,1.2,1,1,60,20,300,1
Style: M,Noto Sans CJK SC,36,&H00FFFFFF,&H00FFFFFF,&H80202020,&H00000000,0,0,0,0,100,100,1,0,1,1.2,1,1,60,20,300,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    def ts(t):
        h, m, s = int(t // 3600), int(t % 3600 // 60), t % 60
        return f"{h}:{m:02d}:{s:05.2f}"
    lines = [hdr]
    for t0, t1, text, who in events:
        n = max(len(text), 1)
        per = cs(t1 - t0) / n
        icon = "◉ " if who == "F" else "◈ "
        body = "".join(f"{{\\k{int(per)}}}{c}" for c in text)
        lines.append(f"Dialogue: 0,{ts(t0)},{ts(t1)},{who},,0,0,0,,{icon}{body}\n")
    Path(path).write_text("".join(lines), encoding="utf-8")


def main():
    skip_sub, skip_wave = "--skip-sub" in sys.argv, "--skip-wave" in sys.argv

    # 1) 拼接（统一重编码）
    clips = []
    for name in CLIP_ORDER:
        f = find_clip(name)
        assert f, f"缺 clip: {name}"
        clips.append((name, f))
        print(f"{name}: {Path(f).name} ({duration(f):.2f}s)")
    lst = WORK / "concat.txt"
    lst.write_text("".join(f"file '{f}'\n" for _, f in clips))
    base = WORK / "base.mp4"
    sh(f"ffmpeg -y -f concat -safe 0 -i {lst} -c:v libx264 -crf 18 -preset fast -c:a aac -b:a 160k {base}")

    # 2) 女台词时间段（自动检测语音段，按序匹配）
    offsets, t = {}, 0.0
    events = []
    for name, f in clips:
        offsets[name] = t
        t += duration(f)
    for name, f in clips:
        lines = CLIP_LINES.get(name, [])
        if not lines:
            continue
        segs = speech_segments(f)
        print(f"{name} 语音段: {[(round(a,2), round(b,2)) for a,b in segs]} → 台词 {len(lines)} 条")
        for i, (text, window) in enumerate(lines):
            if window is not None:
                a, b = window
            elif i < len(segs):
                a, b = segs[i]
            else:
                a, b = 0.8 + i * 2.0, 0.8 + i * 2.0 + min(2.2, 0.55 * len(text))
            events.append((offsets[name] + a, offsets[name] + b + 0.3, text, "F"))

    # 3) 男声画外音混音
    total = duration(base)
    mixed = WORK / "mixed.m4a"
    inputs = f"-i {base}"
    filter_parts, idx = [], 1
    for name, off, mf, text in MALE_LINES:
        at = offsets[name] + off
        inputs += f" -i {POST / mf}"
        # 去除首尾静音，避免压到女主台词
        filter_parts.append(
            f"[{idx}:a]silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,"
            f"areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,areverse,"
            f"adelay={int(at*1000)}|{int(at*1000)},apad[a{idx}]")
        idx += 1
        events.append((at, at + 1.5, text, "M"))
    pad = "".join(f"[a{i}]" for i in range(1, idx))
    filter_parts.append(f"[0:a]{pad}amix=inputs={idx}:normalize=0,atrim=0:{total}[aout]")
    sh(f"ffmpeg -y {inputs} -filter_complex \"{';'.join(filter_parts)}\" -map \"[aout]\" -c:a aac -b:a 160k {mixed}")

    # 4) 字幕 + 波形
    events.sort()
    ass = WORK / "subs.ass"
    build_ass(events, ass)
    filters = f"ass={ass}" if not skip_sub else "copy"
    if not skip_wave:
        # 波形条：跟随最终混音实时跳动，白、细、位于左下（字幕下方）
        wave = (f"[1:a]showwaves=s=520x56:mode=line:rate=25:colors=0xC8C8C8@0.85[w];"
                f"[0:v][w]overlay=60:H-140[v0];[v0]subtitles={ass}:fontsdir=/usr/share/fonts[v]")
        sh(f"ffmpeg -y -i {base} -i {mixed} -filter_complex \"{wave}\" "
           f"-map \"[v]\" -map 1:a -c:v libx264 -crf 18 -preset fast -c:a aac -b:a 160k -pix_fmt yuv420p {POST}/final.mp4")
    else:
        sh(f"ffmpeg -y -i {base} -i {mixed} -vf \"subtitles={ass}:fontsdir=/usr/share/fonts\" -c:v libx264 -crf 18 -preset fast -c:a copy {POST}/final.mp4")
    print(f"DONE -> {POST}/final.mp4")


if __name__ == "__main__":
    main()
