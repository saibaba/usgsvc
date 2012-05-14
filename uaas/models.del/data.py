from sqlalchemy import Column, Integer, String, Sequence, DateTime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship, backref

from uaas.models import Base, id_column, GUID
import datetime
import uuid

class Tenant(Base):

  __tablename__ = 'tenants'

  id = id_column()
  creation_date = Column(DateTime(timezone=True), default=datetime.datetime.utcnow())
  created_by = Column(String(50), default='System')
  lastupdate_date = Column(DateTime(timezone=True), default=None)
  lastupdated_by = Column(String(50), default=None)

  name = Column(String(50))
  email = Column(String(50))
  api_key = Column(GUID(), default=uuid.uuid4)
  password = Column(String(50))

  #  ArgumentError: Error creating backref 'tenant' on relationship 'Tenant.services': property of that name exists on mapper 'Mapper|Service|services'


  services = relationship("Service", backref="tenant")

class Service(Base):

  __tablename__ = 'services'

  id = id_column()
  creation_date = Column(DateTime(timezone=True), default=datetime.datetime.utcnow())
  created_by = Column(String(50), default='System')
  lastupdate_date = Column(DateTime(timezone=True), default=None)
  lastupdated_by = Column(String(50), default=None)

  tenant_id = Column(GUID(), ForeignKey('tenants.id'))
  service_name = Column(String(50))

  #tenant = relationship("Tenant", backref='services')


  metrics = relationship("Metric", order_by="Metric.id", backref="service")

  usages = relationship("Usage", order_by="Usage.id", backref="service")

class Metric(Base):

  __tablename__ = 'metrics'

  id = id_column()
  creation_date = Column(DateTime(timezone=True), default=datetime.datetime.utcnow())
  created_by = Column(String(50), default='System')
  lastupdate_date = Column(DateTime(timezone=True), default=None)
  lastupdated_by = Column(String(50), default=None)

  service_id = Column(GUID(), ForeignKey('services.id'))
  #service = relationship("Service", backref=backref('metrics', order_by=id))

  name = Column(String(50))
  aggregator = Column(String(50))
  uom = Column(String(50))

class Usage(Base):

  __tablename__ = 'usage'

  id = id_column()
  creation_date = Column(DateTime(timezone=True), default=datetime.datetime.utcnow())
  created_by = Column(String(50), default='System')
  lastupdate_date = Column(DateTime(timezone=True), default=None)
  lastupdated_by = Column(String(50), default=None)

  service_id = Column(GUID(), ForeignKey('services.id'))
  #service = relationship("Service", backref=backref('usages', order_by=id))

  resource_owner = Column(String(50))
  resource_id = Column(String(50))
  ext_usage_id = Column(String(50))
  location = Column(String(50))
  event_time = Column(DateTime(timezone=True), default=datetime.datetime.utcnow())

  usagemetrics = relationship("UsageMetric", order_by="UsageMetric.id", backref="usage")

class UsageMetric(Base):

  __tablename__ = 'usagemetrics'

  id = id_column()
  usage_id = Column(GUID(), ForeignKey('usage.id'))
  metric_id = Column(GUID(), ForeignKey('metrics.id'))
  value = Column(String(50))


class AggregatedUsage(Base):

  __tablename__ = 'aggregatedusage'
  id = id_column()
  aggregate_start = Column(DateTime(timezone=True))  #, default=datetime.datetime.utcnow())
  aggregate_end   = Column(DateTime(timezone=True)) #, default=datetime.datetime.utcnow())

  service_id =     Column(GUID(), ForeignKey('services.id'))
  resource_owner = Column(String(50))
  resource_id =    Column(String(50))
  location =       Column(String(50))

  metric_id = Column(GUID(), ForeignKey('metrics.id'))
  value = Column(String(50))
  
"""
At registration:
{
  "attributes": [
    { "displayName" : "Bandwidth In",
    }
  ]
}

At aggreate read time request with:
{
  "tenantId" : "12312-13121",
  "serviceName" : "Cloud Servers",
  "resourceOwner": "acct #1",
  "resourceId" : "cs1",
}

Response would be:

{
  "tenantId" : "12312-13121",
  "serviceName" : "Cloud Servers",
  "resourceOwner": "acct #1",
  "resourceId" : "cs1",
  "startEventTime" : "2012-...",
  "endEventTime" : "2012-...",

  "attributes": [
    { "displayName" : "Bandwidth In",
    }
  ]

  "usageMetrics": [
    { "name" : "Bandwidth In",
      "aggregator" : "Sum",
      "UoM" : "GB",
      "value" : 10
    },
    { "name" : "Bandwidth Out",
      "aggregator" : "Sum",
      "UoM" : "GB",
      "value" : 10
    },
    { "name" : "Duration",
      "aggregator" : "Sum",
      "UoM" : "Hour",
      "value" : 5
    }
  ]
  
}
"""
