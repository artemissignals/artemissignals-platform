import copy,importlib.util,json,os,sys,time,types,unittest,uuid
from datetime import datetime,timezone,timedelta
from pathlib import Path
class Conflict(Exception):pass
class Key:
 def __init__(self,name):self.name=name
 def eq(self,value):return self.name,value
class Table:
 def __init__(self,name):self.name=name;self.rows={}
 def get_item(self,Key,**kw):return {'Item':copy.deepcopy(self.rows[tuple(Key.values())])} if tuple(Key.values()) in self.rows else {}
 def query(self,KeyConditionExpression,Limit=100,**kw):
  key,value=KeyConditionExpression;rows=[copy.deepcopy(r) for r in self.rows.values() if r.get(key)==value];rows.sort(key=lambda r:r.get('sk',''),reverse=kw.get('ScanIndexForward') is False)
  return {'Items':rows[:Limit],**({'LastEvaluatedKey':{'more':True}} if len(rows)>Limit else {})}
class DB:
 def __init__(self):self.tables={}
 def Table(self,name):return self.tables.setdefault(name,Table(name))
class Client:
 exceptions=types.SimpleNamespace(TransactionCanceledException=Conflict)
 def __init__(self,db):self.db=db;self.fail=False;self.fail_sent=False
 def transact_write_items(self,TransactItems):
  if self.fail:raise Conflict()
  for x in TransactItems:
   p=x['Put'];new=p['Item'];old=self.db.Table(p['TableName']).rows.get((new['pk'],new['sk']));condition=p['ConditionExpression'];v=p.get('ExpressionAttributeValues',{})
   if condition=='attribute_not_exists(pk)' and old:raise Conflict()
   if condition=='version=:old' and (not old or old['version']!=v[':old']):raise Conflict()
   if '#s=:preview' in condition and (not old or old['state']!=v[':preview'] or old['actorSub']!=v[':actor'] or old['previewExpiresAt']<=v[':now']):raise Conflict()
   if condition=='#s=:old' and (not old or old['state']!=v[':old']):raise Conflict()
   if self.fail_sent and new.get('state')=='SENT':self.fail_sent=False;raise Conflict()
  for x in TransactItems:
   p=x['Put'];n=p['Item'];self.db.Table(p['TableName']).rows[(n['pk'],n['sk'])]=copy.deepcopy(n)
class Cog:
 enabled=True;admin=True;elite=True
 def admin_get_user(self,UserPoolId,Username):return {'Enabled':self.enabled,'UserAttributes':[{'Name':'sub','Value':'admin-sub' if UserPoolId=='admin-pool' else 'pilot'}]}
 def admin_list_groups_for_user(self,UserPoolId,**kw):return {'Groups':[{'GroupName':'ARTEMIS_ADMIN'}] if UserPoolId=='admin-pool' and self.admin else [{'GroupName':'ELITE'}] if UserPoolId=='customer-pool' and self.elite else []}
class Serializer:
 def serialize(self,v):return v
DB_=DB();CLIENT=Client(DB_);COG=Cog()
b=types.ModuleType('boto3');b.resource=lambda name:DB_;b.client=lambda name:{'dynamodb':CLIENT,'cognito-idp':COG,'ssm':types.SimpleNamespace(get_parameter=lambda **kw:{'Parameter':{'Value':'{"bot_token":"fake"}'}})}[name]
sys.modules['boto3']=b;sys.modules['boto3.dynamodb']=types.ModuleType('boto3.dynamodb')
c=types.ModuleType('boto3.dynamodb.conditions');c.Key=Key;sys.modules[c.__name__]=c
t=types.ModuleType('boto3.dynamodb.types');t.TypeSerializer=Serializer;sys.modules[t.__name__]=t
os.environ.update(TABLE='data',LINKS_TABLE='links',ADMIN_POOL='admin-pool',CUSTOMER_POOL='customer-pool',ADMIN_ISSUER='admin-issuer',CUSTOMER_ISSUER='customer-issuer',PILOT_SUB='pilot',SECRET_PARAMETER='secret')
spec=importlib.util.spec_from_file_location('service',Path(__file__).resolve().parents[1]/'backend/service.py');s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
class Tests(unittest.TestCase):
 def setUp(self):
  DB_.Table('data').rows={};DB_.Table('links').rows={('USER#pilot',):{'status':'CONNECTED','deliveryEnabled':True,'chatId':'123','telegramUserId':'123','cognitoUsername':'member','telegramUsername':'member','linkedAt':1},('CHAT#123',):{'ownerSub':'pilot','telegramUserId':'123'}}
  COG.enabled=True;COG.admin=True;COG.elite=True;CLIENT.fail=False;CLIENT.fail_sent=False;self.calls=[];self.fail_send=False
  def tg(token,method,payload):
   self.calls.append((method,payload))
   if method=='getChat':return {'type':'private','id':123}
   if self.fail_send:raise RuntimeError('Ambiguous')
   return {'message_id':7}
  s.telegram=tg
 def event(self,path,method='GET',body=None,admin=True):return {'rawPath':path,'body':json.dumps(body or {}),'requestContext':{'http':{'method':method},'authorizer':{'jwt':{'claims':{'sub':'admin-sub' if admin else 'member','username':'admin','iss':'admin-issuer' if admin else 'customer-issuer'}}}}}
 def draft(self):return s.preview('admin-sub',{'title':'Service update','message':'A reviewed message','recipients':['pilot']})
 def queue(self):d=self.draft();s.send('admin-sub',{'id':d['id'],'confirm':True});return d
 def deliveries(self):return [r for r in s.TABLE.rows.values() if r['pk']=='DELIVERY']
 def notice(self):
  start=datetime.now(timezone.utc);return {'createId':str(uuid.uuid4()),'title':'Maintenance window','message':'Dashboard maintenance','status':'SCHEDULED','severity':'INFO','services':['Dashboard'],'startsAt':start.isoformat(),'endsAt':(start+timedelta(hours=1)).isoformat(),'displayUntil':(start+timedelta(days=1)).isoformat(),'confirm':True}
 def test_unauthenticated_requests(self):
  for path in ('/notices','/admin/communications'):
   self.assertEqual(s.lambda_handler({'rawPath':path,'requestContext':{'http':{'method':'GET'}}},None)['statusCode'],401)
 def test_customer_token_cannot_use_admin(self):self.assertEqual(s.lambda_handler(self.event('/admin/communications',admin=False),None)['statusCode'],401)
 def test_admin_token_cannot_read_customer_route(self):self.assertEqual(s.lambda_handler(self.event('/notices'),None)['statusCode'],401)
 def test_revoked_admin_membership(self):COG.admin=False;self.assertEqual(s.lambda_handler(self.event('/admin/communications'),None)['statusCode'],401)
 def test_preview_never_sends(self):d=self.draft();self.assertEqual(d['recipientCount'],1);self.assertEqual(self.deliveries(),[]);self.assertFalse(self.calls)
 def test_confirmation_required(self):
  d=self.draft()
  with self.assertRaises(ValueError):s.send('admin-sub',{'id':d['id'],'confirm':False})
 def test_send_idempotent_and_immutable(self):
  d=self.draft();s.send('admin-sub',{'id':d['id'],'confirm':True,'message':'Changed'})
  self.assertTrue(s.send('admin-sub',{'id':d['id'],'confirm':True})['alreadyQueued']);self.assertEqual(len(self.deliveries()),1);self.assertIn('A reviewed message',self.deliveries()[0]['text']);self.assertFalse(self.calls)
 def test_preview_expiration(self):
  d=self.draft();s.TABLE.rows[('DRAFT',d['id'])]['previewExpiresAt']=0
  with self.assertRaises(ValueError):s.send('admin-sub',{'id':d['id'],'confirm':True})
 def test_preview_bound_to_actor(self):
  d=self.draft()
  with self.assertRaises(ValueError):s.send('another-admin',{'id':d['id'],'confirm':True})
 def test_disconnect_between_preview_and_send(self):
  d=self.draft();s.LINKS.rows[('USER#pilot',)]['deliveryEnabled']=False
  with self.assertRaises(ValueError):s.send('admin-sub',{'id':d['id'],'confirm':True})
 def test_only_live_rollout_recipient(self):self.assertIsNone(s.recipient('someone-else'))
 def test_worker_sends_and_records_result(self):
  self.queue();self.assertEqual(s.tick(None)['sent'],1);self.assertEqual(self.deliveries()[0]['state'],'SENT');self.assertEqual(s.tick(None)['sent'],0)
 def test_worker_honors_stop(self):
  self.queue();s.LINKS.rows[('USER#pilot',)]['status']='DISCONNECTED';self.assertEqual(s.tick(None)['blocked'],1);self.assertFalse(self.calls)
 def test_worker_honors_entitlement(self):
  self.queue();COG.elite=False;self.assertEqual(s.tick(None)['blocked'],1);self.assertFalse(self.calls)
 def test_ambiguous_send_not_retried(self):
  self.queue();self.fail_send=True;self.assertEqual(s.tick(None)['reviewRequired'],1);self.fail_send=False;s.tick(None);self.assertEqual(sum(m=='sendMessage' for m,p in self.calls),1)
 def test_postsend_write_failure_never_resends(self):
  self.queue();CLIENT.fail_sent=True;self.assertEqual(s.tick(None)['reviewRequired'],1);s.tick(None);self.assertEqual(sum(m=='sendMessage' for m,p in self.calls),1)
 def test_stale_claim_requires_review(self):
  self.queue();r=self.deliveries()[0];r.update(state='SENDING',queueState='SENDING',updatedAt=0);s.TABLE.rows[(r['pk'],r['sk'])]=r;self.assertEqual(s.tick(None)['reviewRequired'],1);self.assertFalse(self.calls)
 def test_audit_failure_prevents_queue(self):
  d=self.draft();CLIENT.fail=True
  with self.assertRaises(Conflict):s.send('admin-sub',{'id':d['id'],'confirm':True})
  self.assertEqual(self.deliveries(),[])
 def test_publication_separate_from_telegram(self):
  n=s.publish('admin-sub',self.notice());self.assertEqual(n['version'],1);self.assertEqual(self.deliveries(),[]);self.assertFalse(self.calls)
 def test_notice_create_idempotent(self):
  body=self.notice();a=s.publish('admin-sub',body);b=s.publish('admin-sub',body);self.assertEqual(a['id'],b['id']);self.assertEqual(b['version'],1)
 def test_notice_version_conflict(self):
  body=self.notice();a=s.publish('admin-sub',body);body.pop('createId');body.update(id=a['id'],expectedVersion=1,status='RESOLVED');b=s.publish('admin-sub',body);self.assertEqual(b['version'],2)
  with self.assertRaises(ValueError):s.publish('admin-sub',body)
 def test_expired_notice_hidden_before_ttl_cleanup(self):
  n=s.publish('admin-sub',self.notice());s.TABLE.rows[('NOTICE',n['id'])]['displayUntil']=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()
  r=s.lambda_handler(self.event('/notices',admin=False),None);self.assertEqual(json.loads(r['body'])['notices'],[]);self.assertIn(('NOTICE',n['id']),s.TABLE.rows)
 def test_invalid_notice_dates_and_services(self):
  for field,value in [('startsAt','2026-11-08T12:00:00'),('services',['TradingAccount']),('displayUntil','2020-01-01T00:00:00Z')]:
   p=self.notice();p[field]=value
   with self.assertRaises(ValueError):s.publish('admin-sub',p)
 def test_stale_pending_announcement_expires(self):
  self.queue();r=self.deliveries()[0];r['sendBefore']=0;s.TABLE.rows[(r['pk'],r['sk'])]=r
  self.assertEqual(s.tick(None)['expired'],1);self.assertFalse(self.calls)
 def test_telegram_unicode_length_validated(self):
  with self.assertRaises(ValueError):s.preview('admin-sub',{'title':'😀'*120,'message':'😀'*2000,'recipients':['pilot']})
 def test_public_notice_omits_actor_data(self):
  n=s.publish('admin-sub',self.notice());self.assertNotIn('updatedBy',n);self.assertNotIn('requestHash',n)
if __name__=='__main__':unittest.main()
