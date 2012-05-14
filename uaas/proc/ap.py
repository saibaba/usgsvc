from uaas.models.data import *
from sqlalchemy import create_engine, Table, MetaData
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.expression import text
from sqlalchemy.engine.base import Connection
import datetime

"""
  __tablename__ = 'usage'
  service_id = Column(GUID(), ForeignKey('services.id'))
  #service = relationship("Service", backref=backref('usages', order_by=id))

  resource_owner = Column(String(50))
  resource_id = Column(String(50))
  ext_usage_id = Column(String(50))
  location = Column(String(50))
  event_time = Column(DateTime(timezone=True), default=datetime.datetime.utcnow())

  usagemetrics = relationship("UsageMetric", order_by="UsageMetric.id", backref="usage")


  __tablename__ = 'usagemetrics'

  id = id_column()
  usage_id = Column(GUID(), ForeignKey('usage.id'))
  metric_id = Column(GUID(), ForeignKey('metrics.id'))
  value = Column(String(50))

  
"""

import time
from threading import Timer
import types

class Aggregator(object):

  def __init__(self, delay, url, **dbparams):
    self.delay =  delay

    self.dburl = url
    self.engine = create_engine(url, **dbparams)

    self.start()

  def start(self):
    self.timer = Timer(self.delay, self.aggregate, ())
    self.timer.start()

  def process_results(self, resultset, session):

    rows = resultset.fetchall()

    for r in rows:
      print r
      (y,m,d) = r[6].split("-")
      y = int(y)
      m = int(m)
      d = int(d)
      dt = datetime.datetime(y,m,d)

      a = AggregatedUsage(
        service_id = r[0], 
        resource_owner = r[1],
        resource_id = r[2],
        location = r[3],
        metric_id = r[4],
        value = r[5], aggregate_start=dt, aggregate_end=dt)

      session.add(a)
      
    resultset.close()
    session.commit()
  
  def aggregate(self):
    print "AGGREGATING...after ", self.delay
    t = text("""
      SELECT u.service_id, u.resource_owner, u.resource_id, u.location, um.metric_id, sum(um.value),
             strftime('%Y-%m-%d', u.event_time)
      FROM usage u, usagemetrics um 
      where um.usage_id = u.id
      group by u.service_id, u.resource_owner, u.resource_id, u.location,
             strftime('%Y-%m-%d', u.event_time)
    """, bind=self.engine)
    conn = Connection(self.engine)
    result = conn.execute(t)

    Session = sessionmaker(bind=self.engine)
    session = Session()

    """
    blah = session.query(UsageMetric).group_by(
      UsageMetric.service_id, 
      UsageMetric.resource_owner, 
      UsageMetric.resource_id, 
      UsageMetric.location, 
      UsageMetric.metric_id,
      func.day(UsageMetric.event_time)).all()

    for r in blah:
      print r
    """

    self.process_results(result, session)

    conn.close()
    session.close()

    self.timer.cancel()
    #self.start()

  def stop(self):
    self.timer.cancel()
