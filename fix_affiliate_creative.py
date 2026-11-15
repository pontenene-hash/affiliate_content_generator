#!/usr/bin/env python3
"""SNS投稿文の安全な後処理（元ZIPは変更しない）。

使い方:
  python fix_affiliate_creative.py affiliate-creative-prompts-29.zip
  python fix_affiliate_creative.py input.zip --output output-fixed.zip

修正対象: social_posts.md と all_prompts.json 内の social_plan の投稿文。
画像・動画プロンプト、GBP、記事、WordPressデータは変更しない。
価格や医療効果の事実確認を行うプログラムではない。
"""
import argparse
import json
import re
import zipfile
from pathlib import Path

URL_RE = re.compile(r'https?://[^\s<>「」『』"\']+')

def clean_text(value, *, long_name='', short_name=''):
    if not isinstance(value, str) or not value:
        return value
    text = value.replace('\r\n', '\n')
    if long_name and short_name and long_name != short_name:
        text = text.replace(long_name, short_name)
    # URL のクエリ部分だけが次の行に送られた場合を結合する。
    text = re.sub(r'(https?://[^\s]+\?)\s*\n\s*([A-Za-z0-9_]+=[A-Za-z0-9_+%&=.-]+)', r'\1\2', text)
    # 同じURLが隣接して2回出ている場合のみ重複を除去。
    text = re.sub(r'(https?://[^\s]+)(?:[ \t]*\n[ \t]*\1)+', r'\1', text)
    # 「詳細はこちら URL」の直後に同じURLが再掲される場合。
    lines = text.split('\n')
    out = []
    for line in lines:
        match = URL_RE.search(line)
        if out and match and line.strip() == match.group(0):
            prev = URL_RE.search(out[-1])
            if prev and prev.group(0) == match.group(0):
                continue
        out.append(line)
    return '\n'.join(out)

def short_product_name(name):
    # 商品名の【...】表記がある場合だけ短縮。任意の名前を推測しない。
    hits = re.findall(r'【([^【】]+)】', name or '')
    return hits[-1].strip() if hits else (name or '').strip()

def clean_social_plan(plan, long_name, short_name):
    if not isinstance(plan, dict):
        return plan
    # 画像・動画制作指示、シーン、ハッシュタグ等は変更しない。
    def walk(value, key=''):
        if isinstance(value, dict):
            return {k: (clean_text(v, long_name=long_name, short_name=short_name)
                        if k in ('text', 'caption', 'description') and isinstance(v, str)
                        else walk(v, k)) for k, v in value.items()}
        if isinstance(value, list):
            return [walk(x, key) for x in value]
        return value
    return {k: (v if k == 'creative_prompts' else walk(v, k)) for k, v in plan.items()}

def process_zip(source, output):
    if source.resolve() == output.resolve():
        raise ValueError('出力先は入力ZIPとは別名にしてください')
    changes = []
    with zipfile.ZipFile(source, 'r') as src, zipfile.ZipFile(output, 'w') as dst:
        names = src.namelist()
        json_names = [n for n in names if n.endswith('/all_prompts.json') or n == 'all_prompts.json']
        info = {}
        for n in json_names:
            obj = json.loads(src.read(n).decode('utf-8'))
            long_name = obj.get('product_name', '')
            info[n.rsplit('/', 1)[0]] = (long_name, short_product_name(long_name))
        for member in src.infolist():
            raw = src.read(member.filename)
            folder = member.filename.rsplit('/', 1)[0] if '/' in member.filename else ''
            long_name, short_name = info.get(folder, ('', ''))
            if member.filename.endswith('social_posts.md'):
                updated = clean_text(raw.decode('utf-8'), long_name=long_name, short_name=short_name).encode('utf-8')
            elif member.filename in json_names:
                obj = json.loads(raw.decode('utf-8'))
                obj['social_plan'] = clean_social_plan(obj.get('social_plan'), long_name, short_name)
                updated = json.dumps(obj, ensure_ascii=False, indent=2).encode('utf-8')
            else:
                updated = raw
            if updated != raw:
                changes.append(member.filename)
            dst.writestr(member, updated)
    return changes

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path, help='元の制作プロンプトZIP')
    parser.add_argument('--output', type=Path, help='出力ZIP（省略時は -fixed.zip）')
    args = parser.parse_args()
    target = args.output or args.input.with_name(args.input.stem + '-fixed.zip')
    changed = process_zip(args.input, target)
    print('保存先:', target)
    print('修正ファイル:', ', '.join(changed) if changed else 'なし')
    print('注意: 価格・医療効果・広告表示の事実確認は別途必要です。')

if __name__ == '__main__':
    main()
