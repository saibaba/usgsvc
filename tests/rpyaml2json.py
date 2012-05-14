import yaml
import json
import types
from copy import deepcopy

def monkey_patch(d):

  class mpd(object):
    def __init__(self, origd):
      self.origd = origd

    def __getattr__(self, name):
   
      rv = None
      if name in self.origd:
        rv =  self.origd[name]
        if type(rv) == types.DictType:
          rv =  monkey_patch(rv)
        elif type(rv) == types.ListType:
          for i in range(len(rv)):
            x = rv[i]
            if type(x) == types.DictType:
              rv[i] =  monkey_patch(x)

      return rv

  return mpd(d)

def yaml2rateplan(ytext):

  y = yaml.load(ytext)

  result = { 'service_name' : y['service_name'], 'rateplan' : []  }

  for mrp in y['rateplan']:

    rp = { 'metric_name' : mrp['metric_name'] }

    toprp = rp
 
    selectors = mrp['selectors'][:-1] # to exclude the tier pointer

    for sel in selectors:
      rp['selector'] = { "name" : sel , 'value_set' : { "$VALUE$" : { } } }
      rp = rp['selector']['value_set']['$VALUE$']

    result['rateplan'].append(toprp)

    rp = toprp

    for vi in range(len(mrp['value_set'])-1):
      v = mrp['value_set'][vi]
      tvs = rp['selector']['value_set']
      tmpl = tvs['$VALUE$']
      tvs[v] = deepcopy(tmpl)  
      rp = tvs[v]

    rp['tiers'] = mrp['value_set'][len(mrp['value_set'])-1]
 
  return result
 
f = open("amznrp_yaml.txt")
s = "".join(f.readlines())
f.close()
r = yaml2rateplan(s)

print r
