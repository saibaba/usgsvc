from model import gdata
import uuid, json
import datetime, logging
import types
from copy import deepcopy

from uaas import genid
from util import Validated, subtract_one_month

from tenants.api import list_tenants
from uaas.api import get_service

import baas.acctsapi as aapi

from google.appengine.ext import db

from baas.rating import rate_usage, is_currency
from decimal import Decimal

import yaml

@Validated(['tenant_id', 'service_name'])
def add_rateplan_json(req, response):

  tenant = list_tenants(req, response) 
  if len(tenant) != 1:
    response.set_status('404 Tenant Not Found')
    return None

  sdef = get_service(req, response)
  if sdef is None:
    response.set_status('404 Service ' + req['service_name'] + ' Not Found')
    return None

  in_metrics = req['rateplan']

  for in_metric in in_metrics:
      m = gdata.Metric.all()
      m.filter(" service_id = ", sdef['service_id'])
      if not 'metric_name' in in_metric:
        response.set_status('400 Missing ' + ",".join(['metric_name']))
        return None

      m.filter(" metric_name = ", in_metric['metric_name'])
      mr = m.fetch(1000)
      if len(mr) != 1:
        response.set_status('400 Found too many metrics' + ",".join(['metric_name']))
        return None

      if 'rate' in in_metric:

        for cur in in_metric['rate'].keys():
          mrq = gdata.MetricRate.all() 
          mrq.filter("metric_id = ", mr[0].id)
          mrq.filter("currency = ", cur)
          mrr = mrq.fetch(1000)
  
          r = None
          if len(mrr) == 1:
            r = mrr[0]
            r.rate = in_metric['rate'][cur]
          else:
            r = gdata.MetricRate(metric_id=mr[0].id, currency=cur, rate=in_metric['rate'][cur])

      elif 'selector' in in_metric:

        mrq = gdata.MetricRate.all()
        mrq.filter("metric_id = ", mr[0].id)
        mrr = mrq.fetch(1000)
  
        r = None
        if len(mrr) == 1:
          r = mrr[0]
          r.currency = "*"
          r.selector = json.dumps(in_metric)
        else:
          r = gdata.MetricRate(metric_id=mr[0].id, currency="*", selector=json.dumps(in_metric))
   
      r.put()

  loc= "/tenants/"+req['tenant_id'] +"/services/"+req['service_name']

  response.headers['Location'] = str(loc)
  response.set_status(201)

  return None

def yaml2rateplan(ytext):

    y = yaml.load(ytext)

    result = { 'service_name' : y['service_name'], 'rateplan' : []  }

    for mrp in y['rateplan']:

      dfltcurr = mrp.get('currency', 'USD')

      rp = { 'metric_name' : mrp['metric_name'] }

      toprp = rp

      if not 'selectors' in mrp:
        if 'tiers' in mrp:
          rp['tiers'] = mrp['tiers']
          result['rateplan'].append(rp)
        continue
 
      selectors = mrp['selectors'][:-1] # to exclude the tier pointer

      for sel in selectors:
        rp['selector'] = { "name" : sel , 'value_set' : { "$VALUE$" : { } } }
        rp = rp['selector']['value_set']['$VALUE$']



      for vsl in mrp['value_set']:

        rp = toprp
        
        for vi in range(len(vsl)-1):
          v = vsl[vi]
          tvs = rp['selector']['value_set']
          if v not in tvs:
            tmpl = tvs['$VALUE$']
            tvs[v] = deepcopy(tmpl)  
          rp = tvs[v]

        tier = vsl[len(vsl)-1]
        if type(tier) == types.ListType:
          rp['tiers'] = vsl[len(vsl)-1]
        else:
          print "Using rate: ", tier
         
          rp['tiers'] =  [ { 'name': 'flat rate', 'impacts': [ {'balance_counter' : dfltcurr, 'rate' : float(tier) } ] } ] 

      result['rateplan'].append(toprp)

    return result


@Validated(['tenant_id', 'service_name'])
def add_rateplan_yaml(req, response):
  tenant = list_tenants(req, response) 
  if len(tenant) != 1:
    response.set_status('404 Tenant Not Found')
    return None

  sdef = get_service(req, response)
  if sdef is None:
    response.set_status('404 Service ' + req['service_name'] + ' Not Found')
    return None

  logging.info("yaml received:")
  logging.info(req['body'])

  rpjson = yaml2rateplan(req['body'])

  metric_q = gdata.Metric.all()
  metric_q.filter(" service_id = ", sdef['service_id'])
  metric_r = metric_q.fetch(1000)

  if len(metric_r) > 0:
    for metric in metric_r:
      logging.info("UPDATING METRIC RATE FOR METRIC: " + metric.metric_name)
      metricrate_q = gdata.MetricRate.all() 
      metricrate_q.filter("metric_id = ", metric.id)
      metricrate_r = metricrate_q.fetch(1000)
      if len(metricrate_r) == 1:
        metricrate = metricrate_r[0]
	logging.info("Storing rating plan as selector:")
	logging.info(json.dumps(rpjson))
	metricrate.selector = json.dumps(rpjson)
        metricrate.put()
      elif len(metricrate_r) == 0:
        metricrate = gdata.MetricRate(metric_id=metric.id, selector=json.dumps(rpjson))
        metricrate.put()
      else:	
        response.set_status('400 Found too many metric rates for metric' + metric.metric_name)
	break
  else:
    response.set_status('404 metric Not Found')

  return None

def get_bill_items(bill_id, account_no, currency, acct_attrs, start_date, end_date, balances):
 
  logging.info( "Looking for usage for account: %s between %s and %s" % (account_no, str(start_date), str(end_date)))
  uq = gdata.Usage.all()
  uq.filter("resource_owner = ", account_no)
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

    umq = gdata.UsageMetric.all()
    umq.filter("usage_id = ", u.id)
    logging.info("Searching in UsageMetric having usage_id = " + u.id)
    umql = umq.fetch(1000)
    
    logging.info("Found Usage Metrics:" + str(len(umql)))
 

    # Create one bill item per metric

    for um in umql:
    
      itemtot = 0

      mq = gdata.Metric.all()
      mq.filter("id = " , um.metric_id)
      mr = mq.fetch(1000)
      m = mr[0]
      rq = gdata.MetricRate.all()
      rq.filter("metric_id = ", m.id)
      rr = rq.fetch(1000)
 
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
                     resource_id = u.resource_id, metric_id = um.metric_id,
                     total_charge = str(itemtot))
      items.append(c)
      logging.info("Using bill_item_id " + c.id + " for metric: " + m.metric_name)

      for s in all_subbalances:
        bisb.append(s)

      billtot += itemtot

  return (billtot, items, bisb)

def delete_bill(bill_id):

  bq = gdata.Bill.all()
  bq.filter("id = ", bill_id)
  br = bq.fetch(1000)
  if len(br) > 0:
    b = br[0]
    iq = gdata.BillItem.all()
    iq.filter("bill_id = ", b.id)
    ir = iq.fetch(1000)
    
    for item in ir:
      sq = gdata.BillItemSubBalance.all()
      sq.filter("bill_item_id = ", item.id)
      sr = sq.fetch(1000)
      for s in sr:
        logging.info("DELETING subbalance with id " + s.id)
        db.delete(s)
      logging.info("DELETING item with id " + item.id)
      db.delete(item)
    logging.info("DELETING bill with id " + b.id)
    db.delete(b)

@Validated(['tenant_id', 'account_no'])
def delete_current_bill(req, response):
  tenant = list_tenants(req, response) 
  if len(tenant) != 1:
    response.set_status('404 Tenant Not Found')
    return None

  adef = aapi.get_account(req, response)
  if adef is None:
    response.set_status('404 Account Not Found')
    return None

  end_date = datetime.datetime.utcnow()
  end_date = datetime.date(end_date.year, end_date.month, adef.bdom)
  start_date = subtract_one_month(end_date)

  bq =  gdata.Bill.all()
  bq.filter("from_date = ",start_date)
  bq.filter("to_date = ", end_date)
  bq.filter("account_id = ", adef.id)
 
  br = bq.fetch(1000)

  bill = None

  if len(br) > 0:
    bill = br[0]
   
  if bill is not None:
    delete_bill(bill.id)
    response.set_status('204 No Content')
  else:
    response.set_status('404 Current Bill  Not Found')


@Validated(['tenant_id', 'account_no'])
def create_bill(req, response):

  tenant = list_tenants(req, response) 
  if len(tenant) != 1:
    response.set_status('404 Tenant Not Found')
    return None

  adef = aapi.get_account(req, response)
  if adef is None:
    response.set_status('404 Account Not Found')
    return None

  end_date = datetime.datetime.utcnow()
  end_date = datetime.date(end_date.year, end_date.month, adef.bdom)
  start_date = subtract_one_month(end_date)

  bq =  gdata.Bill.all()
  bq.filter("from_date = ",start_date)
  bq.filter("to_date = ", end_date)
  bq.filter("account_id = ", adef.id)
 
  br = bq.fetch(1000)

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

  return None

@Validated(['tenant_id', 'account_no'])
def get_current_bill(req, response):
  tenant = list_tenants(req, response) 
  if len(tenant) != 1:
    response.set_status('404 Tenant Not Found')
    return None

  adef = aapi.get_account(req, response)
  if adef is None:
    response.set_status('404 Account Not Found')
    return None

  end_date = datetime.datetime.utcnow()
  end_date = datetime.date(end_date.year, end_date.month, adef.bdom)
  start_date = subtract_one_month(end_date)

  bq =  gdata.Bill.all()
  bq.filter("from_date = ",start_date)
  bq.filter("to_date = ", end_date)
  bq.filter("account_id = ", adef.id)
 
  br = bq.fetch(1000)

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

  return resp

@Validated(['tenant_id', 'account_no', 'bill_id'])
def get_bill(req, response):

  tenant = list_tenants(req, response) 
  if len(tenant) != 1:
    logging.warn("Tenant %s not found" % req['tenant_id'])
    response.set_status('404 Tenant not found')
    return None

  adef = aapi.get_account(req, response)
  if adef is None:
    logging.warn("Account %s not found" % req['account_no'])
    response.set_status('404 Account not found')
    return None

  q = gdata.Bill.all()
  q.filter("account_id = ", adef.id)
  q.filter("id = " , req['bill_id'])
  r  = q.fetch(1000)
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

  return resp

@Validated(['tenant_id', 'account_no'])
def list_bills(req, response):

  tenant = list_tenants(req, response) 
  if len(tenant) != 1:
    logging.warn("Tenant %s not found" % req['tenant_id'])
    response.set_status('404 Tenant not found')
    return None

  adef = aapi.get_account(req, response)
  if adef is None:
    logging.warn("Account %s not found" % req['account_no'])
    response.set_status('404 Account not found')
    return None

  q = gdata.Bill.all()
  q.filter("account_id = ", adef.id)
 
  r  = q.fetch(1000)
  resp = { 'account_no' : adef.account_no, 'bills' : [] }

  for bill in r:
    bi = { "bill" : gdata.to_dict(bill), "billitems" : [] }
    iq = gdata.BillItem.all()
    iq.filter("bill_id = " , bill.id)
    ir = iq.fetch(1000)
    for item in ir:
      bi['billitems'].append(gdata.to_dict(item))
    resp['bills'].append(bi)

  response.set_status('200 OK')
  return resp

