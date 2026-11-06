'use strict';
// Manual device tests only. No caching, push subscription, or automatic signal delivery.
self.addEventListener('install',event=>event.waitUntil(self.skipWaiting()));
self.addEventListener('activate',event=>event.waitUntil(self.clients.claim()));
self.addEventListener('notificationclick',event=>{
 event.notification.close();
 if(event.notification.tag!=='artemis-device-test')return;
 const target=new URL('./',self.registration.scope);target.hash='myalerts';
 event.waitUntil((async()=>{
  const windows=await self.clients.matchAll({type:'window',includeUncontrolled:true});
  const existing=windows.find(client=>{const url=new URL(client.url);return url.origin===target.origin&&url.pathname===target.pathname;});
  if(existing){await existing.navigate(target.href);return existing.focus();}
  return self.clients.openWindow(target.href);
 })());
});
