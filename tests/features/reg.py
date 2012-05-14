from lettuce import *

from uaas.models import data
from uaas.proc import ap
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def DBURL():
  return 'sqlite:///databases/db.sqlite'

def DBPARAMS():
  return {"echo" : False }

class Txn(object):
  def __enter__(self):
    return world.session

  def __exit__(self, type, value, traceback):
    world.session.commit()

class RTxn(object):
  def __enter__(self):
    return world.session

  def __exit__(self, type, value, traceback):
    pass

@before.all
def setup_database_session():
  world.engine = create_engine(DBURL(), **DBPARAMS()) # echo=True)
  Session = sessionmaker(bind=world.engine)
  world.session = Session()
  data.Base.metadata.create_all(world.engine)

@after.all
def teardown_database_session(total):
  world.session.close()
  
   
@step('tenant (.+) with email (.+) and password (.+)')
def tenant(step, name, email, password):
  world.tenant = data.Tenant(name=name, email=email, password=password)

@step('I register as tenant')
def register_as_tenant(step):
  register(world.tenant)

@step('I see (.+) in database as tenant')
def check_registration(step, expected):
  with RTxn() as txn:
    tenant = txn.query(data.Tenant).filter_by(name = expected).first()
  
  assert tenant.name == expected, "Got %s" % tenant.name

def register(tenant):
  with Txn() as txn:
    txn.add(tenant)

@step(u'Given tenant with email (.+)')
def given_tenant(step, email):

    with Txn() as s:
      tenant = s.query(data.Tenant).filter_by(email=email).first()
      assert tenant != None and tenant.email == email,  "Could not find tenant with email %s" % email
      world.tenant = tenant

@step(u'When I add the service (.+)')
def add_service(step, service):
    with Txn() as s:
      service = data.Service(service_name=service)
      world.tenant.services = [ service ]

@step(u'Then I see (.+) owning the service (.+)')
def check_tenent_own_service(step, email, name):
    with RTxn() as s:
      service = s.query(data.Service).filter_by(tenant_id = world.tenant.id).first()
      assert service.service_name == name, "Got %s when looking for %s" % (service.service_name, name)

@step(u'Given Xtenant with email (.+) and service (.+)')
def given_tenant_and_service(step, email, name):
    with RTxn() as s:
      world.tenant = s.query(data.Tenant).filter_by(email=email).first()
      world.service = world.tenant.services[0]
      assert world.service.service_name == name, "Got %s when looking for %s" % (world.service.service_name, name)

@step(u'When I add the metric (.+) with aggregator (.+) and unit of measure (.+)')
def add_metric(step, name, aggfn, uom):
    with Txn() as s:
      metric = data.Metric(name=name, aggregator=aggfn, uom=uom)
      world.service.metrics = [metric]

@step(u'Then I see (.+) as metric')
def then_i_see_duration_as_metric(step, name):
    with RTxn() as s:
      metric = world.tenant.services[0].metrics[0]
      assert metric.name == name, "Got %s when looking for %s" % (metric.name, name)

@step(u'Given tenant has been created with email (.+)')
def tenant_has_been_created_with_email(step, email):
    with RTxn() as s:
      world.tenant = s.query(data.Tenant).filter_by(email=email).first()

@step(u'And   tenant registered service (.+)')
def tenant_registered_service(step, service):
    with RTxn() as s:
      world.service = world.tenant.services[0]
      assert world.service.service_name == service, "Got %s" % world.service.service_name

@step(u'And   tenent added metric definition (.+) with uom (.+) for service (.+)')
def tenent_added_metric_definition(step, metric, uom, service):
    with RTxn() as s:
      world.service.metric = world.service.metrics[0]

def add_usage_for_metric(metric, value):
    with Txn() as s:
       u = data.Usage(resource_owner="openstack", resource_id="www1.openstack.org", ext_usage_id="1", location="ORD1")
       if world.service.usages != None and len(world.service.usages) > 0:
         world.service.usages.append(u)
       else:
         world.service.usages = [u]

       # TODO need to also validate that the metric belongs to the right service under right tenant
       world.metric = s.query(data.Metric).filter_by(name=metric).first()
       v = data.UsageMetric(value=value, metric_id=world.metric.id)
       if u.usagemetrics != None and len(u.usagemetrics) > 0:
         u.usagemetrics.append(v)
       else:
         u.usagemetrics = [v]

@step(u'When  I add usages for metric (.+) with following values:')
def when_i_add_usages_for_metric_duration_with_following_values(step, metric):
    for usage_dict in step.hashes:
      value= usage_dict['Duration']
      add_usage_for_metric(metric, value)

@step(u'Then  I see values:')
def then_i_see_values(step):
    expected = []
    for usage_dict in step.hashes:
      value = usage_dict['Duration']
      expected.append(value)

    print expected

    with RTxn() as s:
      m = s.query(data.Metric).filter_by(service_id = world.service.id).first()
      u = s.query(data.Usage).filter_by(service_id = world.service.id).first()
      um = s.query(data.UsageMetric).filter(data.UsageMetric.usage_id == u.id).filter(data.UsageMetric.metric_id == m.id).all()
      for row in um:
        print "********", row

      intset = set(expected).intersection( set(um) )
      assert len(intset) == 0, "Did not match"

    #assert False, 'This step must be implemented'

#-------

@step(u'Given aggregator has been started at delay (.+) second')
def aggregator_has_been_started(step, f):
    delay = int(f)
    world.aggregator = ap.Aggregator(delay, DBURL(), **DBPARAMS()) #echo=True)
    
@step(u'And   wait for (.+) seconds for aggregator to pick usage up and  aggregate')
def wait_for(step, wtime):
    import time
    time.sleep(int(wtime))
    world.aggregator.stop()
 
@step(u'Then  I see aggregated value (.+)')
def then_i_see_aggregated_value(step, value):
    with RTxn() as s:
      a = s.query(data.AggregatedUsage).first()
      assert a.value == value, "Got %s" % um.value
