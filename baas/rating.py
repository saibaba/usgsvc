import logging

def is_currency(balctr):
  return balctr in ['USD', 'GBP']


def _locaterate(rp, balances, attrs, quantity, currency):

  qtytier = None

  if 'tiers' in rp:
      for tier in rp['tiers']:

	if tier['currency'] != currency:
          continue

        if not 'rules' in tier:
          qtytier = (quantity, tier)
          break

        min_qty_allowed = None

	for rule in tier['rules']:
          print "Checking rule:", rule
          counter = rule['balance_counter']
          curval = balances.get(counter, 0)
          minv = rule.get('min', curval-1)
          maxv = rule.get('max', curval+quantity)
          allowed = 0
          if curval >= minv and curval < maxv:
            allowed = maxv - curval
          if allowed > 0:
	    if min_qty_allowed is None:
              min_qty_allowed = allowed
	    else:
              min_qty_allowed = min(allowed, min_qty_allowed)
	  else:
            min_qty_allowed = None

	if min_qty_allowed is not None and min_qty_allowed > 0:
	  qtytier = (min_qty_allowed, tier)
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
 
      if nsel is not None:
        qtytier =  _locaterate(nsel, balances, attrs, quantity, currency)
      else:
        logging.error( "Could not find a rate matching with given attributes!")
        logging.error( "No value in the rateplan value set for attribute/value = " + an + "/" + av)

  else:
    logging.error( "rateplan\n", rp, "\n missing selector or rate tiers")

  return qtytier
    
def findrate(srp, metric_name, balances, attrs, quantity, currency):

  rp = None
  for rpl in srp['rateplan']:
    if rpl['metric_name'] == metric_name:
      rp = rpl
      break

  if rp is None: return None

  return _locaterate(rp, balances, attrs, quantity, currency) 
  

def rate_usage(srp, metric_name, balances, attrs, quantity, currency):
  origqty = quantity

  subbalances = {}

  while  quantity > 0:
    qtytier = findrate(srp, metric_name, balances, attrs, quantity, currency)
    if qtytier is not None:
      consumable = min(qtytier[0], quantity)
      tier = qtytier[1]
      impacts = tier['impacts']
  
      if 'rules' in tier:
        for rule in tier['rules']:
          rulectr = rule['balance_counter']
          impacts.append( { "balance_counter" : rulectr, "rate" : 1 } )

      subimpacts={}
      for impact in impacts:
        rate = impact['rate']
	logging.info("multipling rate type: " + str(type(rate)) + " with consumable type : " + str(type(consumable)))
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
      subbalances.setdefault("$UNRATED$", []).append( {'tier_name' : '$UNRATED$', 'rate': 1, 'quantity': quantity})
      break

  tot = 0

  for balance in balances.keys():
    print "Balance for " + balance + " = " + str(balances[balance])

  return subbalances

