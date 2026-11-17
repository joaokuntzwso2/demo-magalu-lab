#!/usr/bin/env python3
"""Add a Section 7 test hub to the existing Magalu lab without replacing its shell.

Usage from repository root after extracting this package:
  python3 section7_lab_update/install.py --check
  python3 section7_lab_update/install.py --apply

This installer intentionally does not touch WSO2, tenant data, generated secrets,
Docker volumes, existing workbenches or existing application sessions.
"""
from __future__ import annotations
import argparse
import ast
import difflib
from pathlib import Path
import re
import shutil
import sys

HERE=Path(__file__).resolve().parent
SOURCE=HERE/'payload'
IMPORT='\n# Section 7 guided test catalog (navigation only; no simulated test outcomes)\nfrom demo.lab_hub import router as _section7_lab_router\napp.include_router(_section7_lab_router)\n'

NAV='''<div class="lab-side-divider" role="presentation">ROTEIRO DE TESTES · SEÇÃO 7</div>
<a href="/lab" class="{% if request.url.path == '/lab' %}active{% endif %}">▣ &nbsp; Roteiro completo de avaliação</a>
<a href="/m3/isolation" class="{% if request.url.path == '/m3/isolation' %}active{% endif %}">⌁ &nbsp; Isolamento entre tenants</a>
<a href="/m3/native-consent" class="{% if request.url.path == '/m3/native-consent' %}active{% endif %}">◎ &nbsp; Consentimento nativo WSO2</a>
<a href="/m3/completion" class="{% if request.url.path == '/m3/completion' %}active{% endif %}">▦ &nbsp; PF / PJ / M2M · Workbench</a>
'''
STYLE='''<style id="s7lab-shell-additions">
.lab-side-divider{padding:16px 15px 5px;font-size:10px;letter-spacing:.10em;color:#9cb4d6;font-weight:800}
.sidebar{overflow-y:auto;scrollbar-width:thin}
html.lab-embedded .sidebar,html.lab-embedded .topbar,html.lab-embedded footer{display:none!important}
html.lab-embedded .shell{display:block!important;grid-template-columns:1fr!important}
html.lab-embedded .main{width:100%!important;margin:0!important;max-width:none!important;min-height:0!important}
html.lab-embedded .content{padding:14px!important;max-width:none!important}
</style>
<script>try{if(new URLSearchParams(location.search).get('embed')==='1')document.documentElement.classList.add('lab-embedded');}catch(_){}</script>
'''

FILES=[
 'demo/lab_hub.py',
 'demo/templates/lab_hub.html',
 'demo/static/lab_hub.css',
 'demo/static/lab_hub.js',
 'scripts/bootstrap_sellerldap_roles.sh',
 'README.md',
 'tests/test_section7_lab.py',
]

def patch_main(text):
    if 'from demo.lab_hub import router as _section7_lab_router' in text:
        return text
    # Fail instead of appending import to a different module with no FastAPI app.
    if not re.search(r'^app\s*=\s*FastAPI\(',text,re.MULTILINE):
        raise RuntimeError('demo/main.py does not define app=FastAPI(...); manual integration required')
    return text.rstrip()+'\n'+IMPORT

def patch_base(text):
    if 'id="s7lab-shell-additions"' not in text:
        if '</head>' not in text:
            raise RuntimeError('demo/templates/base.html has no </head>')
        text=text.replace('</head>',STYLE+'</head>',1)
    if 'ROTEIRO DE TESTES · SEÇÃO 7' not in text:
        marker='<nav class="side-nav">'
        if marker not in text:
            raise RuntimeError('demo/templates/base.html has no expected side-nav marker')
        text=text.replace(marker,marker+'\n'+NAV,1)
    return text


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check',action='store_true',help='Preview changes, no writes')
    mode.add_argument('--apply',action='store_true',help='Write reviewed changes, with backups')
    parser.add_argument('--repo',type=Path,default=Path.cwd(),help='Repository root (default current working directory)')
    args=parser.parse_args()
    root=args.repo.resolve()
    required=['demo/main.py','demo/templates/base.html','compose.yaml']
    missing=[p for p in required if not (root/p).is_file()]
    if missing:
        parser.error('Not at Magalu repository root; missing: '+', '.join(missing))
    updates={}
    for rel in FILES:
        source=SOURCE/rel
        if not source.is_file(): raise RuntimeError(f'Package incomplete: {rel}')
        updates[root/rel]=source.read_text(encoding='utf-8')
    for path,patch in [(root/'demo/main.py',patch_main),(root/'demo/templates/base.html',patch_base)]:
        updates[path]=patch(path.read_text(encoding='utf-8'))
    changed=[]
    for path,content in updates.items():
        previous=path.read_text(encoding='utf-8') if path.exists() else None
        if previous==content:continue
        changed.append((path,previous,content))
    print(('Previewing' if args.check else 'Applying')+f' {len(changed)} file change(s) in {root}')
    for path,old,new in changed:
        rel=path.relative_to(root)
        print(' ', 'ADD' if old is None else 'UPDATE',rel)
        if str(rel) in ('demo/main.py','demo/templates/base.html') and old is not None:
            print(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile=str(rel),tofile=str(rel)+' (updated)'))[:1600])
    if args.check:
        print('No files written. Use --apply to install.')
        return 0
    # Backups are outside tracked source, never automatically stage them.
    backups=root.parent/(root.name+'-section7-backup')
    backups.mkdir(exist_ok=True)
    for path,old,new in changed:
        if old is not None:
            backup=backups/path.relative_to(root)
            backup.parent.mkdir(parents=True,exist_ok=True)
            if not backup.exists(): backup.write_text(old,encoding='utf-8')
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(new,encoding='utf-8')
    print(f'Done. Original modified files backed up outside repository: {backups}')
    print('Next: python3 -m compileall -q demo; rebuild only the demo container; visit http://localhost:8180/lab')
    return 0

if __name__=='__main__':
    sys.exit(main())
