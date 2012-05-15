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

def _locaterate(rp, balances, attrs, quantity):

  qtytier = None

  if 'tiers' in rp:
      for tier in rp['tiers']:
        if not 'rule' in tier:
          qtytier = (quantity, tier)
          break

        counter = tier['rule']['balance_counter']
        curval = balances.get(counter, 0)
        minv = tier['rule'].get('min', curval-1)
        maxv = tier['rule'].get('max', curval+quantity)
        allowed = 0
        if curval >= minv and curval < maxv:
          allowed = maxv - curval
        if allowed > 0:
          qtytier = (allowed, tier)
          break
        
  elif 'selector' in rp:
    sel = rp['selector']
    an = sel['name']

    if not an in attrs:
      logging.error("Could not find attribute: " + an + " in the usage to rate")
    else:  
      av = attrs[an]

      nsel = None
      for vl in sel['value_set'].keys():
        if vl == av:
          nsel = sel['value_set'][vl]
          break
 
      if nsel != None:
        qtytier =  _locaterate(nsel, balances, attrs, quantity)
      else:
        logging.error( "Could not find a rate matching with given attributes!")
        logging.error( "No value in the rateplan value set for attribute/value = " + an + "/" + av)

  else:
    logging.error( "rateplan\n", rp, "\n missing selector or rate tiers")

  return qtytier
    
def findrate(srp, metric_name, balances, attrs, quantity):

  rp = None
  for rpl in srp['rateplan']:
    if rpl['metric_name'] == metric_name:
      rp = rpl
      break

  if rp == None: return None

  return _locaterate(rp, balances, attrs, quantity) 
  

def rate_usage(srp, metric_name, balances, attrs, quantity):
  origqty = quantity

  subbalances = {}

  while  quantity > 0:
    qtytier = findrate(srp, metric_name, balances, attrs, quantity)
    if qtytier != None:
      consumable = min(qtytier[0], quantity)
      tier = qtytier[1]
      impacts = tier['impacts']
  
      if 'rule' in tier:
        rulectr = tier['rule']['balance_counter']
        impacts.append( { "balance_counter" : rulectr, "rate" : 1 } )

      subimpacts={}
      for impact in impacts:
        rate = impact['rate']
        total = rate * consumable
        counter = impact['balance_counter']
        balances[counter] = balances.setdefault(counter, 0) + total
	subimpacts.setdefault(counter, []).append(  { 'tier_name': tier['name'], 'rate': rate, 'quantity' : consumable, 'balance' : total})

      for counter in subimpacts.keys():
        subbalances.setdefault(counter, []).append(subimpacts[counter])

      quantity -= consumable
      print "Consumed: " + str(consumable) + " by tier: " + tier['name']
      
    else:
      logging.error("Could not find tier to consume : " + str(quantity) + " out of total qty: " + str(origqty))
      break

  tot = 0

  for balance in balances.keys():
    print "Balance for " + balance + " = " + str(balances[balance])
    if balance == "USD": tot += balances[balance]

  return (tot, subbalances)
