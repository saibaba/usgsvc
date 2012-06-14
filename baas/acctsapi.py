from model import gdata
import json
import logging

from uaas import genid
from util import Required

from tenants.api import get_tenant
from decimal import Decimal

@Required(['tenant_id'])
def list_accounts(req, response):

  qr = gdata.accounts(tenant_id=req['tenant_id']).fetch(100)

  rv = {"accounts" : [] }

  for item in qr:
    a =  gdata.to_dict(item)
    a['attributes'] = json.loads(a['attributes'],parse_float=Decimal)
    rv['accounts'].append(a)

  return rv

@Required(['tenant_id', 'account_no'])
def get_account_json(req, response):

  logging.info("Searching account = %s for tenant = %s" % (req['account_no'], req['tenant_id']) )
  qr = gdata.accounts(tenant_id=req['tenant_id'], account_no=req['account_no']).fetch(100)

  rv = None

  if len(qr) == 1:
    a = gdata.to_dict(qr[0])
    a['attributes'] = json.loads(a['attributes'], parse_float=Decimal)
    rv = a

  return rv

@Required(['tenant_id', 'account_no'])
def get_account(req, response):
  logging.info("Searching account = %s for tenant = %s" % (req['account_no'], req['tenant_id']) )
  qr = gdata.accounts(tenant_id=req['tenant_id'], account_no=req['account_no']).fetch(100)
  if len(qr) == 1:
    return qr[0]
  else:
    return None

@Required(['tenant_id', 'account_no', 'bdom', 'account_name', 'currency'])
def add_account(req, response):

  tenant = get_tenant(req, response) 
  if tenant is None:
    response.set_status('404 Tenant Not Found')
    return None

  adef = get_account(req, response)
  if adef is not None:
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
                          currency = req['currency'],
                          payment_terms = req.get('payment_terms', gdata.PAYTERM_NET30),
                          attributes=attrs
    )
    adef.put()

  create_account()

  loc= "/tenants/"+req['tenant_id'] +"/accounts/"+req['account_no']

  response.headers['Location'] = str(loc)
  response.set_status(201)

  return None

