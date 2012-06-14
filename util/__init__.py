import uuid, json
import logging
from decimal import Decimal

from util.monad import Nothing

def genid():
  return str(uuid.uuid4())

def _has_required_input(req, response, required):

  rv = True
  missing = []

  for r in required:
    if not req.has_key(r):
      missing.append(r)

  if len( missing) > 0:
    logging.warn("Missing input: " + ",".join(missing))
    response.set_status('400 ' + ",".join(missing))
    rv = False

  return rv

def Required(mfields):
     
    def _validateAndCall(fn):

        def callfn(req, response):
          rv = _has_required_input(req, response, mfields)
          if rv:
            return fn(req, response)

        return callfn

    return _validateAndCall


def process_request(handler, module, reqfn, pathelems = {}):
    handler.response.headers['Content-Type'] = 'application/json'
    content = handler.request.body
    req = {}
    logging.info("******** method ***********")
    logging.info(handler.request.method)
    logging.info("******** body content ***********")
    logging.info(content)
    if handler.request.method == "POST" or handler.request.method == "PUT":
      if handler.request.headers['Content-Type'] == "application/json":
        req = json.loads(content, parse_float=Decimal)
      else:
        req = {'body': content}

    for pe in pathelems.keys():
      req[pe] = pathelems[pe]

    fn = getattr(module, reqfn)
    ans = fn(req, handler.response)

    logging.info(handler.response.status)

    if ans is not None:
      handler.response.headers['Content-Type']  = "application/json"
      handler.response.out.write(json.dumps(ans))

def process_request_m(handler, module, reqfn, pathelems = {}):
    handler.response.headers['Content-Type'] = 'application/json'
    content = handler.request.body
    req = {}
    logging.info("******** method ***********")
    logging.info(handler.request.method)
    logging.info("******** body content ***********")
    logging.info(content)
    if handler.request.method == "POST" or handler.request.method == "PUT":
      if handler.request.headers['Content-Type'] == "application/json":
        req = json.loads(content, parse_float=Decimal)
      else:
        req = {'body': content}

    for pe in pathelems.keys():
      req[pe] = pathelems[pe]

    fn = getattr(module, reqfn)
    ans = fn(req, handler.response )

    def write_output(resp):
      handler.response.headers['Content-Type']  = "application/json"
      handler.response.out.write(json.dumps(resp))
      return Nothing()

    if not isinstance(ans, Nothing):
        ans >> (lambda resp: write_output(resp) )

    logging.info(handler.response.status)

def subtract_one_month(t):

    # http://code.activestate.com/recipes/577274-subtract-or-add-a-month-to-a-datetimedate-or-datet/
    """Return a `datetime.date` or `datetime.datetime` (as given) that is
    one month later.
    
    Note that the resultant day of the month might change if the following
    month has fewer days:
    
        >>> subtract_one_month(datetime.date(2010, 3, 31))
        datetime.date(2010, 2, 28)
    """
    import datetime
    one_day = datetime.timedelta(days=1)
    one_month_earlier = t - one_day
    while one_month_earlier.month == t.month or one_month_earlier.day > t.day:
        one_month_earlier -= one_day
    return one_month_earlier

