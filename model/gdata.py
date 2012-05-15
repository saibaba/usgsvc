import logging

from time import strftime
import datetime
import uuid

from util import genid

from google.appengine.ext import db, deferred
import logging

AGGREGATOR_DELAY = 10

def to_dict(model):
   nvpairs = []
   for p in model.properties():
     attr = getattr(model, p)
     if attr == None:
       attr = None
     else:
       attr = unicode(attr)
     nvpairs.append( (p, attr) )
 
   return dict(nvpairs)
   #return dict([(p, unicode(getattr(model, p))) for p in model.properties()])

class ModelBase(db.Model):
  id = db.StringProperty(required=True)
  creation_date = db.DateTimeProperty(auto_now_add=True)
  created_by = db.StringProperty()
  lastupdate_date = db.DateTimeProperty(auto_now=True)
  lastupdated_by = db.StringProperty()

class Tenant(ModelBase):

  name = db.StringProperty()
  email = db.EmailProperty()
  api_key = db.StringProperty()
  password = db.StringProperty()

  attributes = db.StringProperty(required=False)

class Service(db.Model):

  id = db.StringProperty(required=True)
  creation_date = db.DateTimeProperty(auto_now_add=True)

  tenant_id = db.StringProperty(required=True)
  service_name = db.StringProperty(required=True)

class Metric(db.Model):

  id = db.StringProperty(required=True)
  creation_date = db.DateTimeProperty(auto_now_add=True)

  service_id = db.StringProperty(required=True)
  metric_name = db.StringProperty(required=True)
  aggregator = db.StringProperty(required=True)
  intervalInMinutes = db.IntegerProperty(default=5)
  uom = db.StringProperty(required=True)

class MetricRate(db.Model):

  metric_id = db.StringProperty(required=True)
  selector = db.StringProperty(required=True)
  
class Usage(db.Model):

  id = db.StringProperty(required=True)
  creation_date = db.DateTimeProperty(auto_now_add=True)

  service_id = db.StringProperty(required=True)
  resource_owner = db.StringProperty(required=True)
  resource_id = db.StringProperty(required=True)
  ext_usage_id = db.StringProperty(required=True)
  location = db.StringProperty(required=True)
  event_time = db.DateTimeProperty(required=True, default=datetime.datetime.utcnow())

  attributes = db.StringProperty(required=False)

class UsageMetric(db.Model):

  id = db.StringProperty(required=True)
  creation_date = db.DateTimeProperty(auto_now_add=True)

  usage_id = db.StringProperty(required=True)
  metric_id = db.StringProperty(required=True)
  value = db.StringProperty(required=True)

  aggregated = db.BooleanProperty(default=False)

class AggregatedUsage(db.Model):

  id = db.StringProperty(required=True)
  creation_date = db.DateTimeProperty(auto_now_add=True)

  aggregate_start = db.DateTimeProperty(required=True)
  aggregate_end   = db.DateTimeProperty(required=True)

  service_id =     db.StringProperty(required=True)
  resource_owner = db.StringProperty(required=True)
  resource_id = db.StringProperty(required=True)
  location = db.StringProperty(required=True)

  metric_id = db.StringProperty(required=True)
  value = db.StringProperty(required=True)

  rated = db.BooleanProperty(default=False)

class AggregatedUsageToMetrics(db.Model):
  aggregated_usage_id = db.StringProperty(required=True)
  usage_metric_id = db.StringProperty(required=True)
  
class Charge(db.Model):

  id = db.StringProperty(required=True)
  creation_date = db.DateTimeProperty(auto_now_add=True)
 
  charge_source_id = db.StringProperty(required=True)
  charge_source_table = db.StringProperty(required=True, default="AggregatedUsage")

  unit_price = db.StringProperty(required=True)
  units = db.StringProperty(required=True)
  total_charge = db.StringProperty(required=True)

  billed = db.BooleanProperty(default=False)
  
# ---- billing entities ----------------------------------------

class Account(ModelBase):

  tenant_id = db.StringProperty(required=True)

  account_no = db.StringProperty(required=True)
  bdom = db.IntegerProperty(required=True)
  currency = db.StringProperty(required=True,default="USD")
  account_name = db.StringProperty(required=True)

  attributes = db.StringProperty(required=False)

class Bill(db.Model):
  id = db.StringProperty(required=True)
  creation_date = db.DateTimeProperty(auto_now_add=True)
  account_id = db.StringProperty(required=True)
  from_date = db.DateProperty(required=True)
  to_date = db.DateProperty(required=True)
  bill_total_charge = db.StringProperty(required=True)
 
class BillItem(db.Model):
  id = db.StringProperty(required=True)
  creation_date = db.DateTimeProperty(auto_now_add=True)
  bill_id = db.StringProperty(required=True)

  resource_id = db.StringProperty(required=True)
  metric_id = db.StringProperty(required=True)
  unit_price = db.StringProperty(required=True)
  units = db.StringProperty(required=True)
  total_charge = db.StringProperty(required=True)

class BillItemSubBalances(db.Model):
  id = db.StringProperty(required=True)
  creation_date = db.DateTimeProperty(auto_now_add=True)
  bill_item_id = db.StringProperty(required=True)
 
  balance_counter_name = db.StringProperty(required=True)
  charge_name = db.StringProperty(required=True)
  rate= db.StringProperty(required=True)
  quantity= db.StringProperty(required=True)
  total= db.StringProperty(required=True)

class BillItemToCharges(db.Model):
  billitem_id = db.StringProperty(required=False)
  charge_id = db.StringProperty(required=False)

#-----------------------------------------------------------------

def do_something_expensive(a, b, c=None):
  #logging.info( "******* Doing something expensive - aggregate!")

  PERIOD = 5 
  summary = {}
  ckeys = {}
  umlist = {}
 
  def process(um, metric):

    logging.info("Metric aggregator to use:  "  + metric.aggregator)

    u = Usage.all()
    u.filter("id = ", um.usage_id)
    ur = u.fetch(1)
    if len(ur) == 0:
      logging.warn("Aggregator could not find the usage id for usage metric!")
      return
    u = ur[0]

    timek = u.event_time.strftime('%Y-%m-%d-%H') + "-" + str(u.event_time.minute - (u.event_time.minute % PERIOD))

    k = u.service_id + "::" + u.resource_owner + "::" + u.resource_id + "::" + u.location + "::" + um.metric_id + "::" + timek
    #u.event_time.strftime('%Y-%m-%d-%H-%M')

    summary[k] = int(um.value) + summary.setdefault(k, 0)
    if not ckeys.has_key(k):
       ckeys[k] = { 'service_id' : u.service_id,
                    'resource_owner' : u.resource_owner,
                    'resource_id' : u.resource_id,
                    'location' : u.location,
                    'metric_id' : um.metric_id,
                    'timek' : timek }

    if not umlist.has_key(k):
      umlist[k] = { 'umids'  : [], 'auid' : None }

    umlist[k]['umids'].append(um.id)
    um.aggregated = True
    um.put()

  q = UsageMetric.all()
  q.filter("aggregated = ", False)
  dt = datetime.datetime.utcnow()
  dt = datetime.datetime(dt.year, dt.month, dt.day, dt.hour, dt.minute)

  q.filter("creation_date < ", dt)
  results =  q.fetch(10)

  for item in results:
    m  = Metric.all()
    m.filter("id =", item.metric_id)
    mr = m.fetch(10)
    if len(mr) != 1:
      logging.error("UsageMetric does not resolve to a single metric but: " + len(mr))
    else:
      process(item, mr[0])

  for k in summary:
    logging.info(k + "=>" + str(summary[k]))
    stflds = ckeys[k]['timek'].split("-")
    st = datetime.datetime(int(stflds[0]), int(stflds[1]), int(stflds[2]), int(stflds[3]), int(stflds[4]))
    et = st + datetime.timedelta(0, PERIOD*60, 0)

    au = AggregatedUsage(id = genid(), 
         aggregate_start=st,
         aggregate_end=et,
         service_id = ckeys[k]['service_id'],
         resource_owner = ckeys[k]['resource_owner'],
         resource_id = ckeys[k]['resource_id'],
         location = ckeys[k]['location'],
         metric_id = ckeys[k]['metric_id'],
         value = str(summary[k])
    )
    au.put()
    umlist[k]['auid'] = au.id

    # now need to write all umlist to assoc table

def do_rating(a, b, c=None):
  #logging.info( "******* Doing something expensive - rating!")

  PERIOD = 5 
  summary = {}
  ckeys = {}
 
  def process(au, metric):

    mrq = MetricRate.all()
    mrq.filter("metric_id = ", m.id)
    mrq.filter("currency = ", "USD")
    mrr = mrq.fetch(1)
    r = mrr[0]
    
    tc = "0"
    if (r.rate != None and len(r.rate) > 0):
      tc = int(r.rate) * int(au.value)

    charge = Charge(id=genid(), 
                    charge_source_id=au.id,
                    charge_source_table = "AggregatedUsage",
                    unit_price = r.rate,
                    units = au.value,
                    total_charge = str(tc))
    charge.put()

    au.rated = True
    au.put()

  q = AggregatedUsage.all()
  q.filter("rated = ", False)
  results =  q.fetch(10)

  for au in results:
    m  = Metric.all()
    m.filter("id =", au.metric_id)
    mr = m.fetch(10)
    if len(mr) != 1:
      logging.error("Aggregated does not resolve to a single metric but: " + len(mr))
    else:
      process(au, mr[0])
  
def async_aggregate():
  deferred.defer(do_something_expensive, "Hello, deferred aggregation world!", 42, c=None, _countdown=AGGREGATOR_DELAY)

def async_rate():
  deferred.defer(do_rating, "Hello, deferred rating world!", 42, c=None, _countdown=AGGREGATOR_DELAY)



"""
At registration:
{
  "attributes": [
    { "displayName" : "Bandwidth In",
    }
  ]
}

At aggreate read time request with:
{
  "tenantId" : "12312-13121",
  "serviceName" : "Cloud Servers",
  "resourceOwner": "acct #1",
  "resourceId" : "cs1",
}

Response would be:

{
  "tenantId" : "12312-13121",
  "serviceName" : "Cloud Servers",
  "resourceOwner": "acct #1",
  "resourceId" : "cs1",
  "startEventTime" : "2012-...",
  "endEventTime" : "2012-...",

  "attributes": [
    { "displayName" : "Bandwidth In",
    }
  ]

  "usageMetrics": [
    { "name" : "Bandwidth In",
      "aggregator" : "Sum",
      "UoM" : "GB",
      "value" : 10
    },
    { "name" : "Bandwidth Out",
      "aggregator" : "Sum",
      "UoM" : "GB",
      "value" : 10
    },
    { "name" : "Duration",
      "aggregator" : "Sum",
      "UoM" : "Hour",
      "value" : 5
    }
  ]
  
}
"""
