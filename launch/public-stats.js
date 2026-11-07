/* Public aggregate statistics only. No subscriber token or protected endpoint. */
(function(){
'use strict';
const snapshot={asOfUtc:'2026-11-05',period:'all',summary:{signals:245,targetsReached:{tp1:136,tp2:66,tp3:35},stateCounts:{active:5,completed:151,expired:25,superseded:64,other:0}},byQualityBand:[{name:'90-100',signals:30,targetsReached:{tp1:22,tp2:14,tp3:13}},{name:'80-89',signals:58,targetsReached:{tp1:42,tp2:22,tp3:12}},{name:'70-79',signals:44,targetsReached:{tp1:21,tp2:8,tp3:4}},{name:'0-69',signals:80,targetsReached:{tp1:32,tp2:12,tp3:5}},{name:'unscored',signals:33,targetsReached:{tp1:19,tp2:10,tp3:1}}]};
const $=id=>document.getElementById(id),escape=v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let data=snapshot,source='snapshot',busy=false,lastFetch=0;
const rate=(row,key)=>row.signals?Math.round(1000*row.targetsReached[key]/row.signals)/10:null;
const percent=v=>v===null?'—':v+'%';
function validRow(r){return r&&Number.isInteger(r.signals)&&r.signals>=0&&['tp1','tp2','tp3'].every(k=>Number.isInteger(r.targetsReached?.[k])&&r.targetsReached[k]>=0&&r.targetsReached[k]<=r.signals);}
function validate(d){
 if(!d||d.period!=='all'||!Number.isFinite(Date.parse(d.asOfUtc))||Date.parse(d.asOfUtc)>Date.now()+300000||!validRow(d.summary)||!Array.isArray(d.byQualityBand))throw Error('Invalid aggregate response');
 const allowed=['90-100','80-89','70-79','0-69','unscored'];
 if(d.byQualityBand.length!==5||new Set(d.byQualityBand.map(r=>r.name)).size!==5||d.byQualityBand.some(r=>!allowed.includes(r.name)||!validRow(r)))throw Error('Invalid bands');
 if(d.byQualityBand.reduce((n,r)=>n+r.signals,0)!==d.summary.signals)throw Error('Count mismatch');
 for(const key of ['tp1','tp2','tp3'])if(d.byQualityBand.reduce((n,r)=>n+r.targetsReached[key],0)!==d.summary.targetsReached[key])throw Error('Target mismatch');
 const states=d.summary.stateCounts;if(!states||['active','completed','expired','superseded','other'].some(k=>!Number.isInteger(states[k])||states[k]<0)||Object.values(states).reduce((a,b)=>a+b,0)!==d.summary.signals)throw Error('State mismatch');
 return d;
}
function bar(label,value,n){return '<div class="proof-row"><div class="proof-row-label"><span>'+escape(label)+'</span><span>'+percent(value)+' · n='+escape(n)+'</span></div><div class="proof-track" aria-hidden="true"><i style="width:'+(value??0)+'%"></i></div></div>';}
function render(){
 const band=$('proofBand').value,row=band==='all'?data.summary:data.byQualityBand.find(r=>r.name===band);
 if(!row)return;
 $('proofCards').innerHTML=[['Signals tracked',row.signals,'All records in selected cohort'],...['tp1','tp2','tp3'].map(k=>[k.toUpperCase()+' reached',percent(rate(row,k)),row.targetsReached[k]+' of '+row.signals+' signals'])].map(([label,value,note])=>'<div class="proof-card"><span>'+escape(label)+'</span><strong>'+escape(value)+'</strong><small>'+escape(note)+'</small></div>').join('');
 $('proofTargets').innerHTML=['tp1','tp2','tp3'].map(k=>bar(k.toUpperCase()+' reached',rate(row,k),row.signals)).join('');
 const ordered=['90-100','80-89','70-79','0-69','unscored'].map(name=>data.byQualityBand.find(r=>r.name===name)).filter(Boolean);
 $('proofBands').innerHTML=ordered.map(r=>bar(r.name==='unscored'?'Unscored':'Score '+r.name,rate(r,'tp1'),r.signals)).join('');
 $('proofExact').innerHTML='<table class="proof-table"><caption>All quality bands · exact target counts</caption><thead><tr><th scope="col">Quality</th><th scope="col">Signals</th><th scope="col">TP1</th><th scope="col">TP2</th><th scope="col">TP3</th></tr></thead><tbody>'+ordered.map(r=>'<tr><th scope="row">'+escape(r.name)+'</th><td>'+r.signals+'</td>'+['tp1','tp2','tp3'].map(k=>'<td>'+r.targetsReached[k]+' ('+percent(rate(r,k))+')</td>').join('')+'</tr>').join('')+'</tbody></table>';
 $('proofCoverage').textContent='All-time cohort · '+(band==='all'?'all quality bands':'quality '+band)+' · '+row.signals+' signals. Active, expired and superseded signals remain in the denominator.';
 const c=data.summary.stateCounts;
 $('proofLifecycle').textContent='Across all signals: '+c.active+' active · '+c.completed+' completed · '+c.expired+' expired · '+c.superseded+' superseded · '+c.other+' other.';
}
function showStatus(failed=false){
 if(source==='snapshot'){$('proofStatus').textContent='Recorded snapshot · November 5, 2026 · not a live feed'+(failed?' · live refresh unavailable':'');return;}
 const stale=Date.now()-Date.parse(data.asOfUtc)>15*60*1000;
 $('proofStatus').textContent=(failed?'Refresh unavailable · last recorded data':stale?'Delayed aggregate data':'Connected aggregate feed')+' · updated '+new Date(data.asOfUtc).toLocaleString('en-US',{timeZone:'UTC',timeZoneName:'short'})+(stale?' · older than 15 minutes':'');
}
async function refresh(){
 const endpoint=window.ARTEMIS_PUBLIC_STATS_ENDPOINT;
 if(!endpoint||typeof endpoint!=='string'||!/^https:\/\//i.test(endpoint)){showStatus();return;}
 if(busy)return;busy=true;$('proofRefresh').disabled=true;
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),8000);
 try{const response=await fetch(endpoint,{credentials:'omit',headers:{Accept:'application/json'},signal:controller.signal});if(!response.ok)throw Error('Unavailable');data=validate(await response.json());source='feed';lastFetch=Date.now();render();showStatus();}
 catch(error){showStatus(true);}finally{clearTimeout(timer);busy=false;$('proofRefresh').disabled=false;}
}
$('proofBand').addEventListener('change',render);$('proofRefresh').addEventListener('click',refresh);
$('proofRefresh').hidden=!(typeof window.ARTEMIS_PUBLIC_STATS_ENDPOINT==='string'&&/^https:\/\//i.test(window.ARTEMIS_PUBLIC_STATS_ENDPOINT));
validate(snapshot);render();showStatus();
// Only poll when the public results section is visible.
if('IntersectionObserver' in window){let visible=false;const observer=new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;if(visible&&!document.hidden&&Date.now()-lastFetch>300000)refresh();});observer.observe($('performance-proof'));setInterval(()=>{if(visible&&!document.hidden){showStatus();if(Date.now()-lastFetch>300000)refresh();}},60000);}else refresh();
})();
