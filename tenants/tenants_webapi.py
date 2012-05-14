import logging
import json
import tenants.api as api
import webapp2
import types
from auth.util import Authenticated
from util import process_request

class RegisterApp(webapp2.RequestHandler):
  def post(self):
    process_request(self, api, "register")
 
class ListTenants(webapp2.RequestHandler):
  def get(self):
    process_request(self, api, "list_tenants")

class GetTenant(webapp2.RequestHandler):

  @Authenticated
  def get(self):
    pathelems = filter(lambda p: len(p) > 0, self.request.path.split("/") )
    process_request(self, api, "get_tenant", {'tenant_id' : pathelems[1]})
    
application = webapp2.WSGIApplication(
   [
    ('/register', RegisterApp),
    ('/tenants/[-0-9-a-f]+', GetTenant),
    ('/tenants', ListTenants),
   ] , debug=True)
