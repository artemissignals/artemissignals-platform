"""Artemis service notices and explicitly approved Telegram announcements."""
import base64,hashlib,html,json,os,time,uuid,urllib.request
from datetime import datetime,timezone,timedelta
from decimal import Decimal
import boto3
from boto3.dynamodb.conditions import Key
from boto3.dynamodb.types import TypeSerializer
D=boto3.resource('dynamodb');C=boto3.client('dynamodb');COG=boto3.client('cognito-idp');SSM=boto3.client('ssm')
TABLE=D.Table(os.environ['TABLE']);LINKS=D.Table(os.environ['LINKS_TABLE']);SER=TypeSerializer()
SERVICES={'Dashboard','Signals','Telegram','Market News','Sign-in'}
STATUSES={'SCHEDULED','INVESTIGATING','RESOLVED','CANCELED'}

def now():return datetime.now(timezone.utc)
def iso():return now().isoformat()
def av(item):return {k:SER.serialize(v) for k,v in item.items()}
def get(pk,sk):return TABLE.get_item(Key={'pk':pk,'sk':sk},ConsistentRead=True).get('Item',{})
def response(code,data):return {'statusCode':code,'headers':{'content-type':'application/json','cache-control':'no-store'},'body':json.dumps(data,default=lambda x:int(x) if isinstance(x,Decimal) else str(x))}
def require(ok,message):
    if not ok:raise ValueError(message)
def text(value,minimum,maximum):
    require(isinstance(value,str) and minimum<=len(value.strip())<=maximum,'Invalid text length.')
    require(all(ord(c)>=32 or c in '\n\t' for c in value),'Text contains control characters.')
    return value.strip()
def date(value):
    require(isinstance(value,str),'A date and time with a time zone are required.')
    d=datetime.fromisoformat(value.replace('Z','+00:00'));require(d.tzinfo is not None,'A time zone is required.');return d.astimezone(timezone.utc)
def ident(value):
    require(isinstance(value,str) and len(value)==36,'Invalid record ID.');require(str(uuid.UUID(value))==value,'Invalid record ID.');return value

def query(pk,limit=100):
    result=TABLE.query(KeyConditionExpression=Key('pk').eq(pk),Limit=limit,ScanIndexForward=False,ConsistentRead=True)
    return result.get('Items',[]),bool(result.get('LastEvaluatedKey'))
def all_notices():
    args={'KeyConditionExpression':Key('pk').eq('NOTICE'),'Limit':100,'ConsistentRead':True};rows=[]
    while True:
        page=TABLE.query(**args);rows.extend(page.get('Items',[]))
        if len(rows)>1000:raise RuntimeError('Notice retention limit reached.')
        if not page.get('LastEvaluatedKey'):return rows
        args['ExclusiveStartKey']=page['LastEvaluatedKey']

def audit(actor,action,target,details=None):
    return {'pk':'AUDIT','sk':iso()+'#'+str(uuid.uuid4()),'actorSub':actor,'action':action,'target':target,'details':details or {},'expiresAt':int(time.time())+365*86400}
def put(item,condition='attribute_not_exists(pk)',values=None):
    p={'TableName':TABLE.name,'Item':av(item),'ConditionExpression':condition}
    if values:p['ExpressionAttributeValues']=av(values)
    return {'Put':p}
def transact(actions):C.transact_write_items(TransactItems=actions)

def admin(event):
    claims=event.get('requestContext',{}).get('authorizer',{}).get('jwt',{}).get('claims',{})
    if not claims.get('sub') or claims.get('iss')!=os.environ['ADMIN_ISSUER']:raise PermissionError()
    username=claims.get('username') or claims.get('cognito:username')
    if not username:raise PermissionError()
    user=COG.admin_get_user(UserPoolId=os.environ['ADMIN_POOL'],Username=username)
    attrs={x['Name']:x['Value'] for x in user.get('UserAttributes',[])}
    if not user.get('Enabled') or attrs.get('sub')!=claims['sub']:raise PermissionError()
    args={'UserPoolId':os.environ['ADMIN_POOL'],'Username':username}
    while True:
        r=COG.admin_list_groups_for_user(**args)
        if any(x['GroupName']=='ARTEMIS_ADMIN' for x in r.get('Groups',[])):return claims['sub']
        if not r.get('NextToken'):raise PermissionError()
        args['NextToken']=r['NextToken']

def customer(event):
    claims=event.get('requestContext',{}).get('authorizer',{}).get('jwt',{}).get('claims',{})
    if not claims.get('sub') or claims.get('iss')!=os.environ['CUSTOMER_ISSUER']:raise PermissionError()

def recipient(sub):
    # Initial rollout intentionally stays within the account already enabled for live alerts.
    if sub!=os.environ['PILOT_SUB']:return None
    item=LINKS.get_item(Key={'id':'USER#'+sub},ConsistentRead=True).get('Item',{})
    if item.get('status')!='CONNECTED' or item.get('deliveryEnabled') is not True:return None
    chat=str(item.get('chatId',''));username=item.get('cognitoUsername')
    if not chat.isdigit() or int(chat)<=0 or str(item.get('telegramUserId'))!=chat or not username:return None
    owner=LINKS.get_item(Key={'id':'CHAT#'+chat},ConsistentRead=True).get('Item',{})
    if owner.get('ownerSub')!=sub or str(owner.get('telegramUserId'))!=chat:return None
    user=COG.admin_get_user(UserPoolId=os.environ['CUSTOMER_POOL'],Username=username)
    attrs={x['Name']:x['Value'] for x in user.get('UserAttributes',[])}
    if not user.get('Enabled') or attrs.get('sub')!=sub:return None
    args={'UserPoolId':os.environ['CUSTOMER_POOL'],'Username':username}
    while True:
        r=COG.admin_list_groups_for_user(**args)
        if any(g['GroupName']=='ELITE' for g in r.get('Groups',[])):break
        if not r.get('NextToken'):return None
        args['NextToken']=r['NextToken']
    return {'sub':sub,'chatId':chat,'linkedAt':item.get('linkedAt'),'name':('@'+str(item['telegramUsername'])) if item.get('telegramUsername') else str(item.get('telegramDisplayName') or 'Linked Elite member')}

def preview(actor,body):
    title=text(body.get('title'),3,120);message=text(body.get('message'),1,2000)
    selected=body.get('recipients')
    require(isinstance(selected,list) and 1<=len(selected)<=10 and len(selected)==len(set(selected)),'Select 1–10 eligible recipients.')
    recipients=[]
    for sub in selected:
        r=recipient(sub);require(r is not None,'A selected recipient is no longer eligible. Refresh recipients.');recipients.append(r)
    id_=str(uuid.uuid4());expires=int(time.time())+600
    rendered='ARTEMIS SERVICE UPDATE\n'+title+'\n\n'+message
    require(len(rendered.encode('utf-16-le'))//2<=4096,'Message is too long for Telegram.')
    item={'pk':'DRAFT','sk':id_,'id':id_,'actorSub':actor,'state':'PREVIEW','title':title,'message':message,'rendered':rendered,'recipients':recipients,'createdAt':iso(),'previewExpiresAt':expires,'expiresAt':int(time.time())+90*86400}
    transact([put(item),put(audit(actor,'TELEGRAM_PREVIEW',id_,{'recipientCount':len(recipients)}))])
    return {'id':id_,'preview':rendered,'recipientCount':len(recipients),'recipients':[{'sub':r['sub'],'name':r['name'],'chatLast4':r['chatId'][-4:]} for r in recipients],'expiresAt':expires}

def send(actor,body):
    id_=ident(body.get('id'));require(body.get('confirm') is True,'Explicit confirmation is required.')
    d=get('DRAFT',id_);require(d and d.get('actorSub')==actor,'Preview not found for this administrator.')
    if d['state']=='QUEUED':return {'id':id_,'state':'QUEUED','alreadyQueued':True}
    require(d['state']=='PREVIEW' and int(d['previewExpiresAt'])>time.time(),'Preview expired. Preview the message again.')
    for saved in d['recipients']:
        r=recipient(saved['sub']);require(r and r['chatId']==saved['chatId'] and r.get('linkedAt')==saved.get('linkedAt'),'A recipient connection changed. Create a new preview.')
    d['state']='QUEUED';d['queuedAt']=iso();items=[put(d,'#s=:preview AND actorSub=:actor AND previewExpiresAt>:now')]
    p=items[0]['Put'];p['ExpressionAttributeNames']={'#s':'state'};p['ExpressionAttributeValues']=av({':preview':'PREVIEW',':actor':actor,':now':int(time.time())})
    for r in d['recipients']:
        items.append(put({'pk':'DELIVERY','sk':d['queuedAt']+'#'+id_+'#'+r['sub'],'draftId':id_,'recipientSub':r['sub'],'chatId':r['chatId'],'linkedAt':r.get('linkedAt'),'recipientName':r['name'],'text':d['rendered'],'state':'PENDING','queueState':'PENDING','sendBefore':int(time.time())+3600,'createdAt':d['queuedAt'],'updatedAt':int(time.time()),'expiresAt':int(time.time())+90*86400}))
    items.append(put(audit(actor,'TELEGRAM_QUEUED',id_,{'recipientCount':len(d['recipients'])})))
    transact(items)
    return {'id':id_,'state':'QUEUED','recipientCount':len(d['recipients'])}

def public_notice(n):
    keys=('id','title','message','status','severity','services','startsAt','endsAt','displayUntil','version','updatedAt')
    return {k:n.get(k) for k in keys}

def publish(actor,body):
    id_=ident(body['id']) if body.get('id') else ident(body['createId']) if body.get('createId') else str(uuid.uuid4());old=get('NOTICE',id_)
    request_hash=hashlib.sha256(json.dumps({k:v for k,v in body.items() if k not in ('confirm','createId')},sort_keys=True).encode()).hexdigest()
    if body.get('createId') and old:
        require(old.get('updatedBy')==actor and old.get('requestHash')==request_hash,'This publication request already exists with different content. Reload notices.');return public_notice(old)
    require((not old and not body.get('id')) or old,'Notice not found.')
    version=int(old.get('version',0))
    require((not old) or (type(body.get('expectedVersion')) is int and body.get('expectedVersion')==version),'Notice changed. Reload before editing.')
    require(body.get('confirm') is True,'Explicit publication confirmation is required.')
    status=body.get('status');severity=body.get('severity');services=body.get('services')
    require(status in STATUSES and severity in ('INFO','WARNING','CRITICAL'),'Invalid status or severity.')
    require(isinstance(services,list) and services and set(services)<=SERVICES,'Select affected services.')
    start=date(body.get('startsAt'));end=date(body['endsAt']) if body.get('endsAt') else None;until=date(body.get('displayUntil'))
    require(not end or end>start,'End time must follow start time.')
    require(until>now() and until>start and (not end or until>=end) and until<=now()+timedelta(days=90),'Display-until must follow the notice window and be within 90 days.')
    n={'pk':'NOTICE','sk':id_,'id':id_,'title':text(body.get('title'),3,120),'message':text(body.get('message'),1,2000),'status':status,'severity':severity,'services':sorted(set(services)),'startsAt':start.isoformat(),'endsAt':end.isoformat() if end else None,'displayUntil':until.isoformat(),'version':version+1,'updatedAt':iso(),'updatedBy':actor,'requestHash':request_hash,'expiresAt':int(until.timestamp())+30*86400}
    transact([put(n,'version=:old',{':old':version}) if old else put(n),put(audit(actor,'NOTICE_PUBLISHED',id_,{'status':status,'version':version+1}))])
    return public_notice(n)

def telegram(token,method,payload):
    req=urllib.request.Request('https://api.telegram.org/bot'+token+'/'+method,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=8) as r:result=json.load(r)
    except Exception:raise RuntimeError('Telegram request outcome unavailable.') from None
    if not result.get('ok'):raise RuntimeError('Telegram request rejected.')
    return result['result']

def outcome(item,state,extra=None):
    updated={**item,'state':state,'queueState':state,'updatedAt':int(time.time()),**(extra or {})}
    transact(outcome_actions(updated,item))
def outcome_actions(updated,old):
    action=put(updated,'#s=:old');action['Put']['ExpressionAttributeNames']={'#s':'state'};action['Put']['ExpressionAttributeValues']=av({':old':old['state']})
    return [action,put(audit('SYSTEM','TELEGRAM_'+updated['state'],old['draftId'],{'recipientSub':old['recipientSub']}))]

def tick(context):
    counts={'sent':0,'blocked':0,'reviewRequired':0,'expired':0}
    # A timed-out send is never automatically repeated: its result may be ambiguous.
    stale=TABLE.query(IndexName='queue',KeyConditionExpression=Key('queueState').eq('SENDING'),Limit=10).get('Items',[])
    for item in stale:
        if int(item['updatedAt'])<time.time()-180:
            try:outcome(item,'REVIEW_REQUIRED');counts['reviewRequired']+=1
            except C.exceptions.TransactionCanceledException:pass
    pending=TABLE.query(IndexName='queue',KeyConditionExpression=Key('queueState').eq('PENDING'),Limit=5).get('Items',[])
    token=None
    for item in pending:
        if context and context.get_remaining_time_in_millis()<20000:break
        if int(item.get('sendBefore',0))<=time.time():
            try:outcome(item,'EXPIRED');counts['expired']+=1
            except C.exceptions.TransactionCanceledException:pass
            continue
        r=recipient(item['recipientSub'])
        if not r or r['chatId']!=item['chatId'] or r.get('linkedAt')!=item.get('linkedAt'):
            try:outcome(item,'BLOCKED');counts['blocked']+=1
            except C.exceptions.TransactionCanceledException:pass
            continue
        claiming={**item,'state':'SENDING','queueState':'SENDING','updatedAt':int(time.time())}
        try:transact(outcome_actions(claiming,item))
        except C.exceptions.TransactionCanceledException:continue
        try:
            if token is None:token=json.loads(SSM.get_parameter(Name=os.environ['SECRET_PARAMETER'],WithDecryption=True)['Parameter']['Value'])['bot_token']
            chat=telegram(token,'getChat',{'chat_id':r['chatId']})
            require(chat.get('type')=='private' and str(chat.get('id'))==r['chatId'],'Private recipient verification failed.')
            fresh=recipient(item['recipientSub'])
            require(fresh and fresh['chatId']==r['chatId'] and fresh.get('linkedAt')==r.get('linkedAt'),'Recipient disconnected before send.')
            sent=telegram(token,'sendMessage',{'chat_id':r['chatId'],'text':item['text'],'link_preview_options':{'is_disabled':True}})
            outcome(claiming,'SENT',{'telegramMessageId':sent['message_id']});counts['sent']+=1
        except Exception:
            try:outcome(claiming,'REVIEW_REQUIRED');counts['reviewRequired']+=1
            except Exception:pass
    print(json.dumps({'type':'artemis_admin_telegram_summary',**counts}));return counts

def lambda_handler(event,context):
    if event.get('source')=='artemis.communications.schedule' and not event.get('requestContext'):return tick(context)
    path=event.get('rawPath','');method=event.get('requestContext',{}).get('http',{}).get('method','')
    try:
        if path=='/notices' and method=='GET':
            customer(event);items=all_notices()
            visible=[public_notice(n) for n in items if date(n['displayUntil'])>now()]
            return response(200,{'notices':sorted(visible,key=lambda n:n['startsAt'],reverse=True),'asOfUtc':iso()})
        actor=admin(event)
        if method=='GET' and path=='/admin/communications/recipients':
            r=recipient(os.environ['PILOT_SUB']);return response(200,{'scope':'Current live rollout: selected linked Elite account','recipients':[{'sub':r['sub'],'name':r['name'],'chatLast4':r['chatId'][-4:]}] if r else []})
        if method=='GET' and path=='/admin/communications':
            notices=all_notices();deliveries,more=query('DELIVERY',50);audits,amore=query('AUDIT',30)
            return response(200,{'notices':[public_notice(n) for n in notices],'deliveries':[{k:r.get(k) for k in ('draftId','recipientName','state','createdAt')} for r in deliveries],'deliveryHistoryHasMore':more,'audit':[{'at':a['sk'].split('#')[0],'action':a['action'],'target':a['target']} for a in audits],'auditHasMore':amore})
        raw=event.get('body') or '{}'
        if event.get('isBase64Encoded'):raw=base64.b64decode(raw).decode()
        require(len(raw)<=16384,'Request too large.');body=json.loads(raw);require(isinstance(body,dict),'Invalid request.')
        if method=='POST' and path=='/admin/communications/preview':return response(200,preview(actor,body))
        if method=='POST' and path=='/admin/communications/send':return response(202,send(actor,body))
        if method=='POST' and path=='/admin/communications/notices':return response(200,publish(actor,body))
        return response(404,{'error':'Not found'})
    except PermissionError:return response(401,{'error':'Authorized sign-in required.'})
    except ValueError as e:return response(400,{'error':str(e)})
    except (TypeError,KeyError):return response(400,{'error':'Request invalid. Check required fields and reload before retrying.'})
    except C.exceptions.TransactionCanceledException:return response(409,{'error':'State changed or action already processed. Refresh before retrying.'})
    except Exception:return response(503,{'error':'Communications temporarily unavailable. No automatic resend is attempted.'})
