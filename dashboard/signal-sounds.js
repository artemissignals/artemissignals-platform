/* Artemis dashboard audio. No network requests, external audio, push subscription, or token storage. */
(()=>{
 'use strict';
 if(window.artemisSignalSound)return;
 const byId=id=>document.getElementById(id);
 const choices={bell:[[1046.5,0,.52,'sine'],[2093,.015,.38,'sine']],chime:[[783.99,0,.3,'sine'],[1046.5,.19,.45,'sine']],ping:[[1318.5,0,.16,'sine'],[1318.5,.25,.18,'sine']],soft:[[659.25,0,.45,'triangle']]};
 let account='',prefs={enabled:true,sound:'bell',volume:.5},ctx=null,initialized=false,baseline=0,seen=new Set(),active=[],status='',queue=Promise.resolve(),lastLocalPlay=0;
 const scope=()=>{try{return typeof notifyScope==='function'?notifyScope():'';}catch{return '';}};
 const prefKey=sub=>'artemis_signal_sound_v1:'+sub;
 const playedKey=sub=>'artemis_signal_sound_played_v1:'+sub;
 function readPrefs(sub){try{const p=JSON.parse(localStorage.getItem(prefKey(sub))||'null');return {enabled:typeof p?.enabled==='boolean'?p.enabled:true,sound:choices[p?.sound]?p.sound:'bell',volume:typeof p?.volume==='number'&&Number.isFinite(p.volume)?Math.max(.1,Math.min(1,p.volume)):.5};}catch{return {enabled:true,sound:'bell',volume:.5};}}
 function stop(){for(const node of active){try{node.stop();}catch{}}active=[];}
 function sync(){const sub=scope();if(sub!==account){stop();account=sub;prefs=readPrefs(sub);initialized=false;baseline=0;seen=new Set();status='';}return sub;}
 function render(){
  const checkbox=byId('signalSoundEnabled'),select=byId('signalSoundChoice'),volume=byId('signalSoundVolume'),button=byId('signalSoundToggle'),hint=byId('signalSoundStatus');
  if(checkbox){checkbox.checked=prefs.enabled;checkbox.disabled=!account;}
  if(select){select.value=prefs.sound;select.disabled=!account;}
  if(volume){volume.value=String(prefs.volume);volume.disabled=!account;}
  if(byId('signalSoundTest'))byId('signalSoundTest').disabled=!account;
  if(button){button.disabled=!account;button.setAttribute('aria-pressed',String(prefs.enabled));button.setAttribute('aria-label','New-signal sound '+(prefs.enabled?'on; click to mute':'off; click to unmute'));button.title=!account?'Sign in to use signal sounds':!prefs.enabled?'Signal sounds off · click to turn on':ctx?.state==='running'?'Signal sounds on · click to mute':'Signal sounds on · click anywhere on the dashboard to allow audio';button.dataset.enabled=String(prefs.enabled);const label=button.querySelector('[data-sound-label]');if(label)label.textContent=prefs.enabled?'Sound on':'Sound off';}
  if(hint)hint.textContent=!account?'Sign in to manage sound preferences.':status||(!prefs.enabled?'New-signal sounds are off.':ctx?.state==='running'?'Sound is ready while this dashboard remains running.':'On by default. Click the dashboard or Preview sound once to allow browser audio.');
 }
 function save(){try{localStorage.setItem(prefKey(account),JSON.stringify(prefs));status='Saved for this account on this browser.';}catch{status='Applied for this tab, but browser storage is unavailable; this choice may not persist.';}render();}
 async function unlock(){
  if(!sync())return false;
  try{const Audio=window.AudioContext||window.webkitAudioContext;if(!Audio){status='Audio is unavailable in this browser.';render();return false;}if(!ctx||ctx.state==='closed')ctx=new Audio();if(ctx.state!=='running')await ctx.resume();render();return ctx.state==='running';}catch{status='Browser audio is blocked. Use Preview sound or check this tab’s sound permission.';render();return false;}
 }
 function tone(sound,volume){
  if(!ctx||ctx.state!=='running')return Promise.resolve(false);
  const start=ctx.currentTime+.02;let end=0;
  try{
   for(const [frequency,offset,duration,wave] of choices[sound]||choices.bell){const o=ctx.createOscillator(),g=ctx.createGain();o.type=wave;o.frequency.setValueAtTime(frequency,start+offset);g.gain.setValueAtTime(.0001,start+offset);g.gain.exponentialRampToValueAtTime(Math.max(.001,volume*.14),start+offset+.012);g.gain.exponentialRampToValueAtTime(.0001,start+offset+duration);o.connect(g);g.connect(ctx.destination);o.start(start+offset);o.stop(start+offset+duration+.015);active.push(o);o.onended=()=>{o.disconnect();g.disconnect();active=active.filter(n=>n!==o);};end=Math.max(end,offset+duration);}
   return new Promise(resolve=>setTimeout(()=>resolve(true),(end+.08)*1000));
  }catch{stop();status='Could not play audio. Try Preview sound or check tab sound permissions.';render();return Promise.resolve(false);}
 }
 async function preview(){sync();if(!account)return;if(await unlock()){await tone(prefs.sound,prefs.volume);status='Preview requested. If you heard nothing, check the tab mute setting and device volume.';render();}}
 async function ring(sub,events){
  const work=async()=>{
   if(scope()!==sub||!prefs.enabled||!ctx||ctx.state!=='running')return;
   let saved={ids:[],at:0};try{const p=JSON.parse(localStorage.getItem(playedKey(sub))||'null');if(p&&Array.isArray(p.ids))saved={ids:p.ids.filter(x=>typeof x==='string').slice(-1000),at:Number(p.at)||0};}catch{}
   const fresh=events.filter(e=>!saved.ids.includes(e.id));if(!fresh.length)return;
   const now=Date.now();const state={ids:[...new Set([...saved.ids,...fresh.map(e=>e.id)])].slice(-1000),at:Math.max(saved.at,lastLocalPlay)};
   if(now-state.at<2000){try{localStorage.setItem(playedKey(sub),JSON.stringify(state));}catch{}return;}
   state.at=now;try{localStorage.setItem(playedKey(sub),JSON.stringify(state));}catch{}
   lastLocalPlay=now;await tone(prefs.sound,prefs.volume);
  };
  try{if(navigator.locks?.request)await navigator.locks.request('artemis-signal-audio:'+sub,{ifAvailable:true},async lock=>{if(lock)await work();});else await work();}catch{status='Sound could not be played. Check audio permissions in this browser.';render();}
 }
 async function process(input){
  const sub=sync();render();if(!sub||input.account!==sub||input.complete!==true)return;
  const all=Array.isArray(input.events)?input.events:[],eligible=new Set((input.matching||[]).map(e=>e.id));
  if(!initialized){seen=new Set(all.map(e=>e.id));baseline=Date.now();initialized=true;return;}
  const fresh=all.filter(e=>!seen.has(e.id));for(const e of all)seen.add(e.id);
  if(seen.size>12000)seen=new Set([...seen].slice(-10000));
  const recent=fresh.filter(e=>e.type==='NEW'&&eligible.has(e.id)&&typeof e.eventAt==='number'&&Number.isFinite(e.eventAt)&&e.eventAt>=baseline&&e.eventAt<=Date.now()+300000);
  if(!recent.length||!prefs.enabled||!ctx||ctx.state!=='running')return;
  await ring(sub,recent);
 }
 window.artemisSignalSound={ingest(input){const snapshot={account:input.account,complete:input.complete,events:(input.events||[]).map(e=>({...e})),matching:(input.matching||[]).map(e=>({...e}))};queue=queue.then(()=>process(snapshot)).catch(()=>{});return queue;}};
 byId('signalSoundToggle')?.addEventListener('click',async()=>{sync();if(!account)return;prefs.enabled=!prefs.enabled;if(!prefs.enabled)stop();save();if(prefs.enabled)await unlock();});
 byId('signalSoundEnabled')?.addEventListener('change',async e=>{sync();if(!account)return;prefs.enabled=e.target.checked;if(!prefs.enabled)stop();save();if(prefs.enabled)await unlock();});
 byId('signalSoundChoice')?.addEventListener('change',e=>{sync();if(!account)return;prefs.sound=choices[e.target.value]?e.target.value:'bell';save();});
 byId('signalSoundVolume')?.addEventListener('input',e=>{sync();if(!account)return;prefs.volume=Math.max(.1,Math.min(1,Number(e.target.value)||.5));save();});
 byId('signalSoundTest')?.addEventListener('click',preview);
 for(const event of ['pointerdown','keydown'])document.addEventListener(event,e=>{if(e.isTrusted&&sync()&&prefs.enabled)unlock();},{capture:true});
 window.addEventListener('storage',e=>{if(account&&e.key===prefKey(account)){prefs=readPrefs(account);if(!prefs.enabled)stop();status='Updated from another dashboard tab.';render();}});
 document.addEventListener('visibilitychange',()=>{sync();render();});
 sync();render();setInterval(()=>{sync();render();},3000);
})();
