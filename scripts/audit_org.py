#!/usr/bin/env python3
import argparse, base64, json, os, re, urllib.error, urllib.parse, urllib.request

def api(url, token):
    req=urllib.request.Request(url,headers={'Authorization':f'Bearer {token}','Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'prodkit-workflows-audit'})
    try:
        with urllib.request.urlopen(req) as r: return json.load(r),r.headers
    except urllib.error.HTTPError as e:
        if e.code==404: return None,{}
        raise

def file_text(repo,path,token):
    obj,_=api(f'https://api.github.com/repos/{repo}/contents/{path}',token)
    if not obj: return None
    return base64.b64decode(obj['content']).decode()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--org',required=True); ap.add_argument('--workflows-repository',required=True); ap.add_argument('--required-sha',required=True); ap.add_argument('--repository-prefix',default=''); ap.add_argument('--json-out')
    a=ap.parse_args(); token=os.environ.get('GITHUB_TOKEN');
    if not token: raise SystemExit('GITHUB_TOKEN required')
    if not re.fullmatch(r'[0-9a-f]{40}',a.required_sha): raise SystemExit('required SHA must be 40 lowercase hex chars')
    repos=[]; page=1
    while True:
        data,_=api(f'https://api.github.com/orgs/{a.org}/repos?per_page=100&page={page}&type=all',token)
        if not data: break
        repos.extend(data)
        if len(data)<100: break
        page+=1
    findings=[]; required={'ci.yml':'reusable-ci.yml','security.yml':'reusable-security.yml','release.yml':'reusable-release.yml'}
    direct_release_patterns=[r'softprops/action-gh-release',r'gh\s+release\s+create',r'/releases(?:/|\b)',r'git\s+tag\s+',r'npm\s+publish',r'uv\s+publish']
    for r in sorted(repos,key=lambda x:x['name']):
        name=r['name']
        if r.get('archived') or (a.repository_prefix and not name.startswith(a.repository_prefix)) or r['full_name']==a.workflows_repository: continue
        repo=r['full_name']; errs=[]
        for filename,target in required.items():
            text=file_text(repo,f'.github/workflows/{filename}',token)
            if text is None: errs.append(f'missing .github/workflows/{filename}'); continue
            expected=f'{a.workflows_repository}/.github/workflows/{target}@{a.required_sha}'
            if expected not in text: errs.append(f'{filename} not pinned to required central SHA')
            floating=re.findall(re.escape(a.workflows_repository)+r'/.github/workflows/[^@\s]+@([^\s]+)',text)
            if any(not re.fullmatch(r'[0-9a-f]{40}',x) for x in floating): errs.append(f'{filename} contains floating central reference')
            if filename=='release.yml':
                for pat in direct_release_patterns:
                    if re.search(pat,text,re.I): errs.append(f'release.yml contains local publication implementation: {pat}')
        if errs: findings.append({'repository':repo,'errors':sorted(set(errs))})
    report={'organization':a.org,'workflows_repository':a.workflows_repository,'required_sha':a.required_sha,'repositories_checked':len([r for r in repos if not r.get('archived') and (not a.repository_prefix or r['name'].startswith(a.repository_prefix)) and r['full_name']!=a.workflows_repository]),'noncompliant':findings}
    out=json.dumps(report,indent=2); print(out)
    if a.json_out: open(a.json_out,'w').write(out+'\n')
    if findings: raise SystemExit(f'{len(findings)} repositories violate workflow policy')
if __name__=='__main__': main()
