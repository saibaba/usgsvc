import logging
import json
import tenants.api as api
import webapp2
import types

def authenticate(handler):
 
  handler.response.clear() 
  tl = handler.request.path.split("/")
  tenant_id = tl[2]

  rp = True
  rh = handler.request.headers
  if not 'X-Auth-Apikey' in rh:
    rp = False
  if not 'X-Auth-Password' in rh:
    rp = False

  if not rp:
    logging.warn("Auth Credentials Not Found")
    handler.response.set_status('401 Auth Credentials Not Found')
    return None

  api_key = rh['X-Auth-Apikey']
  password = rh['X-Auth-Password']

  tenant = api.get_tenant({'tenant_id'  : tenant_id}, handler.response)

  if tenant is not None:
    rp = api.check_app(tenant_id, api_key, password)
    if not rp:
      logging.warn("Invalid Auth Credentials")
      handler.response.status = '401 Invalid Auth credentials'
  else:
    logging.warn("Tenant not found")
    handler.response.status = '404 Tenant Not Found'

  return rp

class Authenticated(object):
    def __init__(self, f):
        self.f = f
  
    def __get__(self, obj, ownerClass=None):
        return types.MethodType(self, obj)

    def __call__(self, *args, **kwargs):
        rv = authenticate(*args, **kwargs)
        if rv:
          return self.f(*args, **kwargs)
