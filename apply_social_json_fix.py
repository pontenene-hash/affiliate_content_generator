"""Safely replace only generate_social_plan in social_tools.py.

Usage: python apply_social_json_fix.py social_tools.py
Creates social_tools.py.before_json_fix.bak before modifying the source.
"""
import ast
import pathlib
import shutil
import sys
import textwrap

REPLACEMENT = '''
def generate_social_plan(client, model, article, call_llm, affiliate_url='',
                         promotion_context='アフィリエイト販売'):
    """Generate smaller JSON blocks, then normalize and validate as before."""
    import copy

    article = str(article or '')
    shared_rules = (
        'あなたは日本語の広告・SNS制作の専門家です。完成記事のみを情報源にしてください。\\n'
        '記事にない事実・口コミ・効果・価格・送料・認証・商品画像を創作しない。\\n'
        '医療・健康・美容商品の診断・治療・予防効果を断定しない。\\n'
        '検査サービスを医療機関の診断・検査の代わりと表現しない。\\n'
        '価格、送料、ステージ別性能、早期発見、特許、医療機関との比較は、'
        '一次資料を確認できない限りSNSで強調しない。\\n'
        '正式名称を変えず、自然な日本語の完結した文を使用する。\\n'
        '本文にハッシュタグを重複させず、hashtags配列へ記入する。\\n'
        'アフィリエイトは【PR】、店頭案内のみなら【商品案内】を明記。\\n'
        'X・Threads・Facebook・LINE・YouTubeには指定URLを1回、'
        'Instagram・TikTokはプロフィールへ誘導。URLを創作しない。\\n'
        '動画は音声ナレーションなし、タイピング風字幕と明るい権利確認済みBGM。\\n'
        '各sceneのnarrationは音声ではなく45文字以内の画面テロップ。\\n'
        'JSONオブジェクトだけを返し、Markdownコードフェンスや説明文を付けない。\\n'
        f'制作品質基準：{COMMON_QUALITY}\\n'
        f'販売・案内条件：{promotion_context}\\n'
        f'購入・確認URL：{affiliate_url or "未設定"}\\n'
        f'完成記事：\\n---\\n{article}\\n---\\n'
    )
    specs = (
        (
            '投稿文',
            ('x_posts', 'x_image', 'threads', 'facebook', 'line'),
            'Xは異なる切り口で3案。各SNSの投稿文と画像用の短いコピーを作成。'
            'LINEは本文を必ず作成。\\n'
            '出力JSON形式：\\n'
            '{"x_posts":[{"text":"","hashtags":["#タグ"]}],'
            '"x_image":{"title":"","body":"","visual":""},'
            '"threads":{"text":"","hashtags":["#タグ"],"image_title":"","image_body":"","visual":""},'
            '"facebook":{"text":"","hashtags":["#タグ"],"image_title":"","image_body":"","visual":""},'
            '"line":{"text":"","image_title":"","image_body":"","visual":""}}',
            6000,
        ),
        (
            'Instagramカルーセル',
            ('carousel',),
            'カルーセルは必ず9枚。表紙、読者の悩み、要点、注意点、まとめ、CTAを重複なく構成。'
            '各スライドにはtitle、body、visualを入れる。ハッシュタグは5個。\\n'
            '出力JSON形式：\\n'
            '{"carousel":{"caption":"","hashtags":["#タグ"],'
            '"slides":[{"title":"","body":"","visual":""}]}}',
            5500,
        ),
        (
            '動画',
            ('reel', 'youtube', 'tiktok'),
            'Instagramリール、YouTube、TikTokの3種類を作成。'
            'それぞれ42秒、冒頭表紙と最後のCTAを含む5〜8シーン。'
            '各シーンにscene_type、caption、narration、visualを入れる。'
            'リールのハッシュタグは5個。\\n'
            '出力JSON形式：\\n'
            '{"reel":{"caption":"","hashtags":["#タグ"],'
            '"cover_title":"","cover_body":"",'
            '"scenes":[{"scene_type":"content","caption":"","narration":"","visual":""}]},'
            '"youtube":{"title":"","description":"","hashtags":["#タグ"],'
            '"thumbnail_title":"","thumbnail_body":"",'
            '"scenes":[{"scene_type":"content","caption":"","narration":"","visual":""}]},'
            '"tiktok":{"caption":"","hashtags":["#タグ"],'
            '"cover_title":"","cover_body":"",'
            '"scenes":[{"scene_type":"content","caption":"","narration":"","visual":""}]}}',
            8500,
        ),
    )

    merged = {}
    for group_name, expected_keys, instructions, token_budget in specs:
        last_error = None
        for attempt in range(3):
            extra = (
                '\\n前回の応答はJSONとして不完全でした。必須キーをすべて含め、'
                '文を簡潔にし、有効なJSONオブジェクトのみを返してください。'
                if attempt else ''
            )
            prompt = shared_rules + '\\n【今回の生成対象】' + group_name + '\\n' + instructions + extra
            try:
                raw = call_llm(
                    client, model, prompt, token_budget,
                    response_mime_type='application/json', temperature=0.25,
                )
                part = _load_json_response(raw)
                missing = [key for key in expected_keys if key not in part]
                if missing:
                    raise ValueError('必須キー不足: ' + ', '.join(missing))
                merged.update({key: copy.deepcopy(part[key]) for key in expected_keys})
                break
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                last_error = exc
                print(
                    f'SNS {group_name} JSON再試行 {attempt + 1}/3: {str(exc)[:160]}',
                    flush=True,
                )
        else:
            raise ValueError(
                f'SNS「{group_name}」のJSON生成に失敗しました: {last_error}'
            )

    try:
        result = _normalize_social_plan(
            merged, article, promotion_context, affiliate_url
        )
        _validate_social_plan(result)
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        raise ValueError(f'SNS構成の最終検証に失敗しました: {exc}') from exc
    return result
'''


def main():
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python apply_social_json_fix.py social_tools.py')
    path = pathlib.Path(sys.argv[1])
    if not path.is_file():
        raise SystemExit(f'File not found: {path}')
    original = path.read_text(encoding='utf-8')
    tree = ast.parse(original, filename=str(path))
    functions = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == 'generate_social_plan']
    if len(functions) != 1:
        raise SystemExit('Expected exactly one generate_social_plan function; no changes made')
    new_function = textwrap.dedent(REPLACEMENT).lstrip('\n')
    ast.parse(new_function)
    lines = original.splitlines(keepends=True)
    node = functions[0]
    replacement = ''.join(lines[:node.lineno-1]) + new_function + '\n' + ''.join(lines[node.end_lineno:])
    compile(replacement, str(path), 'exec')
    if replacement == original:
        print('No changes needed')
        return
    backup = path.with_name(path.name + '.before_json_fix.bak')
    if not backup.exists():
        shutil.copy2(path, backup)
    path.write_text(replacement, encoding='utf-8')
    print(f'Updated: {path}')
    print(f'Backup: {backup}')
    print('Syntax OK; run your existing tests before regenerating creative briefs.')


if __name__ == '__main__':
    main()
