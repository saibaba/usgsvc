Feature: Register user
    In order to use UaaS
    As tenant
    We'll implement register tenant
    And   add services for a tenant

    Scenario: Register tenant rackcloud
        Given tenant rackcloud with email sai@sai.org and password sai
        When I register as tenant
        Then I see rackcloud in database as tenant

    Scenario: Add Services for tenant rackcloud
        Given tenant with email sai@sai.org
        When I add the service cloud_servers
        Then I see rackcloud owning the service cloud_servers

    Scenario: Add Metrics for service cloud_servers for tenant rackcloud
        Given Xtenant with email sai@sai.org and service cloud_servers
        When I add the metric Duration with aggregator sum and unit of measure Hour
        Then I see Duration as metric

    Scenario: Add Usage for a service
        Given tenant has been created with email sai@sai.org
        And   tenant registered service cloud_servers
        And   tenent added metric definition Duration with uom Hour for service cloud_servers
        When  I add usages for metric Duration with following values:
              | Duration |
              | 10 |
              | 20 |
              | 30 |
              | 40 |
              | 50 |
        Then  I see values:
              | Duration |
              | 10 |
              | 20 |
              | 30 |
              | 40 |
              | 50 |

    Scenario: Read Aggregated usage
        Given aggregator has been started at delay 1 second
        And   wait for 10 seconds for aggregator to pick usage up and  aggregate
        Then  I see aggregated value 150
