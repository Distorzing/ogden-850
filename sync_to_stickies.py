#!/usr/bin/env python3
"""
Ogden Basic English 850 — 每日桌面便笺 (Stickies)
从 Excel 学习表读取数据，生成今日单词便笺，直接写入 macOS Stickies 数据目录。
"""

import json
import os
import uuid
import plistlib
import datetime
import shutil
import subprocess
import re

# ── 路径 ────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(SCRIPT_DIR, 'words_data.json')
PLAN_FILE = os.path.join(SCRIPT_DIR, 'plan_data.json')
STICKIES_DIR = os.path.expanduser(
    '~/Library/Containers/com.apple.Stickies/Data/Library/Stickies'
)
SAVED_STATE = os.path.join(STICKIES_DIR, '.SavedStickiesState')

START_DATE = datetime.date(2026, 6, 11)

# ── 工具函数 ────────────────────────────────────────────

def load_json(path):
    with open(path) as f:
        return json.load(f)

def parse_range(s):
    if not s or '无' in s:
        return []
    result = []
    for part in s.split('；'):
        part = part.strip()
        m = re.match(r'(\d+)-(\d+)', part)
        if m:
            start, end = int(m.group(1)), int(m.group(2))
            result.extend(range(start, end + 1))
    return result

def parse_review_range(s):
    if not s or '无' in s:
        return []
    return [int(m) for m in re.findall(r'第(\d+)天', s)]

def get_study_day(today=None):
    if today is None:
        today = datetime.date.today()
    diff = (today - START_DATE).days
    if diff < 0:
        return -1
    return diff + 1

def get_words_by_day(plan_data, words_data, day_num):
    plan = next((p for p in plan_data if p['day'] == day_num), None)
    if not plan:
        return []
    indices = parse_range(plan['new_range'])
    return [words_data[i - 1] for i in indices if 1 <= i <= len(words_data)]

def get_review_words(plan_data, words_data, day_num):
    plan = next((p for p in plan_data if p['day'] == day_num), None)
    if not plan:
        return []
    review_days = parse_review_range(plan['review_range'])
    all_words = []
    for d in review_days:
        all_words.extend(get_words_by_day(plan_data, words_data, d))
    return all_words


# ── RTF 生成 ─────────────────────────────────────────────

def rtf_escape(text):
    """转义 RTF 特殊字符"""
    text = text.replace('\\', '\\\\')
    text = text.replace('{', '\\{')
    text = text.replace('}', '\\}')
    # Unicode 字符处理 - 中文等需要转成 \uXXXX 格式
    result = []
    for ch in text:
        code = ord(ch)
        if code < 128:
            result.append(ch)
        elif code <= 0xFFFF:
            # Use \'XX hex encoding for RTF
            result.append(f"\\u{code}?")
        else:
            # Surrogate pair for characters above BMP
            result.append(f"\\u{code - 0x10000}?")
    return ''.join(result)

def generate_rtf(new_words, review_words, day_num, today):
    """生成 RTF 格式的便笺内容"""

    total_learned = min(day_num * 25, 850)
    pct = round(total_learned / 850 * 100)
    date_str = today.strftime('%Y年%m月%d日 %A')

    def esc(t):
        return rtf_escape(str(t))

    lines = []
    # Title
    lines.append(r"{\rtf1\ansi\ansicpg936\cocoartf2900")
    lines.append(r"{\fonttbl\f0\fnil\fcharset134 PingFang SC;}")
    lines.append(r"{\colortbl;\red255\green255\blue255;\red50\green50\blue50;\red100\green100\blue100;\red41\green98\blue199;\red200\green120\blue30;}")
    lines.append(r"\f0\fs40\b")
    lines.append(esc(f"📖 每日背词 | {date_str} | Day {day_num}/30"))
    lines.append(r"\b0\fs26")
    lines.append(r"\line")
    lines.append(esc(f"📊 总进度 {pct}% | 🆕 新词 {len(new_words)} 个 | 🔄 复习 {len(review_words)} 个"))
    lines.append(r"\line\line")

    # New words
    lines.append(r"\fs30\b\cf4 " + esc(f"🆕 今日新词 ({len(new_words)} 词)") + r"\b0\cf2\fs26")
    lines.append(r"\line")
    for w in new_words:
        eng = esc(w['单词'])
        pho = esc(w['音标'])
        chn = esc(w['中文翻译'])
        ex = esc(w.get('使用例句', ''))
        lines.append(r"\line\b " + f"{eng}" + r"\b0  " + f"{pho}  {chn}")
        if ex:
            lines.append(r"\line\i\fs22\cf3 " + f"     {ex}" + r"\i0\fs26\cf2")
    lines.append(r"\line")

    # Review words
    if review_words:
        max_display = 100
        display = review_words[:max_display]
        lines.append(r"\line\fs30\b\cf4 " + esc(f"🔄 今日复习 ({len(display)} 词)") + r"\b0\cf2\fs26")
        if len(review_words) > max_display:
            lines.append(r"\line\fs22\cf3 " + esc(f"（显示前 {max_display} 个，共 {len(review_words)} 个）") + r"\fs26\cf2")
        lines.append(r"\line")
        for w in display:
            eng = esc(w['单词'])
            chn = esc(w['中文翻译'])
            pho = esc(w['音标'])
            lines.append(r"\line\b " + f"{eng}" + r"\b0  " + f"{pho}  {chn}")
    lines.append(r"\line")

    # Method tips
    lines.append(r"\line\fs22\cf3")
    lines.append(esc("💡 1.遮住英文看中文回忆 2.朗读例句 3.自己造句 4.标模糊词"))
    lines.append(r"\fs26\cf2")

    lines.append(r"}")

    return ''.join(lines)


# ── Stickies 写入 ────────────────────────────────────────

def kill_stickies():
    """退出 Stickies 以便安全写入"""
    subprocess.run(['osascript', '-e',
        'tell application "Stickies" to quit'], capture_output=True)
    # 等它退出
    import time
    time.sleep(1)

def launch_stickies():
    """重新打开 Stickies"""
    subprocess.Popen(['open', '-a', 'Stickies'])

def write_sticky(rtf_content):
    """写入一条新便笺到 Stickies 数据目录"""
    os.makedirs(STICKIES_DIR, exist_ok=True)

    # 固定 UUID，确保每天只更新同一条便笺，不堆积
    note_uuid = "OGDEN-DAILY-WORDS-2026"
    rtfd_dir = os.path.join(STICKIES_DIR, f'{note_uuid}.rtfd')
    os.makedirs(rtfd_dir, exist_ok=True)

    # 写 RTF 文件
    rtf_path = os.path.join(rtfd_dir, 'TXT.rtf')
    with open(rtf_path, 'w', encoding='utf-8') as f:
        f.write(rtf_content)

    # 更新 SavedStickiesState
    state = []
    if os.path.exists(SAVED_STATE):
        try:
            with open(SAVED_STATE, 'rb') as f:
                state = plistlib.load(f)
        except Exception:
            state = []

    # 移除旧的每日单词便笺（同 UUID）
    state = [e for e in state if e.get('UUID') != note_uuid]

    # 固定位置：桌面左上角

    new_entry = {
        'UUID': note_uuid,
        'Frame': '{{20, 600}, {420, 700}}',
        'Floating': True,  # 始终在最前
        'Translucent': False,
        'SpellCheckingTypes': 9191,
        'ControlColor': {'Red': 0.996, 'Green': 0.957, 'Blue': 0.612, 'Alpha': 1.0},
        'StickyColor': {'Red': 0.996, 'Green': 0.957, 'Blue': 0.612, 'Alpha': 1.0},
        'SpineColor': {'Red': 0.996, 'Green': 0.918, 'Blue': 0.239, 'Alpha': 1.0},
        'HighlightColor': {'Red': 0.737, 'Green': 0.663, 'Blue': 0.008, 'Alpha': 1.0},
    }

    # Remove old "ogden" notes if any, add new
    state.append(new_entry)

    with open(SAVED_STATE, 'wb') as f:
        plistlib.dump(state, f)

    return note_uuid


def clean_old_ogden_stickies():
    """清理旧的不含内容的便笺文件"""
    if not os.path.exists(STICKIES_DIR):
        return
    # 简单清理：如果目录超过20个rtfd，删最旧的
    rtfd_dirs = sorted([
        d for d in os.listdir(STICKIES_DIR)
        if d.endswith('.rtfd')
    ])
    # 读取 state 文件中的 UUID 列表
    valid_uuids = set()
    if os.path.exists(SAVED_STATE):
        try:
            with open(SAVED_STATE, 'rb') as f:
                state = plistlib.load(f)
            valid_uuids = {e['UUID'] for e in state}
        except Exception:
            pass

    for d in rtfd_dirs:
        uuid_part = d.replace('.rtfd', '')
        if uuid_part not in valid_uuids:
            path = os.path.join(STICKIES_DIR, d)
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)


# ── 主流程 ──────────────────────────────────────────────

def main():
    today = datetime.date.today()
    day_num = get_study_day(today)

    if day_num < 1:
        print("学习计划尚未开始（2026-06-11 起）")
        return

    if day_num > 34:
        # 30天计划结束，循环复习
        day_num = ((day_num - 1) % 30) + 1
        print(f"30 天计划已结束，循环模式对应 Day {day_num}")

    plan_data = load_json(PLAN_FILE)
    words_data = load_json(DATA_FILE)

    new_words = get_words_by_day(plan_data, words_data, day_num)
    review_words = get_review_words(plan_data, words_data, day_num)
    # 去重：新词和复习词不重复
    new_ids = {w['学习顺序'] for w in new_words}
    review_words = [w for w in review_words if w['学习顺序'] not in new_ids]

    print(f"📅 {today} | Day {day_num} | 🆕 {len(new_words)} 新词 | 🔄 {len(review_words)} 复习词")

    # 生成 RTF
    rtf = generate_rtf(new_words, review_words, day_num, today)

    # 写入便笺
    print("正在退出 Stickies...")
    kill_stickies()
    clean_old_ogden_stickies()
    note_uuid = write_sticky(rtf)
    print(f"✅ 已创建便笺: {note_uuid}")
    print("正在重启 Stickies...")
    launch_stickies()

    print("\n🎉 完成！桌面便笺已更新，查看今天的单词吧。")

if __name__ == '__main__':
    main()
