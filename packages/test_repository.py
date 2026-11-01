import base64
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import publish
import validate


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.project=Path(self.temp.name)
        self.root=self.project/'packages'
        shutil.copytree(validate.ROOT,self.root,ignore=shutil.ignore_patterns('__pycache__'))
        (self.project/'.git').mkdir();(self.project/'.gitignore').write_text('packages/release-assets/*.deb\n')
        config=validate.read('repository.json',self.root);config['distribution']='releases';validate.write('repository.json',config,self.root);publish.prepare(self.root)
    def catalog(self):return validate.full_catalog(self.root)
    def write(self,data):
        validate.write('packages-v2.json',data,self.root);validate.write('packages.json',validate.legacy_catalog(data),self.root)
    def test_actual_nine_packages_and_store_version(self):
        data=validate.validate(self.root,quiet=True)
        self.assertEqual(len(data['packages']),10)
        self.assertEqual(next(p for p in data['packages'] if p['package']=='archive-store')['version'],'1.2.8')
        self.assertEqual(data['distribution'],'releases')
    def test_repository_mode_has_raw_urls_and_includes_native_debs(self):
        config=validate.read('repository.json',self.root);config['distribution']='repository';validate.write('repository.json',config,self.root)
        data=publish.prepare(self.root);self.assertEqual(data['distribution'],'repository')
        self.assertTrue(all(p['deb_url'].startswith('https://raw.githubusercontent.com/archive-os/aos-packages/main/packages/release-assets/') for p in data['packages']))
        with patch.object(publish,'ROOT',self.root):self.assertEqual(len([p for p in publish.publication_paths() if p.endswith('.deb')]),10)
        validate.validate(self.root,quiet=True)

    def test_prepare_is_idempotent_and_never_changes_versions_or_calls_network(self):
        original=self.catalog();versions={p['package']:p['version'] for p in original['packages']}
        with patch.object(publish,'run',side_effect=AssertionError('Network/Git call during prepare')):
            one=publish.prepare(self.root);before=(self.root/'packages.json').read_bytes();two=publish.prepare(self.root)
        self.assertEqual(before,(self.root/'packages.json').read_bytes());self.assertEqual(one,two)
        self.assertEqual(versions,{p['package']:p['version'] for p in two['packages']})
    def test_prepare_restores_catalog_when_a_deb_is_corrupt(self):
        data=self.catalog();(self.root/'release-assets'/data['packages'][0]['asset']).write_bytes(b'bad')
        original=(self.root/'packages.json').read_bytes()
        with self.assertRaises(ValueError):publish.prepare(self.root)
        self.assertEqual(original,(self.root/'packages.json').read_bytes())
    def test_rejects_wrong_deb_hash_and_wrong_identity(self):
        for field,value in [('sha256','0'*64),('version','99.0')]:
            original=self.catalog();data=copy.deepcopy(original);data['packages'][0][field]=value;self.write(data)
            with self.subTest(field=field),self.assertRaises(ValueError):validate.validate(self.root,quiet=True)
            self.write(original)
    def test_rejects_raw_download_and_external_url(self):
        original=self.catalog()
        for url in ['https://example.com/package.deb','https://raw.githubusercontent.com/archive-os/aos-packages/main/file.deb']:
            data=copy.deepcopy(original);data['packages'][0]['deb_url']=url;self.write(data)
            with self.assertRaises(ValueError):validate.validate(self.root,quiet=True)
    def test_rejects_path_traversal(self):
        data=self.catalog();data['packages'][0]['asset']='../outside.deb';self.write(data)
        with self.assertRaises(ValueError):validate.validate(self.root,quiet=True)
    def test_optional_application_cannot_be_a_required_system_package(self):
        validate.write('system.json',{'schema_version':1,'version':'2.0.4','packages':['archive-companion']},self.root)
        with self.assertRaisesRegex(ValueError,'Required packages'):validate.validate(self.root,quiet=True)
    def test_unfilled_system_template_is_not_publishable(self):
        shutil.copyfile(self.root/'examples/system.json.example',self.root/'system.json')
        with self.assertRaises(ValueError):validate.validate(self.root,quiet=True)
    def fake_publication(self,corrupt=False,staged=False):
        calls=[];assets={};draft=True
        def run(*argv,**kwargs):
            nonlocal draft
            calls.append(argv)
            if argv[:4]==('git','remote','get-url','origin'):return 'https://github.com/archive-os/aos-packages\n'
            if argv[:3]==('git','branch','--show-current'):return 'main\n'
            if argv[:4]==('git','diff','--cached','--name-only'):
                if staged:return 'unrelated-user-file\n'
                return 'packages/packages.json\n' if any(c[:2]==('git','add') for c in calls) else ''
            if argv[:3]==('gh','repo','view'):return json.dumps({'nameWithOwner':publish.REPOSITORY,'isPrivate':False})
            if argv[:3]==('git','rev-parse','origin/main'):return 'a'*40+'\n'
            if argv[:3]==('git','rev-parse','HEAD'):return 'b'*40+'\n'
            if argv[:2]==('gh','api'):
                if '/releases?' in argv[2]:return '[]'
                name=argv[2].split('/contents/packages/',1)[1].split('?',1)[0]
                return json.dumps({'content':base64.b64encode((self.root/name).read_bytes()).decode()})
            if argv[:3]==('gh','release','view'):return json.dumps({'assets':list(assets.values()),'isDraft':draft})
            if argv[:3]==('gh','release','upload'):
                path=Path(argv[4]);assets[path.name]={'name':path.name,'size':path.stat().st_size};return ''
            if argv[:3]==('gh','release','download'):
                asset=argv[argv.index('--pattern')+1];directory=Path(argv[argv.index('--dir')+1]);directory.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(self.root/'release-assets'/asset,directory/asset)
                if corrupt:(directory/asset).write_bytes(b'corrupt')
                return ''
            if argv[:3]==('gh','release','edit'):draft=False;return ''
            if argv[:2]==('git','ls-remote'):return 'b'*40+'\trefs/heads/main\n'
            return ''
        with patch.object(publish,'ROOT',self.root),patch.object(publish,'PROJECT',self.project),patch.object(publish,'run',side_effect=run),patch.object(publish.shutil,'which',return_value='/available'):
            if corrupt or staged:
                with self.assertRaises(ValueError):publish.publish()
            else:publish.publish()
        return calls
    def test_assets_are_verified_before_catalog_becomes_public(self):
        calls=self.fake_publication()
        indices=lambda prefix:[i for i,c in enumerate(calls) if c[:len(prefix)]==prefix]
        self.assertEqual(len(indices(('gh','release','upload'))),10)
        self.assertEqual(len(indices(('gh','release','download'))),10)
        self.assertLess(max(indices(('gh','release','download'))),min(indices(('gh','release','edit'))))
        self.assertLess(max(indices(('gh','release','edit'))),min(indices(('git','add'))))
        self.assertLess(max(indices(('git','add'))),min(indices(('git','push'))))
        self.assertFalse(any('--clobber' in c or '--force' in c for c in calls))
        remove=next(c for c in calls if c[:2]==('git','rm'));self.assertIn('--cached',remove)
        self.assertTrue(all((self.root/'release-assets'/p['asset']).exists() for p in self.catalog()['packages']))
    def test_corrupt_remote_asset_stops_before_catalog_commit_or_push(self):
        calls=self.fake_publication(corrupt=True)
        self.assertFalse(any(c[:2] in [('git','add'),('git','commit'),('git','push')] for c in calls))
    def test_unrelated_staged_work_is_not_published(self):
        calls=self.fake_publication(staged=True)
        self.assertFalse(any(c[0]=='gh' for c in calls))
    def test_unrelated_local_files_are_not_selected_for_publication(self):
        (self.root/'private-note.txt').write_text('private')
        with patch.object(publish,'ROOT',self.root):paths=publish.publication_paths()
        self.assertNotIn('packages/private-note.txt',paths)
    def test_missing_release_deb_is_downloaded_and_verified(self):
        item=self.catalog()['packages'][0];target=self.root/'release-assets'/item['asset'];content=target.read_bytes();target.unlink()
        calls=[]
        def run(*argv,**kwargs):
            calls.append(argv);directory=Path(argv[argv.index('--dir')+1]);(directory/item['asset']).write_bytes(content)
        with patch.object(publish,'ROOT',self.root),patch.object(publish,'run',side_effect=run):publish.download_assets()
        self.assertEqual(target.read_bytes(),content);self.assertEqual(len(calls),1)
        self.assertEqual(calls[0][:3],('gh','release','download'))
    def test_corrupt_download_does_not_create_a_local_deb(self):
        item=self.catalog()['packages'][0];target=self.root/'release-assets'/item['asset'];target.unlink()
        def run(*argv,**kwargs):
            directory=Path(argv[argv.index('--dir')+1]);(directory/item['asset']).write_bytes(b'bad')
        with patch.object(publish,'ROOT',self.root),patch.object(publish,'run',side_effect=run),self.assertRaises(ValueError):publish.download_assets()
        self.assertFalse(target.exists())
    def test_api_failure_is_not_treated_as_missing_release(self):
        import subprocess
        with patch.object(publish,'run',side_effect=subprocess.CalledProcessError(1,['gh','api'])),self.assertRaises(subprocess.CalledProcessError):publish.existing_release('test')


if __name__=='__main__':unittest.main()
