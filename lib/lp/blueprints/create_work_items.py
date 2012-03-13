# To run this:
# $ ./bin/iharness -c "import lp.blueprints.create_work_items"

__metaclass__ = type
__all__ = []


from datetime import datetime

from lp.blueprints.enums import SpecificationPriority
from lp.registry.model.person import Person
from lp.registry.model.distribution import Distribution
from lp.testing.factory import LaunchpadObjectFactory


april = datetime(2012, 04, 20)
may = datetime(2012, 05, 23)

team = Person.byName('hwdb-team')
participants = list(team.allmembers)
factory = LaunchpadObjectFactory()

# Create a new product with a spec targeted to a milestone due in april and a
# bunch of work items assigned to arbitrary team members.
product1 = factory.makeProduct()
product1_milestone = factory.makeMilestone(
    product=product1, dateexpected=april)
product1_spec = factory.makeSpecification(
    product=product1, milestone=product1_milestone,
    priority=SpecificationPriority.HIGH)
for i in range(10):
    factory.makeSpecificationWorkItem(
        specification=product1_spec, assignee=participants[i])

# Create a second product with a spec targeted to a milestone due in *may* and
# a bunch of work items assigned to arbitrary team members.
product2 = factory.makeProduct()
product2_milestone = factory.makeMilestone(product=product2, dateexpected=may)
product2_spec = factory.makeSpecification(
    product=product2, milestone=product2_milestone,
    priority=SpecificationPriority.LOW)
for i in range(10):
    factory.makeSpecificationWorkItem(
        specification=product2_spec, assignee=participants[i])

# Create spec on the Ubuntu distro targeted to a milestone due in *april*, and
# a bunch of work items assigned to arbitrary team members.
ubuntu = Distribution.byName('ubuntu')
ubuntu_milestone = factory.makeMilestone(
    distribution=ubuntu, dateexpected=april)
ubuntu_spec = factory.makeSpecification(
    distribution=ubuntu, milestone=ubuntu_milestone,
    priority=SpecificationPriority.LOW)
for i in range(10):
    factory.makeSpecificationWorkItem(
        specification=ubuntu_spec, assignee=participants[i])

import transaction
transaction.commit()
