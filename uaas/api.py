from model import gdata
import uuid, json
import datetime, logging
import types

from uaas import genid
from util import Validated

from google.appengine.ext import db
from tenants.api import get_tenant
from decimal import Decimal

@Validated(['tenant_id', 'service_name'])
def add_service(req, response):

  tenant = get_tenant(req, response) 
  if tenant is None:
    response.set_status('404 Tenant Not Found')
    return None

  sdef = get_service(req, response)
  if sdef is not None:
    response.set_status('409 Service Aready Exists Conflict')
    return None

  def create_svc():
    sdef  = gdata.Service(id=genid(), tenant_id =  req['tenant_id'], service_name = req['service_name'])
    sdef.put()

    metrics = req['metrics']

    for metric in metrics:
      m = gdata.Metric(id=genid(), service_id = sdef.id, metric_name=metric['metric_name'], aggregator=metric['aggregator'], uom=metric['uom'])
      m.put()

  create_svc()

  loc= "/tenants/"+req['tenant_id'] +"/services/"+req['service_name']

  response.headers['Location'] = str(loc)
  response.set_status(201)

  return None

@Validated(['tenant_id', 'service_name'])
def get_service(req, response):

  tenant = get_tenant(req, response) 
  if tenant is None:
    response.set_status('404 Tenant Not Found')
    return None

  q  = gdata.Service.all()
  q.filter("tenant_id = ", req['tenant_id'])
  q.filter("service_name = ", req['service_name'])
  results = q.fetch(1000)

  if len(results) != 1:
    response.set_status('404 Service Not Found')
    return None

  service = results[0]

  resp = {"service_name" : service.service_name, "metrics" : []}
  resp['service_id'] = service.id 

  q = gdata.Metric.all()
  q.filter(" service_id = ", service.id)
  results = q.fetch(1000)

  for metric in results:
    mrq = gdata.MetricRate.all()
    mrq.filter("metric_id = " , metric.id)

    mrqr = mrq.fetch(1000)

    if len(mrqr) > 0:
      mr = gdata.to_dict(mrqr[0])
      if mr['selector'] is not None:
        mr['selector'] = json.loads(mr['selector'], parse_float=Decimal)
      resp["metrics"].append({"metric:" : gdata.to_dict(metric), "rate" : mr})
    else:
      resp["metrics"].append({"metric:" : gdata.to_dict(metric) })

  return resp 


@Validated(['tenant_id'])
def list_services(req, response):

  tenant = get_tenant(req, response) 
  if tenant is None:
    response.set_status('404 Tenant Not Found')
    return None

  q  = gdata.Service.all()
  q.filter("tenant_id = ", req['tenant_id'])
  results = q.fetch(1000)

  resp = {}
  resp['tenant_id'] = req['tenant_id']
  resp['services'] = []

  for service in results:
    resp['services'].append( {"service_name" : service.service_name, "service_id": service.id })

  return resp

@Validated(['tenant_id', 'service_name', 'resource_owner', 'resource_id', 'ext_usage_id', 'location', 'event_time', 'usagemetrics'])
def add_usage(req, response):

  tenant = get_tenant(req, response)
  if tenant is None:
    response.set_status('404 Tenant Not Found')
    return None

  sdef = get_service(req, response)

  if sdef is None:
    response.set_status('404 Service Not Found')
    return None

  attrs = None
  if req.has_key('attributes'): attrs = json.dumps(req['attributes'])
 
  u = gdata.Usage(id=genid(), service_id=sdef['service_id'],
              resource_owner = req['resource_owner'], resource_id = req['resource_id'],
              ext_usage_id = req['ext_usage_id'], location=req['location'],
              event_time=datetime.datetime.strptime(req['event_time'], '%Y-%m-%dT%H:%M:%S.%fZ'), attributes=attrs)

  u.put()

  umlist = req['usagemetrics']
  
  for umitem in umlist:
    m = gdata.Metric.all()
    m.filter("service_id = ", sdef['service_id'])
    m.filter("metric_name = ",  umitem['metric_name'])
    r = m.fetch(1000)
    if len(r) > 0:
      mu = r[0]
      um = gdata.UsageMetric(id=genid(), metric_id=mu.id, value=umitem['value'],
                             usage_id=u.id)
      um.put()

  response.headers['Location'] = "/tenants/"+req['tenant_id'] +"/services/"+req['service_name'] + "/usage/" + u.id
  response.set_status(201)

  return None

def get_aggregated_usage(req, response):

  tenant = get_tenant(req, response)
  if tenant is None:
    response.set_status('404 Tenant Not Found')
    return None

  logging.info("Got tenant...")
  svcmap = {}
 
  s = gdata.Service.all()
  s.filter("tenant_id = ", req['tenant_id'])
  sr = s.fetch(1000)

  for si in sr:
    svcmap[si.id] = si.service_name
 
  if len(svcmap.keys()) < 1:
    logging.info("Got NO services...")
    response.set_status('404 A service Not Found')
    return None

  resp = { 'tenant_id' : req['tenant_id'], 'usage' : [] }

  au = gdata.AggregatedUsage.all()
  au.filter("service_id  IN ", svcmap.keys())
  aur = au.fetch(1000)

  for auitem in  au:
    x = gdata.to_dict(auitem)
    x['service_name'] = svcmap[auitem.service_id]
    resp['usage'].append( x)

  return resp

def run_aggregator(req, response):
  gdata.async_aggregate()

def run_rating(req, response):
  gdata.async_rate()

