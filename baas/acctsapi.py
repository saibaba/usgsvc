from model import gdata
import uuid, json
import datetime, logging
import types

from uaas import genid
from util import Validated

from tenants.api import get_tenant
from uaas.api import get_service
from google.appengine.ext import db


@Validated(['tenant_id'])
def list_accounts(req, response):
  q= gdata.Account.all()
  q.filter("tenant_id = ", req['tenant_id'])

  qr = q.fetch(10)

  rv = {"accounts" : [] }

  for item in qr:
    a =  gdata.to_dict(item)
    a['attributes'] = json.loads(a['attributes'])
    rv['accounts'].append(a)

  return rv

@Validated(['tenant_id', 'account_no'])
def get_account_json(req, response):
  q= gdata.Account.all()
  q.filter("tenant_id = ", req['tenant_id'])
  q.filter("account_no = ", req['account_no'])

  logging.info("Searching account = %s for tenant = %s" % (req['account_no'], req['tenant_id']) )
  qr = q.fetch(10)

  rv = None

  if len(qr) == 1:
    a = gdata.to_dict(qr[0])
    a['attributes'] = json.loads(a['attributes'])
    rv = a

  return rv

@Validated(['tenant_id', 'account_no'])
def get_account(req, response):
  q= gdata.Account.all()
  q.filter("tenant_id = ", req['tenant_id'])
  q.filter("account_no = ", req['account_no'])

  logging.info("Searching account = %s for tenant = %s" % (req['account_no'], req['tenant_id']) )
  qr = q.fetch(10)
  if len(qr) == 1:
    return qr[0]
  else:
    return None

@Validated(['tenant_id', 'account_no', 'bdom', 'account_name', 'currency'])
def add_account(req, response):

  tenant = get_tenant(req, response) 
  if tenant == None:
    response.set_status('404 Tenant Not Found')
    return None

  adef = get_account(req, response)
  if adef != None:
    response.set_status('409 Account already exists Conflict')
    return None

  def create_account():
    attrs = None
    if "attributes" in req:
      attrs = json.dumps(req['attributes'])

    adef  = gdata.Account(id=genid(),
                          tenant_id =  req['tenant_id'], 
                          account_name = req['account_name'], 
                          account_no = req['account_no'],
                          bdom = int(req['bdom']),
                          currency = req['currency'], attributes=attrs
    )
    adef.put()

  create_account()

  loc= "/tenants/"+req['tenant_id'] +"/accounts/"+req['account_no']

  response.headers['Location'] = str(loc)
  response.set_status(201)

  return None
