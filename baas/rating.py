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

def _locaterate(rp, currency, attrs):

  logging.info("Working with rp:")
  logging.info(rp)

  rv = None

  if 'rate' in rp:
    if currency in rp['rate']:
      rv =  int(rp['rate'][currency])
    else:
      logging.error( "No rate defined for currency!")
      return None
  elif 'selector' in rp:

    sel = rp['selector']
    an = sel['name']
    logging.info("sel=%s;an=%s;" % (sel, an)) 
    logging.info(attrs)
    logging.info(type(attrs))
    av = attrs[an]

    nsel = None
    for vl in sel['value_set'].keys():
      if vl == av:
        nsel = sel['value_set'][vl]
        break
 
    if nsel != None: 
      rv =  _locaterate(nsel, currency, attrs)
    else:
      logging.error( "Could not find a rate matchig with given attributes!")

  else:
    logging.error( "rateplan\n", rp, "\n missing selector or rate")

  return rv

def findrate(srp, metric_name, currency, attrs):

  logging.info(srp)

  rp = None
  if srp['metric_name'] != metric_name: 
    logging.error(" ***** Found serious bug ******")
    return None

  return _locaterate(srp, currency, attrs)

def findrate_del(srp, metric_name, currency, attrs):

  logging.info(srp)

  rp = None
  for rpl in srp['rateplan']:
    if rpl['metric_name'] == metric_name:
      rp = rpl
      break

  if rp == None: return None

  return _locaterate(rp, currency, attrs)
 
def get_rate(m, currency, attrs):
  rq = gdata.MetricRate.all()
  rq.filter("metric_id = ", m.id)
  rr = rq.fetch(1)

  for ri in rr:
    if ri.currency == currency:
      return ri.rate
    elif ri.currency == "*":
      return findrate( json.loads(ri.selector), m.metric_name, currency, attrs)

  return None


