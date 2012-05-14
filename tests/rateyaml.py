import logging
import yaml
from copy import deepcopy
import types

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

  while  quantity > 0:
    qtytier = findrate(srp, metric_name, balances, attrs, quantity)
    if qtytier != None:
      consumable = min(qtytier[0], quantity)
      tier = qtytier[1]
      impacts = tier['impacts']
  
      if 'rule' in tier:
        rulectr = tier['rule']['balance_counter']
        impacts.append( { "balance_counter" : rulectr, "rate" : 1 } )

      for impact in impacts:
        rate = impact['rate']
        total = rate * consumable
        counter = impact['balance_counter']
        balances[counter] = balances.setdefault(counter, 0) + total

      quantity -= consumable
      print "Consumed: " + str(consumable) + " by tier: " + tier['name']
      
    else:
      logging.error("Could not find tier to consume : " + str(quantity) + " out of total qty: " + str(origqty))
      break

  for balance in balances.keys():
    print "Balance for " + balance + " = " + str(balances[balance])
 
def yaml2rateplan(ytext):

  y = yaml.load(ytext)

  result = { 'service_name' : y['service_name'], 'rateplan' : []  }

  for mrp in y['rateplan']:

    dfltcurr = mrp.get('currency', 'USD')

    rp = { 'metric_name' : mrp['metric_name'] }

    toprp = rp

    if not 'selectors' in mrp:
      if 'tiers' in mrp:
        rp['tiers'] = mrp['tiers']
        result['rateplan'].append(rp)
      continue
 
    selectors = mrp['selectors'][:-1] # to exclude the tier pointer

    for sel in selectors:
      rp['selector'] = { "name" : sel , 'value_set' : { "$VALUE$" : { } } }
      rp = rp['selector']['value_set']['$VALUE$']



    for vsl in mrp['value_set']:

      rp = toprp
      
      for vi in range(len(vsl)-1):
        v = vsl[vi]
        tvs = rp['selector']['value_set']
        if v not in tvs:
          tmpl = tvs['$VALUE$']
          tvs[v] = deepcopy(tmpl)  
        rp = tvs[v]

      tier = vsl[len(vsl)-1]
      if type(tier) == types.ListType:
        rp['tiers'] = vsl[len(vsl)-1]
      else:
        print "Using rate: ", tier
       
        rp['tiers'] =  [ { 'name': 'flat rate', 'impacts': [ {'balance_counter' : dfltcurr, 'rate' : float(tier) } ] } ] 

    result['rateplan'].append(toprp)

  return result

f  = open("amznrp_yaml.txt")
yamlstr = "".join(f.readlines())
f.close()
jsonobj = yaml2rateplan(yamlstr)

print jsonobj

rate_usage(jsonobj, "Duration", { } , 
     { "instance_type" :  "Standard On-Demand", "os" : "windows", "flavor" : "Small" , "region" : "US East (Virginia)"}, 50)
#print rate_usage(jsonobj, "Duration", { "INR" : 0} , { "os" : "linux", "flavor" : "256" })
#print rate_usage(jsonobj, "Duration", { "USD" : 0} , { "os" : "redhat", "flavor" : "256" })

rate_usage(jsonobj, "Bandwidth In", { } , { }, 1000)
rate_usage(jsonobj, "Bandwidth Out", { } , { }, 100)

