#!/usr/bin/env python3
import argparse, json, pathlib, tomllib

def dotted(obj, selector):
    for part in selector.split('.'):
        obj=obj[part]
    return obj

def validate(root: pathlib.Path, manifest_path: pathlib.Path, version: str):
    root=root.resolve(); mp=manifest_path.resolve()
    if root not in mp.parents: raise ValueError('manifest escapes root')
    data=json.loads(mp.read_text())
    if data.get('schema_version') != 1: raise ValueError('unsupported schema_version')
    sources=data.get('version',{}).get('sources',[])
    if not sources: raise ValueError('at least one version source required')
    for src in sources:
        p=(root/src['path']).resolve()
        if root not in p.parents: raise ValueError(f"path escapes root: {src['path']}")
        typ=src['type']; selector=src.get('selector')
        if typ=='text': actual=p.read_text().strip()
        elif typ=='json': actual=dotted(json.loads(p.read_text()),selector or 'version')
        elif typ=='toml': actual=dotted(tomllib.loads(p.read_text()),selector or 'project.version')
        else: raise ValueError(f'unsupported type: {typ}')
        if str(actual)!=version: raise ValueError(f"version mismatch {src['path']}: {actual} != {version}")
    notes=data['notes']['path_template'].format(version=version,tag='v'+version)
    if not (root/notes).is_file(): raise ValueError(f'missing notes {notes}')
    build=data['build']; script=(root/build['script']).resolve(); artifact=(root/build['artifact_dir']).resolve()
    if root not in script.parents or root not in artifact.parents: raise ValueError('build path escapes root')
    if not script.is_file() or script.is_symlink(): raise ValueError('build script invalid')
    return data

def main():
    p=argparse.ArgumentParser(); p.add_argument('version'); p.add_argument('--root',default='.'); p.add_argument('--manifest',default='.prodkit/release.json')
    a=p.parse_args(); root=pathlib.Path(a.root); validate(root,root/a.manifest,a.version); print('release manifest valid')
if __name__=='__main__': main()
