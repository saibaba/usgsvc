#from google.appengine.ext import webapp
#from google.appengine.ext.webapp.util import run_wsgi_app

import logging
import json
import uaas.api as api
import webapp2
import types
from auth.util import Authenticated

class RunAggregator(webapp2.RequestHandler):
  def get(self):
    api.run_aggregator(None, None)

class RunRating(webapp2.RequestHandler):
  def get(self):
    api.run_rating(None, None)

application = webapp2.WSGIApplication(
   [
    ('/run_rating', RunRating),
    ('/run_aggregator', RunAggregator),
   ] , debug=True)
