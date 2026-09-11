import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'config' / 'portable-installation-manifest.json'


def digest_bytes(value: bytes) -> str:
    return 'sha256:' + hashlib.sha256(value).hexdigest()


def canonical_digest(value) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')
    return digest_bytes(encoded)


manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
for name in ('autonomous-worker-framework', 'worker-lab'):
    component = manifest['components'][name]
    component_root = ROOT / component['root']
    if component['scope'] == 'runtime-dependency-closure':
        files = tuple(component['files'])
    elif component['scope'] == 'python-production-tree':
        production = component_root / component['production_root']
        files = tuple(sorted(
            p.relative_to(component_root).as_posix()
            for p in production.rglob('*.py')
            if '__pycache__' not in p.parts
        ))
    else:
        raise SystemExit(f'unsupported scope for {name}')
    entries = [
        {'path': relative, 'sha256': digest_bytes((component_root / relative).read_bytes())}
        for relative in files
    ]
    component['digest'] = canonical_digest(entries)
    print(name, len(files), component['digest'])

MANIFEST.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
