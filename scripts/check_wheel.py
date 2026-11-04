"""Install the built wheel outside the checkout and verify its public resources."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile


def main():
    wheels = list(Path(sys.argv[1]).resolve().glob('ontology_review-*.whl'))
    if len(wheels) != 1:
        raise SystemExit('Expected exactly one ontology_review wheel')
    wheel = wheels[0]
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        for ending in ['licenses/LICENSE', 'licenses/NOTICE.md', 'design/LICENSE.open-props', 'design/LICENSE.lucide']:
            assert any(name.endswith(ending) for name in names), ending
    with tempfile.TemporaryDirectory(prefix='ontology-review-wheel-') as temporary:
        root = Path(temporary)
        target = root / 'installed'
        subprocess.run([sys.executable, '-m', 'pip', 'install', '--no-deps', '--target', str(target), str(wheel)], check=True)
        env = dict(os.environ, PYTHONPATH=str(target), PYTHONUTF8='1')
        code = '''
from importlib import metadata, resources
from pathlib import Path
import sys
import evidence_wiki
assert Path(evidence_wiki.__file__).is_relative_to(Path(sys.argv[1]))
assert metadata.version('ontology-review') == '0.2.0'
entries = {entry.name for entry in metadata.distribution('ontology-review').entry_points}
assert {'ontology-review', 'evidence-wiki'} <= entries
package = resources.files('evidence_wiki')
for name in ['web/workbench.html', 'web/workbench.js', 'web/workbench.css', 'web/example.json', 'design/open-props.css', 'design/LICENSE.open-props', 'design/LICENSE.lucide']:
    assert package.joinpath(name).is_file(), name
assert 'ONTOLOGY REVIEW' in package.joinpath('web/workbench.html').read_text(encoding='utf-8')
print('Installed module, CLI entry points, web assets and licenses verified')
'''
        subprocess.run([sys.executable, '-c', code, str(target)], cwd=root, env=env, check=True)
        subprocess.run([sys.executable, '-m', 'evidence_wiki', '--help'], cwd=root, env=env, check=True, stdout=subprocess.DEVNULL)
    print(json.dumps({'wheel': wheel.name, 'installed_check': 'passed'}))


if __name__ == '__main__':
    main()
