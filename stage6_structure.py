import re

def merge_faq(md):
    """Move all explicit FAQ sections together without dropping their content."""
    chunks = re.split(r'(?m)(?=^##\s+)', md)
    faq, rest = [], []
    for chunk in chunks:
        head, _, body = chunk.partition('\n')
        if re.match(r'^##\s+.*(?:FAQ|よくある質問)', head, re.I):
            faq.append(body.strip())
        else:
            rest.append(chunk)
    if len(faq) < 2:
        return md
    pos = next((i for i,c in enumerate(rest) if re.match(r'^##\s+まとめ',c)),len(rest))
    rest.insert(pos,'## よくある質問（FAQ）\n\n'+'\n\n'.join(faq)+'\n\n')
    return ''.join(rest)
