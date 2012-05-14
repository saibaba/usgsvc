import logging
import json
import uaas.api as api
import webapp2
import types
from auth.util import Authenticated
from util import process_request


class GetService(webapp2.RequestHandler):
  
  @Authenticated
  def get(self):
    pathelems = filter(lambda p: len(p) > 0, self.request.path.split("/"))
    process_request(self, api, "get_service", {'tenant_id' : pathelems[1], 'service_name' : pathelems[3] })  

class AddOrListServices(webapp2.RequestHandler):
  
  @Authenticated
  def post(self):
    pathelems = filter(lambda p: len(p) > 0, self.request.path.split("/"))
    process_request(self, api, "add_service", {'tenant_id' : pathelems[1]})  

  @Authenticated
  def get(self):
    pathelems = filter(lambda p: len(p) > 0, self.request.path.split("/"))
    process_request(self, api, "list_services", {'tenant_id' : pathelems[1]})  

class AddUsage(webapp2.RequestHandler):

  @Authenticated
  def post(self):
    pathelems = filter(lambda p: len(p) > 0, self.request.path.split("/"))
    process_request(self, api, "add_usage", 
      {'tenant_id' : pathelems[1],  'service_name' : pathelems[3] })  

class GetService(webapp2.RequestHandler):

  @Authenticated
  def get(self):

    pathelems = filter(lambda p: len(p) > 0, self.request.path.split("/"))
    process_request(self, api, "get_service", 
      {'tenant_id' : pathelems[1],  'service_name' : pathelems[3] })  

class GetAggregatedUsage(webapp2.RequestHandler):

  @Authenticated
  def get(self):
    pathelems = filter(lambda p: len(p) > 0, self.request.path.split("/"))
    process_request(self, api, "get_aggregated_usage", 
      {'tenant_id' : pathelems[1]})  

application = webapp2.WSGIApplication(
   [
    ('/tenants/[-0-9-a-f]+/services/[-_0-9a-zA-Z]+/usage', AddUsage),
    ('/tenants/[-0-9-a-f]+/services/.*', GetService),
    ('/tenants/[-0-9-a-f]+/services', AddOrListServices),
    ('/tenants/[-0-9-a-f]+/aggregated_usage', GetAggregatedUsage),
   ] , debug=True)
