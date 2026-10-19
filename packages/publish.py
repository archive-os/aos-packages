#!/usr/bin/env python3
"""Bind a repository URL, push catalog/media and upload DEBs to GitHub Releases."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from urllib.parse import quote
from validate import ROOT, read, validate
PREFIX = read('repository.json').get('path','')
if PREFIX not in ('','packages'):raise ValueError('Invalid repository directory')
PROJECT = ROOT.parent if PREFIX and ROOT.name==PREFIX else ROOT
CHECKOUT = PROJECT

def run(*args, capture=False):
    return subprocess.run(list(args), cwd=CHECKOUT if args[0]=='git' else ROOT, check=True, text=True,
                          stdout=subprocess.PIPE if capture else None).stdout

def write(name, data):
    (ROOT/name).write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def main():
    global CHECKOUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repository', nargs='?', help='https://github.com/OWNER/aos-packages or OWNER/aos-packages')
    parser.add_argument('--check', action='store_true', help='Validate only; never connects or publishes')
    parser.add_argument('--prepare', action='store_true', help='Bind download URLs locally without connecting or publishing')
    args = parser.parse_args()
    catalog = validate()
    if args.check:
        return
    if not args.repository:
        parser.error('Repository URL is required unless --check is given')
    repo = args.repository.removeprefix('https://github.com/').removesuffix('/').removesuffix('.git')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]*/aos-packages', repo):
        parser.error('Expected OWNER/aos-packages')
    config=read('repository.json')
    if config['repository'] not in (None,repo):raise SystemExit('Catalog is already bound to another repository')
    def bind(owner):
        for item in catalog['packages']:
            item['deb_url']=(f'https://raw.githubusercontent.com/{owner}/main/'+(PREFIX+'/' if PREFIX else '')+f'release-assets/{quote(item["asset"],safe="")}'
                if catalog.get('distribution')=='repository' else
                f'https://github.com/{owner}/releases/download/{quote(catalog["release_tag"],safe="")}/{quote(item["asset"],safe="")}')
        config['repository']=owner;write('packages.json',catalog);write('repository.json',config);validate()
    if args.prepare:
        bind(repo);print('Prepared locally: https://github.com/'+repo);return
    for executable in ('git', 'gh'):
        if not shutil.which(executable):raise SystemExit(f'Missing command: {executable}')
    run('gh', 'auth', 'status')
    actual = json.loads(run('gh','repo','view',repo,'--json','nameWithOwner,isPrivate',capture=True))
    if actual['isPrivate']:raise SystemExit('The Store needs a public repository; repository is private.')
    if actual['nameWithOwner'].lower() != repo.lower():raise SystemExit('Repository mismatch')
    repo = actual['nameWithOwner']
    remote = 'https://github.com/'+repo+'.git'
    if (PROJECT/'.git').exists():
        origin = run('git','remote','get-url','origin',capture=True).strip()
        if origin != remote:raise SystemExit('Existing Git remote does not match')
    else:
        if run('git','ls-remote',remote,capture=True).strip():
            temporary=tempfile.TemporaryDirectory(prefix='aos-packages-publish-')
            checkout=Path(temporary.name)/'repository'
            subprocess.run(['git','clone','--branch','main',remote,str(checkout)],cwd=ROOT,check=True)
            CHECKOUT=checkout
        else:
            run('git','init','-b','main')
            run('git','remote','add','origin',remote)
    tag = catalog['release_tag']
    bind(repo)
    tracked=['packages.json','logos.json','screenshots.json','repository.json',
             'logos','screenshots','.gitignore','README.md','publish.py','validate.py']
    if catalog.get('distribution')=='repository':tracked.append('release-assets')
    destination=CHECKOUT/PREFIX if PREFIX else CHECKOUT
    destination.mkdir(parents=True,exist_ok=True)
    if destination!=ROOT:
        for name in tracked:
            source=ROOT/name;target=destination/name
            if source.is_dir():shutil.copytree(source,target,dirs_exist_ok=True)
            else:shutil.copy2(source,target)
    run('gh','auth','setup-git')
    run('git','status','--short')
    def tracked_path(name):return (PREFIX+'/' if PREFIX else '')+name
    run('git','add','--',*[tracked_path(name) for name in tracked if name!='release-assets'])
    if catalog.get('distribution')=='repository':run('git','add','-f','--',tracked_path('release-assets'))
    if subprocess.run(['git','diff','--cached','--quiet'],cwd=CHECKOUT).returncode:
        run('git','commit','-m','Publish ArchiveOS application catalog and media')
    run('git','push','-u','origin','main')
    if catalog.get('distribution')=='repository':
        commit=run('git','rev-parse','HEAD',capture=True).strip()
        remote_head=run('git','ls-remote',remote,'refs/heads/main',capture=True).split()
        if not remote_head or remote_head[0]!=commit:raise SystemExit('Remote commit verification failed')
        for item in catalog['packages']:
            content=subprocess.check_output(['git','show',commit+':'+tracked_path('release-assets')+'/'+item['asset']],cwd=CHECKOUT)
            if hashlib.sha256(content).hexdigest()!=item['sha256']:raise SystemExit('Published DEB checksum mismatch')
        print('Published catalog, media and 8 DEBs: https://github.com/'+repo)
        return
    existing = subprocess.run(['gh','release','view',tag,'--repo',repo,'--json','tagName'],cwd=ROOT,
                              text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if existing.returncode:
        run('gh','release','create',tag,'--repo',repo,'--target','main','--draft',
            '--title','ArchiveOS application packages','--notes',
            'ArchiveOS DEB packages. Versions, architectures and SHA256 values: packages.json.')
    remote_assets=json.loads(run('gh','release','view',tag,'--repo',repo,'--json','assets',capture=True))['assets']
    by_name={asset['name']:asset for asset in remote_assets}
    for item in catalog['packages']:
        previous=by_name.get(item['asset'])
        if previous:
            # Do not silently replace an already published binary.
            with __import__('tempfile').TemporaryDirectory() as tmp:
                run('gh','release','download',tag,'--repo',repo,'--pattern',item['asset'],'--dir',tmp)
                if hashlib.sha256((Path(tmp)/item['asset']).read_bytes()).hexdigest()!=item['sha256']:
                    raise SystemExit('Existing release asset differs: '+item['asset'])
        else:
            run('gh','release','upload',tag,str(ROOT/'release-assets'/item['asset']),'--repo',repo)
    remote_assets=json.loads(run('gh','release','view',tag,'--repo',repo,'--json','assets',capture=True))['assets']
    by_name={asset['name']:asset for asset in remote_assets}
    for item in catalog['packages']:
        asset=by_name[item['asset']]
        if asset['size'] != item['size']:raise SystemExit('Remote asset size mismatch')
        with __import__('tempfile').TemporaryDirectory() as tmp:
            run('gh','release','download',tag,'--repo',repo,'--pattern',item['asset'],'--dir',tmp)
            if hashlib.sha256((Path(tmp)/item['asset']).read_bytes()).hexdigest()!=item['sha256']:
                raise SystemExit('Remote SHA256 mismatch: '+item['asset'])
    run('gh','release','edit',tag,'--repo',repo,'--draft=false')
    print('Published: https://github.com/'+repo)
    print('ArchiveStore repository integration is the next separate step.')

if __name__ == '__main__':main()
