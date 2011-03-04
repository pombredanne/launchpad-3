from lp.bugs.model.personsubscriptioninfo import PersonSubscriptionInfoSet
from lp.registry.interfaces.teammembership import TeamMembershipStatus
p = factory.makePerson()
b = factory.makeBug()
t = factory.makeTeam(members=[p])
ta = factory.makeTeam()
ta.addMember(p, p, status=TeamMembershipStatus.ADMIN)
b.subscribe(p, p) # populates direct subscriptions
b.subscribe(t, p) # populates direct subscriptions
b.subscribe(ta, p) # populates direct subscriptions

db = factory.makeBug()
db.markAsDuplicate(b)
db.subscribe(p, p) # populates direct subscriptions
db.subscribe(t, p) # populates direct subscriptions
db.subscribe(ta, p) # populates direct subscriptions

psis = PersonSubscriptionInfoSet(p,b)

print psis.direct_subscriptions
print psis.direct_subscriptions.as_team_admin
print psis.direct_subscriptions.as_team_member

print psis.duplicate_subscriptions
print psis.duplicate_subscriptions.as_team_admin
print psis.duplicate_subscriptions.as_team_member

print psis.supervisor_subscriptions
