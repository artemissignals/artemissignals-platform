#!/usr/bin/env python3
"""Add optional new-signal audio to the current dashboard HTML without replacing the page."""
import argparse,shutil
from datetime import datetime,timezone
from pathlib import Path
STYLE='''<style id="artemisSignalSoundStyles">
.signal-sound-toggle{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--line,#29465a);border-radius:10px;padding:8px 10px;background:transparent;color:inherit;cursor:pointer;font:inherit;font-size:11px;white-space:nowrap}.signal-sound-toggle svg{width:19px;height:19px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}.signal-sound-toggle[data-enabled="true"]{color:var(--brand,#ffa460)}.signal-sound-toggle[data-enabled="true"] .sound-slash{display:none}.signal-sound-toggle:focus-visible{outline:2px solid var(--brand,#ffa460);outline-offset:3px}.signal-sound-settings{display:flex;gap:16px;align-items:center;flex-wrap:wrap}.signal-sound-settings label{display:flex;align-items:center;gap:8px}.signal-sound-settings select{padding:8px;border-radius:8px;background:var(--panel,#122438);color:inherit;border:1px solid var(--line,#29465a)}@media(max-width:600px){.signal-sound-toggle [data-sound-label]{display:none}}
</style>'''
BUTTON='''<button id="signalSoundToggle" class="signal-sound-toggle" type="button" data-enabled="true" aria-pressed="true" aria-label="New-signal sound on; click to mute" title="Signal sounds on"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/><path class="sound-slash" d="M3 3l18 18"/></svg><span data-sound-label>Sound on</span></button>'''
PANEL='''<div class="panel" id="signalSoundPanel"><h3>New-signal sounds</h3><p class="v105-note">Play a sound when a newly detected signal matches your Notification Center filters. On by default. Target hits, stops, historical signals and initial page loading do not ring.</p><div class="signal-sound-settings"><label><input id="signalSoundEnabled" type="checkbox" checked> Sound on</label><label for="signalSoundChoice">Sound <select id="signalSoundChoice"><option value="bell">Bell</option><option value="chime">Chime</option><option value="ping">Double ping</option><option value="soft">Soft tone</option></select></label><label for="signalSoundVolume">Volume <input id="signalSoundVolume" type="range" min="0.1" max="1" step="0.1" value="0.5"></label><button id="signalSoundTest" type="button">Preview sound</button></div><p id="signalSoundStatus" class="v105-note" role="status" aria-live="polite">On by default. Click the dashboard once to allow browser audio.</p><p class="alerts106-hint">Saved separately for each account on this browser. Keep the dashboard tab open and sign in. Background tabs can ring while running, but browser suspension, tab mute, sleep or closing the tab can delay or prevent alerts. This is dashboard audio, separate from Telegram and browser push. Multiple tabs use best-effort duplicate suppression.</p></div>'''
HOOK="try{window.artemisSignalSound?.ingest({account:notifyAccount,events:notifyState.events,matching:notifyFiltered(),complete:typeof signalMetricsComplete==='boolean'&&signalMetricsComplete});}catch(_){}"
def patch(text):
 text=text.replace('\r\n','\n')
 if 'id="signalSoundPanel"' in text:
  if 'signal-sounds.js' in text and HOOK in text:return text
  raise ValueError('A partial sound installation already exists. Review before patching.')
 if text.count('<div id="notifyRoot"')!=1:raise ValueError('Expected dashboard notification bell not found.')
 a=text.find('<section id="settings"');b=text.find('</section>',a)
 if a<0 or b<0:raise ValueError('Account Settings section not found.')
 begin=text.find('function notifyIngest(){');end=text.find('function notifyFiltered()',begin)
 if begin<0 or end<0:raise ValueError('Expected notification ingestion functions missing.')
 part=text[begin:end];anchor='notifySave();notifyRender();'
 if part.count(anchor)!=1:raise ValueError('Notification ingestion changed. Stop for source review.')
 for name in ('notifyScope','notifyFiltered','notifyState','signalMetricsComplete'):
  if name not in text:raise ValueError('Required dashboard integration missing: '+name)
 text=text[:begin]+part.replace(anchor,anchor+'\n '+HOOK)+text[end:]
 text=text.replace('<div id="notifyRoot"',BUTTON+'<div id="notifyRoot"',1)
 a=text.find('<section id="settings"');b=text.find('</section>',a);text=text[:b]+PANEL+'\n'+text[b:]
 if text.count('</head>')!=1 or text.count('</body>')!=1:raise ValueError('Unexpected HTML document structure.')
 text=text.replace('</head>',STYLE+'\n</head>',1).replace('</body>','<script src="signal-sounds.js"></script>\n</body>',1)
 return text

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('index',type=Path);args=p.parse_args();path=args.index.expanduser().resolve()
 if path.name!='index.html' or not path.is_file():raise SystemExit('Provide the current dashboard/index.html file.')
 text=path.read_text();updated=patch(text);asset=Path(__file__).resolve().parent.parent/'dashboard'/'signal-sounds.js'
 if not asset.is_file():raise SystemExit('Keep the supplied tools/ and dashboard/ folders together.')
 if updated!=text:
  backupdir=Path.home()/'artemis-backups'/'dashboard-sounds';backupdir.mkdir(parents=True,exist_ok=True);backup=backupdir/('index-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')+'.html');shutil.copy2(path,backup);path.write_text(updated);print('Backup:',backup)
 else:print('HTML sound integration already present.')
 dest=path.parent/'signal-sounds.js'
 if dest!=asset:shutil.copy2(asset,dest)
 print('Updated:',path);print('Commit only dashboard/index.html and dashboard/signal-sounds.js. No AWS changes.')
if __name__=='__main__':main()
