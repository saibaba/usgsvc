import datetime
from google.appengine.ext import db

PAYTERM_NET30  = "30"

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
  selector = db.TextProperty(required=True)
  
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

  billed = db.BooleanProperty(default=False)

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
  payment_terms = db.StringProperty(required=False, default=PAYTERM_NET30)
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
  usage_metric_id = db.StringProperty(required=True)
  total_charge = db.StringProperty(required=True)

class BillItemSubBalance(db.Model):
  id = db.StringProperty(required=True)
  creation_date = db.DateTimeProperty(auto_now_add=True)
  bill_item_id = db.StringProperty(required=True)

  currency = db.StringProperty(required=False)
  balance_counter = db.StringProperty(required=False)
  charge_tier_name = db.StringProperty(required=True)
  rate= db.StringProperty(required=True)
  quantity= db.StringProperty(required=True)
  total= db.StringProperty(required=True)

class BillItemToCharges(db.Model):
  billitem_id = db.StringProperty(required=False)
  charge_id = db.StringProperty(required=False)


def filteredEntity(entity, **filter):
    eq = entity.all()
    for n,v in filter.items():
        eq.filter(n + " = ", v)
    
    return eq

# helpful one-liners

def accounts(**filter):
    return filteredEntity(Account, **filter)

def bills(**filter):
    return filteredEntity(Bill, **filter)

def billItems(**filter):
    return filteredEntity(BillItem, **filter)

def usages(**filter):
    return filteredEntity(Usage, **filter)

def usageMetrics(**filter):
    return filteredEntity(UsageMetric, **filter)

def metrics(**filter):
    return filteredEntity(Metric, **filter)

def metricRates(**filter):
    return filteredEntity(MetricRate, **filter)

def billItemSubBalances(**filter):
    return filteredEntity(BillItemSubBalance, **filter)

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
