/* Authenticated service notices. Network failures never imply that maintenance is clear. */
(()=>{
 let busy=false,lastAccount=null;
 const content=document.getElementById('maintenanceContent'),indicator=document.getElementById('maintenanceIndicator');
 const banner=document.createElement('div');banner.id='serviceNoticeBanner';banner.hidden=true;banner.setAttribute('role','status');banner.style.cssText='margin:12px 0;padding:13px 16px;border:1px solid var(--brand);border-radius:12px;background:var(--amber-bg);font-size:12px;white-space:pre-wrap;';
 const root=document.getElementById('appRoot');if(root){const header=root.querySelector('header');header?header.insertAdjacentElement('afterend',banner):root.prepend(banner);}
 function message(title,body){content.replaceChildren();const h=document.createElement('strong');h.textContent=title;const p=document.createElement('p');p.textContent=body;content.append(h,p);}
 function render(notices){
  const valid=notices.filter(n=>Date.parse(n.displayUntil)>Date.now());
  content.replaceChildren();
  if(!valid.length){indicator.className='status-pill ok';indicator.textContent='No notices';message('No current service notices','No maintenance or incident notices are currently published. This is separate from automated service health checks.');banner.hidden=true;return;}
  indicator.className='status-pill unknown';indicator.textContent=valid.length+' notice'+(valid.length===1?'':'s');
  for(const n of valid.sort((a,b)=>Date.parse(a.startsAt)-Date.parse(b.startsAt))){
   const article=document.createElement('article');article.style.cssText='padding:12px 0;border-bottom:1px solid var(--line)';const h=document.createElement('strong');h.textContent=n.title;const state=document.createElement('p');state.textContent=(n.status==='RESOLVED'?'Work complete':n.status.toLowerCase())+' · '+n.severity.toLowerCase()+' · '+n.services.join(', ');const dates=document.createElement('p');dates.textContent=new Date(n.startsAt).toLocaleString()+(n.endsAt?' → '+new Date(n.endsAt).toLocaleString():'');const body=document.createElement('p');body.textContent=n.message;body.style.whiteSpace='pre-wrap';article.append(h,state,dates,body);content.append(article);
  }
  const active=valid.filter(n=>(n.status==='INVESTIGATING'||n.status==='SCHEDULED')&&Date.parse(n.startsAt)<=Date.now()&&(n.status==='INVESTIGATING'||!n.endsAt||Date.parse(n.endsAt)>Date.now()));
  banner.hidden=!active.length;banner.textContent=active.map(n=>n.title+' · '+n.services.join(', ')+'\n'+n.message).join('\n\n');
 }
 async function load(){
  const token=sessionStorage.getItem('artemis_id_token');
  if(!token){lastAccount=null;banner.hidden=true;indicator.className='status-pill unknown';indicator.textContent='Not checked';message('Sign in to view service notices','Your sign-in is required to retrieve current notices.');return;}
  if(busy)return;busy=true;const account=typeof decodeJwt==='function'?decodeJwt(token).sub:token;
  if(lastAccount!==account){banner.hidden=true;message('Checking service notices…','Retrieving published maintenance and incident notices.');lastAccount=account;}
  try{
   const base=String(window.ARTEMIS_COMMUNICATIONS_API||'').replace(/\/$/,'');if(!/^https:\/\/[a-z0-9]+\.execute-api\.eu-west-2\.amazonaws\.com$/.test(base))throw Error('The notice feed has not been connected.');
   const response=await artemisFetch(base+'/notices',{headers:{Authorization:'Bearer '+token,Accept:'application/json'},cache:'no-store'});
   if(sessionStorage.getItem('artemis_id_token')!==token)return;
   if(!response.ok)throw Error('Notice feed returned HTTP '+response.status);const body=await response.json();if(!Array.isArray(body.notices))throw Error('Unexpected notice response.');render(body.notices);
  }catch(e){if(sessionStorage.getItem('artemis_id_token')!==token)return;banner.hidden=true;indicator.className='status-pill unknown';indicator.textContent='Unavailable';message('Service notices unavailable','We could not verify current notices. Try Check now again.');}finally{busy=false;}
 }
 document.getElementById('refreshStatus').addEventListener('click',load);
 window.artemisLoadServiceNotices=load;
 setInterval(load,60000);
 load();
})();
