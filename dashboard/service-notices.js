/* Authenticated notices: status, severity and explicit impact remain distinct. */
(()=>{
 let busy=false,lastAccount=null;
 const content=document.getElementById('maintenanceContent'),indicator=document.getElementById('maintenanceIndicator');if(!content||!indicator)return;
 const style=document.createElement('style');style.textContent=`
 #maintenanceContent{border-style:solid;padding:12px!important}.sn-card{border:1px solid var(--line,#29465a);border-left:3px solid var(--sn-accent,#90aec6);border-radius:10px;padding:14px 16px;background:var(--card2,#0c1b2a);margin:0 0 10px}.sn-card:last-child{margin-bottom:0}.sn-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;flex-wrap:wrap}.sn-title{display:flex;align-items:center;gap:9px;font-size:13px;line-height:1.5;font-weight:700}.sn-icon{display:inline-flex;flex-shrink:0;color:var(--sn-accent,#90aec6)}.sn-icon svg{width:18px;height:18px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}.sn-badges{display:flex;gap:6px;flex-wrap:wrap}.sn-badge{font-size:10px;line-height:1.4;padding:4px 7px;border:1px solid currentColor;border-radius:999px;white-space:nowrap}.sn-muted{color:var(--muted,#abc0d2)}.sn-blue{color:#81baff}.sn-green{color:#69d8be}.sn-amber{color:#ffc078}.sn-red{color:#ff9999}.sn-meta{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:11px;color:var(--muted,#abc0d2);margin-top:7px;line-height:1.6}.sn-body{font-size:12px;line-height:1.65;margin:10px 0 0!important;white-space:pre-wrap;overflow-wrap:anywhere}.sn-resolution{border-left:2px solid #69d8be;padding-left:10px}.sn-original{margin-top:10px;font-size:11px;color:var(--muted,#abc0d2)}.sn-original summary,.sn-recent>summary{cursor:pointer;min-height:28px;line-height:28px}.sn-recent>summary{font-size:12px;font-weight:600;color:var(--muted,#abc0d2);margin:3px 0 8px}.sn-card p{margin-bottom:0}.sn-card details p{font-size:12px}.sn-empty{font-size:12px;line-height:1.6;padding:5px}.sn-empty strong{display:block;margin-bottom:5px}@media(max-width:600px){.sn-card{padding:12px}.sn-head{gap:8px}.sn-badges{margin-left:27px}.sn-meta{display:block}.sn-meta span{display:block}}`;
 document.head.append(style);
 const paths={check:'<path d="m5 12 4 4L19 6"/>',info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/>',warning:'<path d="m12 3 10 18H2L12 3Z"/><path d="M12 9v5M12 17h.01"/>',calendar:'<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4M17 3v4M3 10h18M8 14h3"/>',cancel:'<circle cx="12" cy="12" r="9"/><path d="m8 8 8 8m0-8-8 8"/>'};
 function el(tag,className,text){const n=document.createElement(tag);if(className)n.className=className;if(text!==undefined)n.textContent=text;return n;}
 function icon(name){const n=el('span','sn-icon');n.setAttribute('aria-hidden','true');n.innerHTML='<svg viewBox="0 0 24 24">'+(paths[name]||paths.info)+'</svg>';return n;}
 function badge(text,tone){return el('span','sn-badge sn-'+tone,text);}
 function ms(value){const n=Date.parse(value);return Number.isFinite(n)?n:null;}
 function stamp(value){const d=ms(value);if(d===null)return 'Time unavailable';return new Date(d).toLocaleString(undefined,{month:'short',day:'numeric',year:new Date(d).getFullYear()!==new Date().getFullYear()?'numeric':undefined,hour:'2-digit',minute:'2-digit'});}
 function windowText(n){const start=ms(n.startsAt),end=ms(n.endsAt);if(start===null)return 'Window not specified';const date=new Date(start);const day=date.toLocaleDateString(undefined,{month:'short',day:'numeric',year:date.getFullYear()!==new Date().getFullYear()?'numeric':undefined});const clock=t=>new Date(t).toLocaleTimeString(undefined,{hour:'2-digit',minute:'2-digit'});if(end===null)return day+' · '+clock(start);return date.toDateString()===new Date(end).toDateString()?day+' · '+clock(start)+'–'+clock(end):stamp(n.startsAt)+' → '+stamp(n.endsAt);}
 const terminal=n=>['RESOLVED','CANCELED'].includes(n.status);
 const priority=n=>n.status==='INVESTIGATING'?0:n.status==='SCHEDULED'&&(ms(n.startsAt)||0)<=Date.now()?1:2;
 function card(n){
  const complete=n.status==='RESOLVED',canceled=n.status==='CANCELED',investigating=n.status==='INVESTIGATING';
  const state=complete?['Completed','check','green','#69d8be']:canceled?['Canceled','cancel','muted','#90aec6']:investigating?['Investigating','warning','amber','#ffc078']:['Scheduled','calendar','blue','#81baff'];
  const article=el('article','sn-card');article.style.setProperty('--sn-accent',state[3]);
  const head=el('div','sn-head'),title=el('div','sn-title');title.append(icon(state[1]),el('strong','',n.title));
  const badges=el('div','sn-badges');badges.append(badge(state[0],state[2]));
  const severity={INFO:['Information','blue'],WARNING:['Warning','amber'],CRITICAL:['Critical notice','red']}[n.severity]||['Unspecified severity','muted'];badges.append(badge(...severity));
  const created=ms(n.createdAt);if(!terminal(n)&&created!==null&&created<=Date.now()&&created>Date.now()-86400000)badges.append(badge('New','blue'));
  head.append(title,badges);article.append(head);
  const meta=el('div','sn-meta');meta.append(el('span','', 'Services: '+n.services.join(' · ')),el('span','', 'Window: '+windowText(n)));
  const impacts={UNKNOWN:'Not specified',NONE_EXPECTED:'No disruption expected',DEGRADED:'Service may be degraded',OUTAGE:'Confirmed service disruption'};
  meta.append(el('span',n.impact==='OUTAGE'&&!terminal(n)?'sn-red':'','Reported impact: '+(impacts[n.impact]||impacts.UNKNOWN)));
  if(complete&&ms(n.completedAt)!==null)meta.append(el('span','','Completed: '+stamp(n.completedAt)));
  article.append(meta);
  if(complete){
   article.append(el('p','sn-body sn-resolution',n.resolutionNote||'Work marked complete. No completion note was recorded.'));
   const original=el('details','sn-original');original.append(el('summary','','Original notice'),el('p','sn-body',n.message));article.append(original);
  }else article.append(el('p','sn-body',n.message));
  return article;
 }
 const banner=el('div');banner.id='serviceNoticeBanner';banner.hidden=true;banner.setAttribute('role','status');banner.style.cssText='margin:12px 0;padding:11px 14px;border:1px solid var(--brand);border-radius:10px;background:var(--amber-bg);font-size:12px;white-space:pre-wrap;';
 const root=document.getElementById('appRoot');if(root){const header=root.querySelector('header');header?header.insertAdjacentElement('afterend',banner):root.prepend(banner);}
 function message(title,body){content.replaceChildren();const box=el('div','sn-empty');box.append(el('strong','',title),el('span','',body));content.append(box);}
 function render(notices){
  if(notices.some(n=>!n||typeof n.title!=='string'||typeof n.message!=='string'||!Array.isArray(n.services)||ms(n.displayUntil)===null||!['SCHEDULED','INVESTIGATING','RESOLVED','CANCELED'].includes(n.status)))throw Error('Unexpected notice data.');
  const valid=notices.filter(n=>ms(n.displayUntil)>Date.now()),open=valid.filter(n=>!terminal(n)).sort((a,b)=>priority(a)-priority(b)||(ms(a.startsAt)||0)-(ms(b.startsAt)||0)),past=valid.filter(terminal).sort((a,b)=>(ms(b.completedAt)||ms(b.updatedAt)||0)-(ms(a.completedAt)||ms(a.updatedAt)||0));
  content.replaceChildren();
  if(!valid.length){indicator.className='status-pill ok';indicator.textContent='No notices';message('No current service notices','No maintenance or incident notices are currently published. Automated service health checks are shown separately.');banner.hidden=true;return;}
  const completed=past.filter(n=>n.status==='RESOLVED').length;
  indicator.className='status-pill '+(open.length?'unknown':'ok');indicator.textContent=open.length?open.length+' open notice'+(open.length===1?'':'s')+(completed?' · '+completed+' completed':''):completed===past.length?completed+' completed update'+(completed===1?'':'s'):past.length+' past update'+(past.length===1?'':'s');
  for(const n of open)content.append(card(n));
  if(past.length){const details=el('details','sn-recent');details.open=past.some(n=>(ms(n.completedAt)||ms(n.updatedAt)||0)>Date.now()-86400000);details.append(el('summary','','Recent updates ('+past.length+')'));for(const n of past)details.append(card(n));content.append(details);}
  const active=open.filter(n=>ms(n.startsAt)!==null&&ms(n.startsAt)<=Date.now()&&(n.status==='INVESTIGATING'||!n.endsAt||ms(n.endsAt)>Date.now())&&(n.status==='INVESTIGATING'||['WARNING','CRITICAL'].includes(n.severity)||['DEGRADED','OUTAGE'].includes(n.impact)));
  banner.hidden=!active.length;banner.textContent=active.map(n=>(n.status==='INVESTIGATING'?'⚠ Investigating: ':'◷ Maintenance: ')+n.title+' · '+n.services.join(', ')+'\n'+n.message).join('\n\n');
 }
 function currentAccount(){const token=sessionStorage.getItem('artemis_id_token');if(!token)return '';try{return typeof decodeJwt==='function'?(decodeJwt(token).sub||''):token;}catch{return '';}}
 async function load(){
  const token=sessionStorage.getItem('artemis_id_token'),account=currentAccount();
  if(!token||!account){lastAccount=null;banner.hidden=true;indicator.className='status-pill unknown';indicator.textContent='Not checked';message('Sign in to view service notices','Your sign-in is required to retrieve current notices.');return;}
  if(busy)return;busy=true;
  if(lastAccount!==account){banner.hidden=true;message('Checking service notices…','Retrieving published maintenance and incident notices.');lastAccount=account;}
  try{
   const base=String(window.ARTEMIS_COMMUNICATIONS_API||'').replace(/\/$/,'');if(!/^https:\/\/[a-z0-9]+\.execute-api\.eu-west-2\.amazonaws\.com$/.test(base))throw Error('Notice feed not connected.');
   const response=await artemisFetch(base+'/notices',{headers:{Authorization:'Bearer '+token,Accept:'application/json'},cache:'no-store'});
   if(currentAccount()!==account)return;
   if(!response.ok)throw Error('Notice feed returned HTTP '+response.status);const body=await response.json();if(!Array.isArray(body.notices))throw Error('Unexpected notice response.');render(body.notices);
  }catch(e){if(currentAccount()!==account)return;banner.hidden=true;indicator.className='status-pill unknown';indicator.textContent='Unavailable';message('Service notices unavailable','We could not verify current notices. Try Check now again.');}finally{busy=false;}
 }
 document.getElementById('refreshStatus')?.addEventListener('click',load);window.artemisLoadServiceNotices=load;setInterval(load,60000);load();
})();
