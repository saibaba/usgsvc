import json
import logging

sample="""
{ "service_name": "my_cloud_servers", 
    "rateplan" : [ 
      { "metric_name": "Duration",
        "selector":
          [ { "filter" : { "os" : "windows", "flavor" = "256", "currency" = "USD" },   "rate" : 18 },
            { "filter" : { "os" : "linux", "flavor" = "256", "currency" = "USD" },   "rate" : 2 }
          ]
      },
      { "metric_name": "Bandwidth In" , "rate": { "USD": "1"} } ,
      { "metric_name": "Bandwidth Out", "rate" : { "USD" : "7" } } 
    ]
}
"""

f  = open("cpxrp.txt")
jsonstr = "".join(f.readlines())
f.close()

jsonobj = json.loads(jsonstr)

print jsonobj

def _locaterate(rp, attrs, currency):

  rv = None

  if rp.has_key('rate'):
    if rp['rate'].has_key(currency):
      rv =  rp['rate'][currency]
    else:
      logging.error( "No rate defined for currency!")
      return None
  elif rp.has_key('selector'):
    sel = rp['selector']
    an = sel['name']
    av = attrs[an]

    nsel = None
    for vl in sel['value_set'].keys():
      if vl == av:
        nsel = sel['value_set'][vl]
        break
 
    if nsel != None: 
      rv =  _locaterate(nsel, attrs, currency)
    else:
      logging.error( "Could not find a rate matchig with given attributes!")

  else:
    logging.error( "rateplan\n", rp, "\n missing selector or rate")

  return rv
    
def findrate(srp, metric_name, currency, attrs):

  rp = None
  for rpl in srp['rateplan']:
    if rpl['metric_name'] == metric_name:
      rp = rpl
      break

  if rp == None: return None

  return _locaterate(rp, attrs, currency) 
  

print findrate(jsonobj, "Duration", "USD", { "os" : "windows", "flavor" : "256" })
print findrate(jsonobj, "Duration", "INR", { "os" : "linux", "flavor" : "256" })
print findrate(jsonobj, "Duration", "USD", { "os" : "redhat", "flavor" : "256" })
print findrate(jsonobj, "Bandwidth In", "USD", { })
