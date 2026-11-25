"""Deterministic editorial normalization; never establishes factual verification."""
import re


def display_name(name):
    name = str(name).strip()
    bracketed = re.findall(r'【([^】]+)】', name)
    if len(bracketed) == 1 and 2 <= len(bracketed[0]) <= 40:
        return bracketed[0].strip()
    return name


def polish(md, original, name):
    # Preserve URLs and HTML attributes, including publisher-issued tracking codes.
    parts = re.split(r'(https?://[^\s<>]+|<[^>]+>)', md)
    for i in range(0, len(parts), 2):
        if original and original != name:
            parts[i] = parts[i].replace(original, name)
        parts[i] = parts[i].replace('確認するのがの手間', '確認するのが手間')
    md = ''.join(parts)
    # No verified testimonials are supplied by the current pipeline.
    md = re.sub(r'^#\s+([^\n]*(?:口コミ|評判|体験談|レビュー)[^\n]*)$',
                lambda m: '# ' + name + 'の特徴・選び方と利用前の注意点', md, flags=re.M)
    # Remove only identical prose paragraphs, never headings, lists or ads.
    seen = set(); out = []
    for block in re.split(r'\n\s*\n', md.strip()):
        key = re.sub(r'\s+', '', block)
        prose = len(key) >= 80 and not re.search(r'(?m)^\s*(?:#|[-*]|\d+[.、]|[|<\[])', block) and 'http' not in block
        if prose and key in seen:
            continue
        if prose: seen.add(key)
        out.append(block)
    return '\n\n'.join(out) + '\n'
