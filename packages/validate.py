#!/usr/bin/env python3
"""Validate local package artifacts and Store metadata without network access."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
from urllib.parse import quote
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parent
PACKAGE=re.compile(r'(?:aos-[a-z0-9][a-z0-9+.-]*|archiveos-[a-z0-9][a-z0-9+.-]*|aosver|archive-store|archive-companion)\Z')
ASSET=re.compile(r'[A-Za-z0-9][A-Za-z0-9_.+~:-]*\.deb\Z')


def require(condition,message):
    if not condition:raise ValueError(message)


def read(name,root=ROOT):
    return json.loads((Path(root)/name).read_text(encoding='utf-8'))


def write(name,data,root=ROOT):
    path=Path(root)/name
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def full_catalog(root=ROOT):
    root=Path(root)
    return read('packages-v2.json' if (root/'packages-v2.json').exists() else 'packages.json',root)


def legacy_catalog(data):
    allowed=re.compile(r'(?:aos-[a-z0-9][a-z0-9+.-]*|archiveos-[a-z0-9][a-z0-9+.-]*|aosver|archive-store)\Z')
    return dict(data,extended_catalog='packages-v2.json',packages=[p for p in data['packages'] if not p.get('system_package') and not p.get('store_hidden') and allowed.fullmatch(p['package']) and p.get('desktop_id')])


def sha256(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        while block:=stream.read(1024*1024):digest.update(block)
    return digest.hexdigest()


def local_file(value,root=ROOT):
    require(isinstance(value,str) and '\\' not in value,'Invalid local path')
    relative=PurePosixPath(value)
    require(not relative.is_absolute() and '..' not in relative.parts,'Unsafe local path: '+value)
    path=Path(root)/value
    require(path.resolve().is_relative_to(Path(root).resolve()) and path.is_file() and not path.is_symlink(),'Missing or unsafe local file: '+value)
    return path


def version(value,system=False):
    require(isinstance(value,str) and 0<len(value)<=100 and not value.startswith('-'),'Invalid package version')
    if system:require(bool(re.fullmatch(r'v?\d+(?:\.\d+){0,4}(?:[-+][A-Za-z0-9.-]+)?',value)),'Unsupported system version')
    require(subprocess.run(['dpkg','--validate-version',value],capture_output=True).returncode==0,'Invalid Debian version: '+value)


def validate(root=ROOT,quiet=False):
    from PIL import Image
    root=Path(root)
    config=read('repository.json',root)
    require(config.get('schema_version')==1 and config.get('repository')=='archive-os/aos-packages' and config.get('path')=='packages' and config.get('branch')=='main','Unexpected repository configuration')
    catalog=full_catalog(root)
    logos,shots=(read(n,root) for n in ('logos.json','screenshots.json'))
    require(all(isinstance(d,dict) and d.get('schema_version')==1 for d in (catalog,logos,shots)),'Unsupported metadata schema')
    require(catalog.get('distribution')=='releases','DEBs must use GitHub Releases')
    tag=catalog.get('release_tag','')
    require(isinstance(tag,str) and bool(re.fullmatch(r'[A-Za-z0-9._-]{1,100}',tag)),'Invalid release tag')
    packages=catalog.get('packages')
    require(isinstance(packages,list) and 1<=len(packages)<=256,'Invalid package list')
    keys=set()
    for item in packages:
        require(isinstance(item,dict),'Invalid package entry')
        name=item.get('package','')
        require(isinstance(name,str) and bool(PACKAGE.fullmatch(name)) and name not in keys,'Invalid or duplicate package identity')
        keys.add(name)
        version(item.get('version'))
        asset=item.get('asset','')
        require(isinstance(asset,str) and bool(ASSET.fullmatch(asset)),'Invalid DEB filename')
        deb=local_file('release-assets/'+asset,root)
        size=item.get('size')
        require(type(size) is int and 0<size<2*1024**3 and size==deb.stat().st_size,'Invalid DEB size: '+asset)
        require(item.get('sha256')==sha256(deb),'DEB checksum mismatch: '+asset)
        actual=subprocess.check_output(['dpkg-deb','-f',str(deb),'Package','Version','Architecture'],text=True)
        fields={line.split(':',1)[0]:line.split(':',1)[1].strip() for line in actual.splitlines() if ':' in line}
        for field,key in [('Package','package'),('Version','version'),('Architecture','architecture')]:
            require(fields.get(field)==item.get(key),'DEB '+field+' mismatch: '+asset)
        require(item.get('architecture') in ('all','amd64','arm64','i386','armhf'),'Unsupported architecture')
        url='https://github.com/'+config['repository']+'/releases/download/'+quote(tag,safe='')+'/'+quote(asset,safe='')
        require(item.get('deb_url')==url,'Incorrect release asset URL: '+asset)
        system=item.get('system_package',False)
        require(type(system) is bool,'Invalid system package flag')
        hidden=item.get('store_hidden',False)
        require(type(hidden) is bool and (not hidden or system),'Only system packages may be hidden')
        for key in ('optional','removable'):
            require(key not in item or type(item[key]) is bool,'Invalid '+key+' flag')
        desktop=item.get('desktop_id','')
        require(isinstance(desktop,str) and (system and not desktop or bool(re.fullmatch(r'[A-Za-z0-9_.+-]+\.desktop',desktop))),'Missing or invalid desktop ID')
        require(isinstance(item.get('summary',{}),dict),'Invalid localized summary')
        logo=logos.get('logos',{}).get(name)
        require(system or bool(logo),'Missing application logo: '+name)
        if logo:
            require(logo.startswith('logos/'),'Invalid logo directory')
            path=local_file(logo,root)
            require(path.stem==name,'Logo identity mismatch')
            if path.suffix=='.svg':require(ET.parse(path).getroot().tag.endswith('svg'),'Invalid SVG')
            else:
                with Image.open(path) as image:image.verify()
        images=shots.get('screenshots',{}).get(name,[])
        require(isinstance(images,list) and len(images)<=12 and (system or images),'Missing or invalid screenshots')
        for image_path in images:
            require(isinstance(image_path,str) and PurePosixPath(image_path).parts[:2]==('screenshots',name),'Invalid screenshot directory')
            with Image.open(local_file(image_path,root)) as image:
                require(image.width>=500 and image.height>=300,'Screenshot is too small')
                image.verify()
    require(set(logos.get('logos',{}))<=keys and set(shots.get('screenshots',{}))<=keys,'Media references an unknown package')
    system_file=root/'system.json'
    if system_file.exists():
        system=read('system.json',root)
        require(isinstance(system,dict) and system.get('schema_version')==1,'Invalid system manifest')
        version(system.get('version'),system=True)
        required=system.get('packages')
        require(isinstance(required,list) and bool(required) and all(isinstance(n,str) for n in required),'Invalid required system packages')
        require(len(required)==len(set(required)) and set(required)<=keys,'Duplicate or unknown required system package')
        by_name={p['package']:p for p in packages}
        require(all(by_name[n].get('system_package') is True and not by_name[n].get('optional') and not by_name[n].get('removable') for n in required),'Required packages cannot be removable or optional apps')
    if (root/'packages-v2.json').exists():
        require(read('packages.json',root)==legacy_catalog(catalog),'Legacy compatibility catalog differs; run --prepare')
    if not quiet:print(f'PASS: {len(packages)} DEBs, metadata, SHA256, media and optional system manifest; GitHub Releases')
    return catalog


if __name__=='__main__':
    try:validate()
    except (OSError,ValueError,KeyError,subprocess.CalledProcessError) as error:raise SystemExit('Validation failed: '+str(error))
