import os, json, re, hashlib, datetime, secrets, urllib.parse, hmac
import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

table = boto3.resource('dynamodb').Table(os.environ['TABLE_NAME'])
ses = boto3.client('ses')
sender = os.getenv('SENDER_EMAIL','').strip()
verification_base = os.getenv('VERIFICATION_BASE','https://artemissignals.ai').rstrip('/')

def now(): return datetime.datetime.now(datetime.timezone.utc)
def reply(status, message, **fields):
    return {'statusCode':status,'headers':{'Content-Type':'application/json','Cache-Control':'no-store'},'body':json.dumps({'message':message,**fields})}
def digest(s): return hashlib.sha256(s.encode('utf-8')).hexdigest()
def send_email(to,subject,body):
    ses.send_email(Source=sender,Destination={'ToAddresses':[to]},Message={'Subject':{'Data':subject,'Charset':'UTF-8'},'Body':{'Text':{'Data':body,'Charset':'UTF-8'}}})
def handle_signup(event):
    raw=event.get('body') or '{}'
    if len(raw)>6000: return reply(413,'Request too large.')
    try: data=json.loads(raw)
    except (ValueError,TypeError): return reply(400,'Invalid submission.')
    if not isinstance(data,dict): return reply(400,'Invalid submission.')
    if data.get('website'): return reply(200,'Thanks for your interest.')
    email=str(data.get('email') or '').strip().lower()
    name=str(data.get('name') or '').strip()[:81]
    market=str(data.get('market') or 'All').strip()
    consent=data.get('consent') is True
    ref=str(data.get('referral') or '').strip().upper()
    if not re.fullmatch(r'[^\s@]{1,64}@[^\s@]{1,190}\.[^\s@]{2,}',email) or len(email)>254: return reply(400,'Enter a valid email address.')
    if len(name)>80 or market not in ('Forex','Gold','Indices','Crypto','All'): return reply(400,'Please check your details.')
    if not consent: return reply(400,'Please agree to receiving launch updates.')
    if ref and not re.fullmatch(r'[A-Z0-9]{12}',ref): ref=''
    key=digest(email); stamp=now().isoformat()
    existing=table.get_item(Key={'emailHash':key},ConsistentRead=True).get('Item')
    if existing and existing.get('status')=='VERIFIED':
        return reply(200,'If this address is registered, you’re already on the list.')
    code=existing.get('referralCode') if existing else secrets.token_hex(6).upper()
    if not sender:
        item={'emailHash':key,'email':email,'createdAt':existing.get('createdAt',stamp) if existing else stamp,'consentAt':stamp,'consentVersion':'2026-10-09-v1.2','market':market,'source':'launch-website','status':'UNVERIFIED','referralCode':code,'referralCount':existing.get('referralCount',0) if existing else 0}
        if name:item['name']=name
        if ref and ref!=code:item['referredBy']=ref
        table.put_item(Item=item)
        return reply(200,'Thanks! You’re on the early-access list. Email verification will be enabled soon.',verificationRequired=False)
    token=secrets.token_urlsafe(32)
    full_token=key+'.'+token
    expiry=int((now()+datetime.timedelta(hours=24)).timestamp())
    # Capture original referrer only on first signup; don't overwrite existing registrations.
    item={'emailHash':key,'email':email,'createdAt':existing.get('createdAt',stamp) if existing else stamp,'consentAt':stamp,'consentVersion':'2026-10-09-v1.2','market':market,'source':'launch-website','status':'PENDING','referralCode':code,'referralCount':existing.get('referralCount',0) if existing else 0,'verifyTokenHash':digest(token),'verifyExpires':expiry}
    if name:item['name']=name
    if existing and existing.get('referredBy'):item['referredBy']=existing['referredBy']
    elif ref and ref!=code:item['referredBy']=ref
    table.put_item(Item=item)
    url=verification_base+'/verify.html?token='+urllib.parse.quote(full_token)
    try:
        send_email(email,'Confirm your ArtemisSignals early access','Thanks for joining ArtemisSignals.\n\nVerify your email within 24 hours:\n'+url+'\n\nIf you did not request this, ignore this email.\n\nArtemisSignals — Trading involves risk.')
    except Exception:
        # No claimed verification until email really sends; submission remains pending for retry.
        return reply(503,'We could not send the verification email. Please try again shortly.')
    return reply(200,'Check your inbox for a verification link. It expires in 24 hours.',verificationRequired=True)

def handle_verify(event):
    params=event.get('queryStringParameters') or {}
    token=str(params.get('token') or '')
    pieces=token.split('.',1)
    if len(pieces)!=2 or not re.fullmatch('[a-f0-9]{64}',pieces[0]) or len(pieces[1])>100:
        return reply(400,'Invalid verification link.')
    key,raw_token=pieces
    item=table.get_item(Key={'emailHash':key},ConsistentRead=True).get('Item')
    if not item or item.get('status')!='PENDING' or not hmac.compare_digest(str(item.get('verifyTokenHash','')),digest(raw_token)) or int(item.get('verifyExpires',0))<int(now().timestamp()):
        return reply(400,'This verification link is invalid or has expired. Please register again.')
    stamp=now().isoformat()
    try:
        table.update_item(Key={'emailHash':key},UpdateExpression='SET #s=:verified, verifiedAt=:stamp REMOVE verifyTokenHash,verifyExpires',ConditionExpression='#s=:pending AND verifyTokenHash=:token',ExpressionAttributeNames={'#s':'status'},ExpressionAttributeValues={':verified':'VERIFIED',':pending':'PENDING',':stamp':stamp,':token':digest(raw_token)})
    except ClientError as e:
        if e.response['Error']['Code']=='ConditionalCheckFailedException':return reply(400,'This verification link was already used.')
        raise
    referral_url=verification_base+'/?ref='+urllib.parse.quote(item['referralCode'])+'#early-access'
    ref=item.get('referredBy')
    if ref and ref!=item['referralCode']:
        matches=table.query(IndexName='ReferralCodeIndex',KeyConditionExpression=Key('referralCode').eq(ref),Limit=1).get('Items',[])
        if matches and matches[0]['emailHash']!=key and matches[0].get('status')=='VERIFIED':
            table.update_item(Key={'emailHash':matches[0]['emailHash']},UpdateExpression='ADD referralCount :one',ExpressionAttributeValues={':one':1})
    try:
        send_email(item['email'],'Welcome to ArtemisSignals','Your email is confirmed. Welcome to the ArtemisSignals early-access list!\n\nYour referral link:\n'+referral_url+'\n\nWhen someone joins and verifies through your link, it counts as a referral.\n\nYou can withdraw consent by contacting hello@artemissignals.ai.\n\nTrading involves risk.')
    except Exception:
        pass # Verification has succeeded even if welcome message can't send.
    return reply(200,'Your email is verified. Welcome to ArtemisSignals!',referralUrl=referral_url,referralCode=item['referralCode'])

def handler(event,context):
    try:
        http=event.get('requestContext',{}).get('http',{})
        method=http.get('method','')
        path=http.get('path','')
        if method=='POST' and path.endswith('/interest'): return handle_signup(event)
        if method=='GET' and path.endswith('/verify'): return handle_verify(event)
        return reply(404,'Not found.')
    except Exception:
        return reply(500,'An unexpected error occurred. Please try again later.')
