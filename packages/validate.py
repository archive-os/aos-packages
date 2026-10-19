#!/usr/bin/env python3
"""Validate the complete local catalog before publication; makes no network calls."""
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent

def read(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))

def local_file(value):
    path = (ROOT / value).resolve()
    if not path.is_relative_to(ROOT) or not path.is_file():
        raise ValueError(f'Missing or unsafe path: {value}')
    return path

def validate():
    from PIL import Image
    catalog, logos, shots = (read(n) for n in ('packages.json', 'logos.json', 'screenshots.json'))
    packages = catalog['packages']
    assert catalog['schema_version'] == logos['schema_version'] == shots['schema_version'] == 1
    assert len(packages) == len({p['package'] for p in packages})
    keys = {p['package'] for p in packages}
    assert keys == set(logos['logos']) == set(shots['screenshots']), 'Media keys must match package names'
    repository = read('repository.json')['repository']
    prefix=read('repository.json').get('path','')
    assert prefix in ('','packages')
    for item in packages:
        deb = local_file('release-assets/' + item['asset'])
        assert item['size'] == deb.stat().st_size
        assert item['sha256'] == hashlib.sha256(deb.read_bytes()).hexdigest(), deb.name
        for field, key in [('Package', 'package'), ('Version', 'version'), ('Architecture', 'architecture')]:
            actual = subprocess.check_output(['dpkg-deb', '-f', str(deb), field], text=True).strip()
            assert actual == item[key], (deb.name, field)
        if repository:
            from urllib.parse import quote
            release='https://github.com/'+repository+'/releases/download/'+quote(catalog['release_tag'],safe='')+'/'+quote(item['asset'],safe='')
            raw='https://raw.githubusercontent.com/'+repository+'/main/'+(prefix+'/' if prefix else '')+'release-assets/'+quote(item['asset'],safe='')
            assert item['deb_url'] in (release,raw), 'Wrong DEB download address'
        else:
            assert item['deb_url'] is None, 'Repository has not been configured'
        logo = local_file(logos['logos'][item['package']])
        assert logo.stem == item['package']
        if logo.suffix == '.svg':
            assert ET.parse(logo).getroot().tag.endswith('svg')
        else:
            with Image.open(logo) as image: image.verify()
        assert shots['screenshots'][item['package']], item['package']
        for path in shots['screenshots'][item['package']]:
            assert Path(path).parts[:2] == ('screenshots', item['package'])
            with Image.open(local_file(path)) as image:
                assert image.width >= 500 and image.height >= 300
                image.verify()
    print(f'PASS: {len(packages)} DEBs, metadata, SHA256, logos and screenshots; repository={repository or "pending"}')
    return catalog

if __name__ == '__main__':
    validate()
