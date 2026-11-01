#!/usr/bin/env python3
"""Prepare/check locally, or explicitly publish verified DEBs before catalog metadata."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from urllib.parse import quote
from validate import ROOT,read,write,sha256,validate,require,full_catalog,legacy_catalog

PROJECT=ROOT.parent
REPOSITORY='archive-os/aos-packages'


def run(*argv,capture=False,cwd=PROJECT):
    result=subprocess.run(list(argv),cwd=cwd,check=True,text=True,stdout=subprocess.PIPE if capture else None)
    return result.stdout


def prepare(root=None):
    root=Path(root or ROOT)
    data=full_catalog(root)
    identity=sorted((p['package'],p['version'],p['asset'],p['sha256']) for p in data['packages'])
    digest=hashlib.sha256(json.dumps(identity,separators=(',',':')).encode()).hexdigest()[:24]
    tag='packages-'+digest
    data.update(distribution='releases',release_tag=tag)
    for item in data['packages']:
        item['deb_url']=f'https://github.com/{REPOSITORY}/releases/download/{tag}/'+quote(item['asset'],safe='')
    names=['packages.json']+(['packages-v2.json'] if (root/'packages-v2.json').exists() else [])
    previous={name:(root/name).read_bytes() for name in names}
    try:
        if 'packages-v2.json' in names:
            write('packages-v2.json',data,root);write('packages.json',legacy_catalog(data),root)
        else:write('packages.json',data,root)
        validate(root,quiet=True)
    except BaseException:
        for name,content in previous.items():(root/name).write_bytes(content)
        raise
    print(f'Prepared {len(identity)} packages for {tag}; no network, version change or publication.')
    return data


def existing_release(tag):
    for page in range(1,1001):
        releases=json.loads(run('gh','api',f'repos/{REPOSITORY}/releases?per_page=100&page={page}',capture=True))
        require(isinstance(releases,list),'Invalid releases API response')
        found=next((release for release in releases if release.get('tag_name')==tag),None)
        if found is not None:return found
        if len(releases)<100:return None
    raise ValueError('Release listing exceeded the supported page count')


def verify_remote_assets(tag,catalog,temporary):
    listing=json.loads(run('gh','release','view',tag,'--repo',REPOSITORY,'--json','assets,isDraft',capture=True))
    assets={a['name']:a for a in listing['assets']}
    for item in catalog['packages']:
        remote=assets.get(item['asset'])
        require(remote is not None and remote['size']==item['size'],'Missing or wrong-size remote asset: '+item['asset'])
        directory=Path(temporary)/item['package'];directory.mkdir(parents=True,exist_ok=True)
        run('gh','release','download',tag,'--repo',REPOSITORY,'--pattern',item['asset'],'--dir',str(directory))
        require(sha256(directory/item['asset'])==item['sha256'],'Remote asset checksum mismatch: '+item['asset'])
    return listing


def publication_paths():
    result=['.gitignore'] if (ROOT.parent/'.gitignore').is_file() else []
    names=('.gitignore','repository.json','packages.json','packages-v2.json','logos.json','screenshots.json','system.json',
           'README.md','RELEASE-NOTES.md','publish.py','validate.py','test_repository.py',
           'examples/system.json.example','examples/system-package.json.example')
    for name in names:
        path=ROOT/name
        if path.is_file():
            require(not path.is_symlink(),'Publication source cannot be a symlink')
            result.append('packages/'+name)
    media=set(read('logos.json',ROOT)['logos'].values())
    for images in read('screenshots.json',ROOT)['screenshots'].values():
        media.update(images)
        if images:
            info=str(Path(images[0]).parent/'BILGI.txt')
            if (ROOT/info).is_file():media.add(info)
    for name in media:
        from validate import local_file
        local_file(name,ROOT)
        result.append('packages/'+name)
    return sorted(set(result))


def publish():
    for executable in ('git','gh'):
        require(shutil.which(executable) is not None,'Missing executable: '+executable)
    catalog=prepare();tag=catalog['release_tag']
    require((PROJECT/'.git').is_dir(),'Run publication from the supplied repository checkout')
    origin=run('git','remote','get-url','origin',capture=True).strip().rstrip('/').removesuffix('.git')
    require(origin=='https://github.com/'+REPOSITORY,'Unexpected Git origin')
    require(run('git','branch','--show-current',capture=True).strip()=='main','Check out main before publishing')
    require(not run('git','diff','--cached','--name-only',capture=True).strip(),'Index already contains staged changes; review/unstage them before publishing')
    run('gh','auth','status')
    info=json.loads(run('gh','repo','view',REPOSITORY,'--json','nameWithOwner,isPrivate',capture=True))
    require(info['nameWithOwner'].lower()==REPOSITORY and not info['isPrivate'],'Expected the public aos-packages repository')
    run('git','fetch','origin','main')
    run('git','merge-base','--is-ancestor','origin/main','HEAD')
    target=run('git','rev-parse','origin/main',capture=True).strip()
    paths=publication_paths()
    snapshots={name:sha256(PROJECT/name) for name in paths}
    previous=existing_release(tag)
    with tempfile.TemporaryDirectory(prefix='aos-release-') as temporary:
        tmp=Path(temporary)
        staged=tmp/'upload';staged.mkdir()
        for item in catalog['packages']:
            source=ROOT/'release-assets'/item['asset'];destination=staged/item['asset']
            shutil.copyfile(source,destination)
            require(sha256(destination)==item['sha256'],'Local DEB changed during publication')
        if previous is None:
            run('gh','release','create',tag,'--repo',REPOSITORY,'--target',target,'--draft',
                '--title','ArchiveOS packages','--notes','Verified DEBs for the ArchiveStore packages catalog. SHA256 and package versions are recorded in packages/packages.json.')
        listing=json.loads(run('gh','release','view',tag,'--repo',REPOSITORY,'--json','assets,isDraft',capture=True))
        existing={a['name'] for a in listing['assets']}
        for item in catalog['packages']:
            if item['asset'] not in existing:
                run('gh','release','upload',tag,str(staged/item['asset']),'--repo',REPOSITORY)
        listing=verify_remote_assets(tag,catalog,tmp/'verify')
        require(all((PROJECT/name).is_file() and sha256(PROJECT/name)==digest for name,digest in snapshots.items()),'Metadata changed during publication; rerun after reviewing changes')
        require(publication_paths()==paths,'Metadata file list changed during publication')
        if listing['isDraft']:run('gh','release','edit',tag,'--repo',REPOSITORY,'--draft=false','--latest=false')
    run('git','add','--',*paths)
    run('git','rm','-r','--cached','--ignore-unmatch','--','packages/release-assets')
    staged=run('git','diff','--cached','--name-only',capture=True).splitlines()
    require(all(name in paths or name.startswith('packages/release-assets/') for name in staged),'Unexpected staged path')
    if staged:run('git','commit','-m','Publish verified ArchiveOS packages catalog')
    run('git','push','origin','HEAD:main')
    local=run('git','rev-parse','HEAD',capture=True).strip()
    remote=run('git','ls-remote','origin','refs/heads/main',capture=True).split()
    require(bool(remote) and remote[0]==local,'Remote commit verification failed')
    import base64
    for name in ('packages.json','packages-v2.json','system.json'):
        if not (ROOT/name).exists():continue
        response=json.loads(run('gh','api',f'repos/{REPOSITORY}/contents/packages/{name}?ref={local}',capture=True))
        require(base64.b64decode(response['content'])==(ROOT/name).read_bytes(),'Published catalog verification failed: '+name)
    print(f'Published and verified {len(catalog["packages"])} packages: https://github.com/{REPOSITORY}/releases/tag/{tag}')


def download_assets():
    catalog=full_catalog(ROOT)
    require(catalog.get('distribution')=='releases','Expected a prepared Releases catalog')
    tag=catalog.get('release_tag','')
    import re
    require(isinstance(tag,str) and bool(re.fullmatch(r'[A-Za-z0-9._-]{1,100}',tag)),'Invalid release tag')
    for item in catalog['packages']:
        from validate import ASSET
        require(isinstance(item.get('asset'),str) and bool(ASSET.fullmatch(item['asset'])),'Invalid asset filename')
        target=ROOT/'release-assets'/item['asset']
        require(target.parent.resolve().is_relative_to(ROOT.resolve()),'Unsafe local asset directory')
        if target.exists():
            require(not target.is_symlink() and target.stat().st_size==item['size'] and sha256(target)==item['sha256'],'Existing local DEB differs; review it before downloading')
            continue
        with tempfile.TemporaryDirectory(prefix='aos-download-') as temporary:
            run('gh','release','download',tag,'--repo',REPOSITORY,'--pattern',item['asset'],'--dir',temporary)
            source=Path(temporary)/item['asset']
            require(source.is_file() and source.stat().st_size==item['size'] and sha256(source)==item['sha256'],'Downloaded DEB checksum/size mismatch')
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source,target)
    validate(ROOT)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check',action='store_true',help='Validate local catalog and DEBs; no network or writes')
    mode.add_argument('--prepare',action='store_true',help='Prepare deterministic release URLs locally; never change package versions')
    mode.add_argument('--download',action='store_true',help='Download missing Release DEBs into the local staging area; never publish')
    mode.add_argument('--publish',action='store_true',help='Upload/verify release assets, then commit and push catalog metadata')
    args=parser.parse_args()
    try:
        if args.check:validate()
        elif args.prepare:prepare()
        elif args.download:download_assets()
        else:publish()
    except (OSError,ValueError,KeyError,subprocess.CalledProcessError) as error:raise SystemExit('Stopped: '+str(error))


if __name__=='__main__':main()
