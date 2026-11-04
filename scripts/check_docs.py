"""Check local documentation targets and the committed media inventory."""
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def main():
    errors = []
    checked = 0
    for path in [*ROOT.glob('*.md'), *ROOT.glob('research/*.md')]:
        content = re.sub(r'```.*?```', '', path.read_text(encoding='utf-8'), flags=re.S)
        targets = re.findall(r'!?\[[^\]\n]*\]\(([^)\s]+)', content)
        targets += re.findall(r'(?:src|href)="([^"]+)"', content)
        for target in targets:
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            local = path.parent / unquote(parsed.path)
            checked += 1
            if not local.is_file():
                errors.append(f'{path.relative_to(ROOT)}: missing {target}')
    inventory = json.loads((ROOT / 'assets/media-manifest.json').read_text(encoding='utf-8'))
    for entry in inventory['files']:
        path = ROOT / entry['path']
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
            errors.append(f'Media inventory mismatch: {entry["path"]}')
    if errors:
        raise SystemExit('\n'.join(errors))
    print(f'{checked} local documentation links and {len(inventory["files"])} media hashes verified')


if __name__ == '__main__':
    main()
