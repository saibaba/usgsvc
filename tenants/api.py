from model import gdata
import uuid, json
import datetime, logging
import types

from uaas import genid
from util import Required

from google.appengine.ext import db
from decimal import Decimal

@Required(['email', 'name', 'password'])
def register(req, response):

  q = gdata.Tenant.all()
  q.filter("email = ", req['email'])
  results = q.fetch(1000)

  if len(results) > 0:
    response.set_status(409, "Email unavailable")
    return {"email not available" : req['email']}

  attrs = None
  if 'attributes' in req:
    attrs = json.dumps(req['attributes'])
   
  x = gdata.Tenant(id=genid(), name=req["name"], email=req["email"], api_key=genid(), password=req["password"], attributes=attrs)

  x.put()

  response.headers['Location'] = "/tenants/"+x.id
  response.set_status(201)

  rv = gdata.to_dict(x)
  if rv['attributes'] is None:
      rv['attributes'] = {}
  else:
      rv['attributes'] = json.loads(rv['attributes'],parse_float=Decimal)

  return rv 

def check_app(tenant_id, api_key, password):

  q = gdata.Tenant.all()
  q.filter("id = " , tenant_id)
  q.filter("api_key = " , api_key)
  q.filter("password = " , password)

  results  = q.fetch(1000)

  x = []
  for w in results:
    x.append(w)

  results = x

  #logging.info("Checking: apikey: " + api_key + "; password: " + password + "; tenant: " + tenant_id + "; results=" + str(len(results)))
  
  if len(results) != 1:
    return False
  
  return True

def list_tenants(req, response):

  tenants  = []

  q = gdata.Tenant.all()
  results = q.fetch(1000)
  for p in results:
    item = gdata.to_dict(p)
    if item['attributes'] is None:
      item['attributes'] = {}
    else:
      item['attributes'] = json.loads(item['attributes'], parse_float=Decimal)
    tenants.append(item)
  
  return {"tenants" : tenants }

@Required(['tenant_id'])
def get_tenant(req, response):

  q = gdata.Tenant.all()
  if req is not None:
    q.filter(" id = " , req['tenant_id'])
  results = q.fetch(1000)

  rv = None
  if len(results) == 1:
    rv =  gdata.to_dict(results[0])
    if rv['attributes'] is None:
      rv['attributes'] = {}
    else:
      rv['attributes'] = json.loads(rv['attributes'], parse_float=Decimal)

  return rv

