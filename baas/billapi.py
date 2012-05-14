from model import gdata
import uuid, json
import datetime, logging
import types

from uaas import genid
from util import Validated, subtract_one_month

from tenants.api import list_tenants
from uaas.api import get_service

import baas.acctsapi as aapi

from google.appengine.ext import db

from baas.rating import get_rate

@Validated(['tenant_id', 'service_name'])
def add_rateplan_json(req, response):

  tenant = list_tenants(req, response) 
  if len(tenant) != 1:
    response.set_status('404 Tenant Not Found')
    return None

  sdef = get_service(req, response)
  if sdef == None:
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
      mr = m.fetch(10)
      if len(mr) != 1:
        response.set_status('400 Found too many metrics' + ",".join(['metric_name']))
        return None

      if 'rate' in in_metric:

        for cur in in_metric['rate'].keys():
          mrq = gdata.MetricRate.all() 
          mrq.filter("metric_id = ", mr[0].id)
          mrq.filter("currency = ", cur)
          mrr = mrq.fetch(1)
  
          r = None
          if len(mrr) == 1:
            r = mrr[0]
            r.rate = in_metric['rate'][cur]
          else:
            r = gdata.MetricRate(metric_id=mr[0].id, currency=cur, rate=in_metric['rate'][cur])

      elif 'selector' in in_metric:

        mrq = gdata.MetricRate.all()
        mrq.filter("metric_id = ", mr[0].id)
        mrr = mrq.fetch(1)
  
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

def get_bill_items(bill_id, account_no, currency, acct_attrs, start_date, end_date):
 
  logging.info( "Looking for usage for account: %s between %s and %s" % (account_no, str(start_date), str(end_date)))
  uq = gdata.Usage.all()
  uq.filter("resource_owner = ", account_no)
  uq.filter("event_time >= ", start_date)
  uq.filter("event_time < ", end_date)
 
  uqr = uq.fetch(10)

  summary = {}
  ckeys = {}

  logging.info("Found " + str(len(uqr)) + " entries...")
 
  for u in uqr:

    attrs = {}
    for aak in acct_attrs.keys():
      attrs[aak] = acct_attrs[aak]

    if u.attributes != None:
      usg_attrs = json.loads(str(u.attributes))
      for uak in usg_attrs.keys():
        attrs[uak] = usg_attrs[uak]

    umq = gdata.UsageMetric.all()
    umq.filter("usage_id = ", u.id)
    logging.info("Searching in UsageMetric having usage_id = " + u.id)
    umql = umq.fetch(10)
    
    logging.info("Found Usage Metrics:" + str(len(umql)))
  
    for um in umql:

      #ak = "None"
      #if u.attributes != None: ak = u.attributes

      k = u.service_id + "::" + u.resource_id + "::" + um.metric_id + u.attributes

      mq = gdata.Metric.all()
      mq.filter("id = " , um.metric_id)
      mr = mq.fetch(1)
      m = mr[0]
      rq = gdata.MetricRate.all()
      rq.filter("metric_id = ", m.id)
      rq.filter("currency = ", currency)
      rr = rq.fetch(1)
      r = None
      rate = None
 
      if len(rr) != 0:
        r = rr[0]
        rate = int(r.rate)

      else:
        rq = gdata.MetricRate.all()
        rq.filter("metric_id = ", m.id)
        rq.filter("currency = ", "*")
        rr = rq.fetch(1)
        if len(rr) == 0:
          logging.error("Could not find a rate for metric: " + m.metric_name)
          continue   # the loop
        else:
          logging.info("type of attrs: ")
          logging.info ( type(attrs))
          rate  = get_rate(m, currency, attrs)

      if rate == None:
        logging.error("Could not find a rate for metric: " + m.metric_name)
        continue

      if not k in ckeys:
        ckeys[k] = { 'service_id' : u.service_id, 
                     'resource_id' : u.resource_id,
                     'metric_id' : um.metric_id,
                     'rate' : rate
                   }

      summary[k] = int(um.value) + summary.setdefault(k, 0)

  items = []
  
  for k in ckeys.keys():
    total = ckeys[k]['rate'] * summary[k]
    c = gdata.BillItem(id=genid(), bill_id=bill_id,
                     resource_id = ckeys[k]['resource_id'], metric_id = ckeys[k]['metric_id'],
                     unit_price = str(ckeys[k]['rate']), units = str(summary[k]), total_charge = str(total))
                     
    items.append(c)

  return items
 
@Validated(['tenant_id', 'account_no'])
def create_bill(req, response):

  tenant = list_tenants(req, response) 
  if len(tenant) != 1:
    response.set_status('404 Tenant Not Found')
    return None

  adef = aapi.get_account(req, response)
  if adef == None:
    response.set_status('404 Account Not Found')
    return None

  end_date = datetime.datetime.utcnow()
  end_date = datetime.date(end_date.year, end_date.month, adef.bdom)
  start_date = subtract_one_month(end_date)

  bq =  gdata.Bill.all()
  bq.filter("from_date = ",start_date)
  bq.filter("to_date = ", end_date)
  bq.filter("account_id = ", adef.id)
 
  br = bq.fetch(1)

  bill = None
  btot = 0

  if len(br) > 0:
    bill = br[0]
  else:
    acct_attrs = {}
    if adef.attributes != None: 
      acct_attrs = json.loads(adef.attributes)

    bill = gdata.Bill(id=genid(), from_date=start_date, to_date=end_date, account_id=adef.id, bill_total_charge=str(btot))
    items = get_bill_items(bill.id, adef.account_no, adef.currency, acct_attrs, start_date, end_date)

    for item in items:
      logging.info(gdata.to_dict(item))
      item.put()
      btot += int(item.total_charge)
    bill.bill_total_charge = str(btot)
    bill.put()

  loc= "/tenants/"+req['tenant_id'] +"/accounts/"+req['account_no'] +"/bills/"+bill.id

  response.headers['Location'] = str(loc)
  response.set_status(201)

  return None

@Validated(['tenant_id', 'account_no', 'bill_id'])
def get_bill(req, response):

  tenant = list_tenants(req, response) 
  if len(tenant) != 1:
    logging.warn("Tenant %s not found" % req['tenant_id'])
    response.set_status('404 Tenant not found')
    return None

  adef = aapi.get_account(req, response)
  if adef == None:
    logging.warn("Account %s not found" % req['account_no'])
    response.set_status('404 Account not found')
    return None

  q = gdata.Bill.all()
  q.filter("account_id = ", adef.id)
  q.filter("id = " , req['bill_id'])
  r  = q.fetch(1)
  resp = None

  if len(r) == 1:
    bill = r[0]
    bi = { "bill" : gdata.to_dict(bill), "billitems" : [] }
    iq = gdata.BillItem.all()
    iq.filter("bill_id = " , bill.id)
    ir = iq.fetch(10)
    for item in ir:
      bi['billitems'].append(gdata.to_dict(item))
    resp = bi
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
  if adef == None:
    logging.warn("Account %s not found" % req['account_no'])
    response.set_status('404 Account not found')
    return None

  q = gdata.Bill.all()
  q.filter("account_id = ", adef.id)
 
  r  = q.fetch(10)
  resp = { 'account_no' : adef.account_no, 'bills' : [] }

  for bill in r:
    bi = { "bill" : gdata.to_dict(bill), "billitems" : [] }
    iq = gdata.BillItem.all()
    iq.filter("bill_id = " , bill.id)
    ir = iq.fetch(10)
    for item in ir:
      bi['billitems'].append(gdata.to_dict(item))
    resp['bills'].append(bi)

  return resp

