from model import gdata
import json
import datetime, logging

from uaas import genid
from util import Required, subtract_one_month

from tenants.api import list_tenants

import baas.acctsapi as aapi

from google.appengine.ext import db

from baas.rating import rate_usage, is_currency
from decimal import Decimal

from util.monad import Left, Right, do, Just, Nothing, unpack

def get_bill_items(bill_id, account_no, currency, acct_attrs, start_date, end_date, balances):
 
  logging.info( "Looking for usage for account: %s between %s and %s" % (account_no, str(start_date), str(end_date)))
  uq = gdata.usages(resource_owner=account_no)
  uq.filter("event_time >= ", start_date)
  uq.filter("event_time < ", end_date)
 
  uqr = uq.fetch(1000)

  logging.info("Found " + str(len(uqr)) + " entries...")

  billtot = 0
  bisb = []
  items = []

  for u in uqr:
  
    all_subbalances = []

    attrs = {}
    for aak in acct_attrs.keys():
      attrs[aak] = acct_attrs[aak]

    if u.attributes is not None:
      usg_attrs = json.loads(str(u.attributes),parse_float=Decimal)
      for uak in usg_attrs.keys():
        attrs[uak] = usg_attrs[uak]

    logging.info("Searching in UsageMetric for unbilled entries having usage_id = " + u.id)
    umql = gdata.usageMetrics(usage_id=u.id,billed=False).fetch(1000)
    logging.info("Found Usage Metrics:" + str(len(umql)))
 
    # Create one bill item per metric

    for um in umql:
    
      itemtot = 0

      mr = gdata.metrics(id=um.metric_id).fetch(1000)
      m = mr[0]
      rr = gdata.metricRates(metric_id=m.id).fetch(1000)
 
      bill_item_id = genid()

      if len(rr) == 0:
        logging.error("Could not find a rate for metric: " + m.metric_name)
        continue   # the loop
      else:
        rsel = rr[0].selector
        r = json.loads(rsel, parse_float=Decimal)
        subbalances  = rate_usage(r, m.metric_name, balances, attrs, Decimal(um.value), currency)

	for balance_counter in subbalances.keys():
          for il in subbalances[balance_counter]:
            for i in il:
	      cval = None
	      if is_currency(balance_counter): 
                cval = currency
                itemtot += i['balance']
              all_subbalances.append(gdata.BillItemSubBalance(id=genid(),bill_item_id=bill_item_id,currency=cval,
	        balance_counter=balance_counter, charge_tier_name=i['tier_name'],
	        rate=str(i['rate']),quantity=str(i['quantity']), total=str(i['balance'])))


      c = gdata.BillItem(id=bill_item_id, bill_id=bill_id,
                     resource_id = u.resource_id, usage_metric_id = um.id,
                     total_charge = str(itemtot))
      items.append(c)
      logging.info("Using bill_item_id " + c.id + " for metric: " + m.metric_name)

      for s in all_subbalances:
        bisb.append(s)

      billtot += itemtot

  return (billtot, items, bisb)

def delete_bill(bill_id):

  br = gdata.bills(id=bill_id).fetch(1000)
  if len(br) > 0:
    b = br[0]
    ir = gdata.billItems(bill_id=b.id).fetch(1000)
    
    for item in ir:
      sr = gdata.billItemSubBalances(bill_item_id=item.id).fetch(1000)
      for s in sr:
        logging.info("DELETING subbalance with id " + s.id)
        db.delete(s)
      logging.info("DELETING item with id " + item.id)
      db.delete(item)
    logging.info("DELETING bill with id " + b.id)
    db.delete(b)

@Required(['tenant_id', 'account_no'])
@do
def delete_current_bill(req, response):

  j = yield get_tenant(req, response)
  tenant = j >> unpack
  tenant # just to thawrt PEP warning
  j = yield get_account(req, response)
  adef = j >> unpack

  end_date = datetime.datetime.utcnow()
  end_date = datetime.date(end_date.year, end_date.month, adef.bdom)
  start_date = subtract_one_month(end_date)

  br =  gdata.bills(from_date=start_date,to_date=end_date,account_id=adef.id).fetch(1000)

  bill = None

  if len(br) > 0:
    bill = br[0]
   
  if bill is not None:
    delete_bill(bill.id)
    response.set_status('204 No Content')
  else:
    response.set_status('404 Current Bill  Not Found')

  yield Nothing()

@Required(['tenant_id', 'account_no'])
@do
def create_bill(req, response):

  j = yield get_tenant(req, response)
  tenant = j >> unpack
  tenant # just to thawrt PEP warning
  j = yield get_account(req, response)
  adef = j >> unpack

  end_date = datetime.datetime.utcnow()
  end_date = datetime.date(end_date.year, end_date.month, adef.bdom)
  start_date = subtract_one_month(end_date)

  br =  gdata.bills(from_date=start_date, to_date=end_date, account_id=adef.id).fetch(1000)

  bill = None
  btot = 0

  if len(br) > 0:
    bill = br[0]
  else:
    acct_attrs = {}
    if adef.attributes is not None: 
      acct_attrs = json.loads(adef.attributes, parse_float=Decimal)

    bill = gdata.Bill(id=genid(), from_date=start_date, to_date=end_date, account_id=adef.id, bill_total_charge=str(btot))
    balances = {} # TODO

    (btot, items, subbalances) = get_bill_items(bill.id, adef.account_no, adef.currency, acct_attrs, start_date, end_date, balances)

    for item in items:
      logging.info(gdata.to_dict(item))
      item.put()

    for sb in subbalances:
      sb.put()

    bill.bill_total_charge = str(btot)
    bill.put()

  loc= "/tenants/"+req['tenant_id'] +"/accounts/"+req['account_no'] +"/bills/"+bill.id

  response.headers['Location'] = str(loc)
  response.set_status(201)

  yield Nothing()

@do
def get_tenant(req, response):

  tenants = list_tenants(req, response) ['tenants']
  if len(tenants) != 1:
    logging.warn("Tenant %s not found" % req['tenant_id'])
    response.set_status('404 Tenant not found')
    yield Left(Nothing())
  else:
    tenant = tenants[0]
    logging.info("Tenant %s found" % tenant['id'])
    yield Right(Just(tenant))

@do
def get_account(req, response):

  adef = aapi.get_account(req, response)
  if adef is None:
    logging.warn("Account %s not found" % req['account_no'])
    response.set_status('404 Account not found')
    yield Left(Nothing())
  else:
    yield Right(Just(adef))

@Required(['tenant_id', 'account_no'])
@do
def list_bills(req, response):

  j = yield get_tenant(req, response)
  tenant = j >> unpack
  tenant # just to thawrt PEP warning
  j = yield get_account(req, response)
  adef = j >> unpack

  r = gdata.bills(account_id=adef.id).fetch(1000)
  
  resp = { 'account_no' : adef.account_no, 'bills' : [] }

  for bill in r:
    bi = { "bill" : gdata.to_dict(bill), "billitems" : [] }
    ir = gdata.billItems(bill_id=bill.id).fetch(1000)
    for item in ir:
      bi['billitems'].append(gdata.to_dict(item))
    resp['bills'].append(bi)

  response.set_status('200 OK')
  logging.info(resp)
  yield Just(resp)

@Required(['tenant_id', 'account_no', 'bill_id'])
@do
def get_bill(req, response):

  j = yield get_tenant(req, response)
  tenant = j >> unpack
  tenant  # just to thawrt PEP warning
  j = yield get_account(req, response)
  adef = j >> unpack

  r = gdata.bills(account_id=adef.id,id=req['bill_id']).fetch(1000)
  resp = None

  if len(r) == 1:
    bill = r[0]
    bi = { "bill" : gdata.to_dict(bill), "billitems" : [] }
    iq = gdata.BillItem.all()
    iq.filter("bill_id = " , bill.id)
    ir = iq.fetch(1000)
    for item in ir:
      bi['billitems'].append(gdata.to_dict(item))
    resp = bi
    response.set_status('200 OK')
  else:
    response.set_status('404 A bill Not Found')

  yield Just(resp)

@Required(['tenant_id', 'account_no'])
@do
def get_current_bill(req, response):

  j = yield get_tenant(req, response)
  tenant = j >> unpack
  tenant  # just to thawrt PEP warning
  j = yield get_account(req, response)
  adef = j >> unpack

  end_date = datetime.datetime.utcnow()
  end_date = datetime.date(end_date.year, end_date.month, adef.bdom)
  start_date = subtract_one_month(end_date)

  br = gdata.bills(from_date=start_date, to_date=end_date, account_id=adef.id).fetch(1000)

  bill = None
  resp = None

  if len(br) > 0:
    bill = br[0]
   
  if bill is not None:
    bi = { "bill" : gdata.to_dict(bill), "billitems" : [] }
    iq = gdata.BillItem.all()
    iq.filter("bill_id = " , bill.id)
    ir = iq.fetch(1000)
    for item in ir:
      bi['billitems'].append(gdata.to_dict(item))
    resp = bi
    response.set_status('200 OK')
  else:
    response.set_status('404 A bill Not Found')

  yield Just(resp)

