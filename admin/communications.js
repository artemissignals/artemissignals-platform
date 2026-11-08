/* Admin-only communications; uses the existing admin sign-in without copying tokens to storage. */
let commDraft=null,commBusy=false,commNoticeCreateId=null;
const commNode=id=>document.getElementById(id);
function commNote(message){commNode('commStatus').textContent=message;}
function commReset(){commInvalidate();commNode('commRecipients').replaceChildren();commNode('commNotices').replaceChildren();commNode('commDeliveries').replaceChildren();commNode('commAudit').replaceChildren();}
function commInvalidate(){commDraft=null;commNode('commSendConfirm').checked=false;commNode('commSendConfirm').disabled=true;commNode('commSend').disabled=true;commNode('commMessagePreview').textContent='Preview again after editing the message or recipients.';}
async function commRequest(path,options={}){
 const base=String(window.ARTEMIS_COMMUNICATIONS_API||'').replace(/\/$/,'');
 if(!/^https:\/\/[a-z0-9]+\.execute-api\.eu-west-2\.amazonaws\.com$/.test(base))throw Error('Deploy communications-config.js to connect this page.');
 if(!accessToken||Date.now()>expiresAt)throw Error('Sign in again before using Communications.');
 const token=accessToken;const response=await fetch(base+path,{...options,headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},cache:'no-store'});
 const body=await response.json().catch(()=>({}));if(accessToken!==token)throw Error('Administrator session changed. Reload Communications.');
 if(!response.ok)throw Error(body.error||('Communications API '+response.status));return body;
}
function commLocal(value){const d=new Date(value);return new Date(d.getTime()-d.getTimezoneOffset()*60000).toISOString().slice(0,16);}
function commNoticeData(){
 const p={title:commNode('commNoticeTitle').value.trim(),message:commNode('commNoticeMessage').value.trim(),status:commNode('commNoticeState').value,severity:commNode('commSeverity').value,services:[...document.querySelectorAll('#commNoticeForm .comm-services input[value]:checked')].map(n=>n.value),startsAt:new Date(commNode('commStarts').value).toISOString(),endsAt:commNode('commEnds').value?new Date(commNode('commEnds').value).toISOString():null,displayUntil:new Date(commNode('commUntil').value).toISOString(),confirm:true};
 if(commNode('commNoticeId').value){p.id=commNode('commNoticeId').value;p.expectedVersion=Number(commNode('commNoticeVersion').value);}else p.createId=commNoticeCreateId;return p;
}
function commNoticePreview(){try{const p=commNoticeData();commNode('commNoticePreview').textContent=p.title+'\n'+p.status+' · '+p.services.join(', ')+'\n'+new Date(p.startsAt).toLocaleString()+(p.endsAt?' → '+new Date(p.endsAt).toLocaleString():'')+'\n\n'+p.message+'\n\nVisible until '+new Date(p.displayUntil).toLocaleString();}catch{commNode('commNoticePreview').textContent='Complete the dates to preview this notice.';}}
function commClearNotice(){commNoticeCreateId=crypto.randomUUID();commNode('commNoticeForm').reset();commNode('commNoticeId').value='';commNode('commNoticeVersion').value='';const t=Date.now();commNode('commStarts').value=commLocal(t);commNode('commEnds').value=commLocal(t+3600000);commNode('commUntil').value=commLocal(t+86400000);commNode('commPublish').textContent='Publish dashboard notice';commNoticePreview();}
function commRecord(parent,title,detail){const box=document.createElement('div');box.className='comm-record';const h=document.createElement('strong');h.textContent=title;const p=document.createElement('p');p.textContent=detail;box.append(h,p);parent.append(box);return box;}
function commEdit(n){commNode('commNoticeId').value=n.id;commNode('commNoticeVersion').value=n.version;commNode('commNoticeTitle').value=n.title;commNode('commNoticeMessage').value=n.message;commNode('commNoticeState').value=n.status;commNode('commSeverity').value=n.severity;commNode('commStarts').value=commLocal(n.startsAt);commNode('commEnds').value=n.endsAt?commLocal(n.endsAt):'';commNode('commUntil').value=commLocal(n.displayUntil);for(const input of document.querySelectorAll('#commNoticeForm .comm-services input[value]'))input.checked=n.services.includes(input.value);commNode('commPublishConfirm').checked=false;commNode('commPublish').textContent='Publish updated notice';commNoticePreview();commNode('commNoticeForm').scrollIntoView({behavior:'smooth',block:'start'});}
async function commNoticeAction(n,action){
 if(commBusy)return;
 const question=action==='delete'?'Delete "'+n.title+'"? It will be removed from the dashboard and notice list. The audit history is retained.':'Mark "'+n.title+'" as work complete? It will remain visible as completed until its display window ends.';
 if(!confirm(question))return;
 commBusy=true;
 try{
  await commRequest('/admin/communications/notices',{method:'POST',body:JSON.stringify({id:n.id,expectedVersion:n.version,action,confirm:true})});
  if(commNode('commNoticeId').value===n.id)commClearNotice();
  commBusy=false;await commLoad();
  commNote(action==='delete'?'Notice deleted. Dashboard updates on its next check. No Telegram message was sent.':'Work marked complete. Dashboard updates on its next check. No Telegram message was sent.');
 }catch(e){commNote(e.message);}finally{commBusy=false;}
}
async function commLoad(){
 if(commBusy)return;commBusy=true;commNote('Loading communications…');commInvalidate();
 try{
  const [state,people]=await Promise.all([commRequest('/admin/communications'),commRequest('/admin/communications/recipients')]);
  commNode('commScope').textContent=people.scope;const recipients=commNode('commRecipients');recipients.replaceChildren();commNode('commAll').checked=false;
  for(const r of people.recipients){const label=document.createElement('label');const input=document.createElement('input');input.type='checkbox';input.value=r.sub;input.addEventListener('change',commInvalidate);label.append(input,document.createTextNode(r.name+' · chat ending '+r.chatLast4));recipients.append(label);}
  if(!people.recipients.length)recipients.textContent='No eligible linked recipients. Connection, delivery enablement, and current Elite membership are required.';
  const notices=commNode('commNotices');notices.replaceChildren();for(const n of state.notices.sort((a,b)=>b.updatedAt.localeCompare(a.updatedAt))){const expired=Date.parse(n.displayUntil)<=Date.now();const card=commRecord(notices,n.title,(n.status==='RESOLVED'?'Work complete':n.status)+' · '+n.services.join(', ')+(expired?' · Expired':'')+'\n'+new Date(n.startsAt).toLocaleString()+'\n'+n.message);const edit=document.createElement('button');edit.className='secondary';edit.textContent='Edit notice';edit.addEventListener('click',()=>commEdit(n));card.append(edit);
   if(n.status==='SCHEDULED'||n.status==='INVESTIGATING'){const complete=document.createElement('button');complete.className='secondary';complete.textContent='Mark work complete';complete.addEventListener('click',()=>commNoticeAction(n,'complete'));card.append(complete);}
   const remove=document.createElement('button');remove.className='secondary';remove.textContent='Delete notice';remove.addEventListener('click',()=>commNoticeAction(n,'delete'));card.append(remove);
  }if(!state.notices.length)notices.textContent='No notices published.';
  const delivery=commNode('commDeliveries');delivery.replaceChildren();for(const r of state.deliveries)commRecord(delivery,r.state,r.recipientName+' · '+new Date(r.createdAt).toLocaleString());if(!state.deliveries.length)delivery.textContent='No announcements queued.';
  if(state.deliveryHistoryHasMore)commRecord(delivery,'Recent results only','Older delivery records are not shown.');
  const audit=commNode('commAudit');audit.replaceChildren();for(const r of state.audit)commRecord(audit,r.action,new Date(r.at).toLocaleString()+' · '+r.target);if(!state.audit.length)audit.textContent='No communication audit events yet.';
  commNote('Loaded. Nothing is published or sent until you explicitly approve it.');
 }catch(e){commNote(e.message);}finally{commBusy=false;}
}
commNode('commRefresh').addEventListener('click',commLoad);
for(const id of ['commTitle','commMessage'])commNode(id).addEventListener('input',commInvalidate);
commNode('commAll').addEventListener('change',e=>{for(const input of commNode('commRecipients').querySelectorAll('input'))input.checked=e.target.checked;commInvalidate();});
commNode('commNoticeForm').addEventListener('input',()=>{commNode('commPublishConfirm').checked=false;commNoticePreview();});
// Confirmation itself must not clear its own checked state.
commNode('commPublishConfirm').addEventListener('input',e=>e.stopPropagation());
commNode('commNoticeClear').addEventListener('click',commClearNotice);
commNode('commGenerate').addEventListener('click',()=>{try{const p=commNoticeData();commNode('commTitle').value=p.title||'Artemis service update';commNode('commMessage').value='Status: '+p.status.toLowerCase()+'\nAffected services: '+p.services.join(', ')+'\nStarts: '+new Date(p.startsAt).toUTCString()+(p.endsAt?'\nEnds: '+new Date(p.endsAt).toUTCString():'')+'\n\n'+p.message;commInvalidate();}catch{commNote('Complete the notice dates before generating a template.');}});
commNode('commPreview').addEventListener('click',async()=>{if(commBusy)return;commBusy=true;commInvalidate();const payload={title:commNode('commTitle').value.trim(),message:commNode('commMessage').value.trim(),recipients:[...commNode('commRecipients').querySelectorAll('input:checked')].map(n=>n.value)};try{const d=await commRequest('/admin/communications/preview',{method:'POST',body:JSON.stringify(payload)});const latest={title:commNode('commTitle').value.trim(),message:commNode('commMessage').value.trim(),recipients:[...commNode('commRecipients').querySelectorAll('input:checked')].map(n=>n.value)};if(JSON.stringify(latest)!==JSON.stringify(payload))throw Error('Draft changed while previewing. Preview again.');commDraft=d;commNode('commMessagePreview').textContent=d.preview+'\n\nRecipients: '+d.recipients.map(r=>r.name+' (…'+r.chatLast4+')').join(', ')+'\nPreview expires '+new Date(d.expiresAt*1000).toLocaleTimeString();commNode('commSendConfirm').disabled=false;commNote('Preview ready. No message has been queued.');}catch(e){commNote(e.message);}finally{commBusy=false;}});
commNode('commSendConfirm').addEventListener('change',()=>commNode('commSend').disabled=!commDraft||!commNode('commSendConfirm').checked);
commNode('commSend').addEventListener('click',async()=>{if(commBusy||!commDraft||!commNode('commSendConfirm').checked)return;if(!confirm('Send this exact announcement to '+commDraft.recipientCount+' selected recipient(s)?'))return;commBusy=true;commNode('commSend').disabled=true;try{const d=await commRequest('/admin/communications/send',{method:'POST',body:JSON.stringify({id:commDraft.id,confirm:true})});commInvalidate();commNote(d.alreadyQueued?'This preview was already queued; no duplicate was created.':'Announcement queued. Refresh in about one minute for delivery results.');}catch(e){commNote(e.message+' Refresh results before attempting another send.');}finally{commBusy=false;}});
commNode('commNoticeForm').addEventListener('submit',async e=>{e.preventDefault();if(commBusy||!commNode('commPublishConfirm').checked)return;commBusy=true;commNode('commPublish').disabled=true;try{const n=await commRequest('/admin/communications/notices',{method:'POST',body:JSON.stringify(commNoticeData())});commNode('commNoticeId').value=n.id;commNode('commNoticeVersion').value=n.version;commNode('commPublishConfirm').checked=false;commNote('Dashboard notice published. No Telegram message was sent.');}catch(e){commNote(e.message);}finally{commBusy=false;commNode('commPublish').disabled=false;}});
commClearNotice();
