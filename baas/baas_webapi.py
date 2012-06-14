"""
  Billing API entry points
"""
import baas.acctsapi as aapi
import baas.billapi as bapi
import baas.rpapi as rapi
import webapp2

from auth.util import Authenticated
from util import process_request, process_request_m

class AddOrListAccounts(webapp2.RequestHandler):

  @Authenticated
  def post(self):
    pathelems = filter(lambda p: len(p) > 0, self.request.path.split("/"))
    process_request(self, aapi, "add_account", {'tenant_id' : pathelems[1]})  

  @Authenticated
  def get(self):
    pathelems = filter(lambda p: len(p) > 0, self.request.path.split("/"))
    process_request(self, aapi, "list_accounts", {'tenant_id' : pathelems[1] })  

class GetAccount(webapp2.RequestHandler):
  
  @Authenticated
  def get(self):
    pathelems = filter(lambda p: len(p) > 0, self.request.path.split("/"))
    process_request(self, aapi, "get_account_json", {'tenant_id' : pathelems[1], 'account_no' : pathelems[3]})  

class AddOrListBills(webapp2.RequestHandler):
  
  @Authenticated
  def post(self):
    pathelems = filter(lambda p: len(p) > 0, self.request.path.split("/"))
    process_request_m(self, bapi, "create_bill", {'tenant_id' : pathelems[1], 'account_no' : pathelems[3]})  

  @Authenticated
  def get(self):
    pathelems = filter(lambda p: len(p) > 0, self.request.path.split("/"))
    process_request_m(self, bapi, "list_bills", {'tenant_id' : pathelems[1], 'account_no' : pathelems[3]})  

class CurrBill(webapp2.RequestHandler):
  
  @Authenticated
  def put(self):
    pathelems = filter(lambda p: len(p) > 0, self.request.path.split("/"))
    process_request(self, bapi, "create_bill", {'tenant_id' : pathelems[1], 'account_no' : pathelems[3]})  

  @Authenticated
  def get(self):
    pathelems = filter(lambda p: len(p) > 0, self.request.path.split("/"))
    process_request_m(self, bapi, "get_current_bill", {'tenant_id' : pathelems[1], 'account_no' : pathelems[3]})  

  @Authenticated
  def delete(self):
    pathelems = filter(lambda p: len(p) > 0, self.request.path.split("/"))
    process_request_m(self, bapi, "delete_current_bill", {'tenant_id' : pathelems[1], 'account_no' : pathelems[3]})  

class GetBill(webapp2.RequestHandler):

  @Authenticated
  def get(self):
    pathelems = filter(lambda p: len(p) > 0, self.request.path.split("/"))
    process_request_m(self, bapi, "get_bill",
       {'tenant_id' : pathelems[1], 'account_no' : pathelems[3], 'bill_id' : pathelems[5] })  


class AddRateplan(webapp2.RequestHandler):

  @Authenticated
  def put(self):
    pathelems = filter(lambda p: len(p) > 0, self.request.path.split("/"))

    if self.request.headers['Content-Type'] == "application/yaml":
      process_request(self, rapi, "add_rateplan_yaml", 
         {'tenant_id' : pathelems[1], 'service_name' : pathelems[3] })
    else:
      process_request(self, rapi, "add_rateplan_json", 
         {'tenant_id' : pathelems[1], 'service_name' : pathelems[3] })  

application = webapp2.WSGIApplication(
   [
    ('/tenants/[-0-9-a-f]+/accounts/[0-9]+/bills/current', CurrBill),
    ('/tenants/[-0-9-a-f]+/accounts/[0-9]+/bills/[-0-9a-z]+', GetBill),
    ('/tenants/[-0-9-a-f]+/accounts/[0-9]+/bills', AddOrListBills),
    ('/tenants/[-0-9-a-f]+/accounts', AddOrListAccounts),
    ('/tenants/[-0-9-a-f]+/accounts/[0-9]+', GetAccount),
    ('/tenants/[-0-9-a-f]+/services/[-_a-z]+/rateplan', AddRateplan),
   ] , debug=True)
