# Copyright 2008, 2009 Canonical Ltd.  All rights reserved.

"""In-memory doubles of core codehosting objects."""

__metaclass__ = type
__all__ = [
    'InMemoryFrontend',
    'XMLRPCWrapper'
    ]

import operator
from xmlrpclib import Fault

from bzrlib.urlutils import escape, unescape

from zope.component import adapter, getSiteManager
from zope.interface import implementer

from canonical.database.constants import UTC_NOW
from lp.code.model.branchnamespace import BranchNamespaceSet
from lp.code.model.branchtarget import (
    PackageBranchTarget, ProductBranchTarget)
from lp.code.interfaces.branch import BranchType, IBranch
from lp.code.interfaces.branchtarget import IBranchTarget
from lp.code.interfaces.codehosting import (
    BRANCH_TRANSPORT, CONTROL_TRANSPORT, LAUNCHPAD_ANONYMOUS,
    LAUNCHPAD_SERVICES)
from lp.soyuz.interfaces.publishing import PackagePublishingPocket
from canonical.launchpad.testing import ObjectFactory
from canonical.launchpad.validators import LaunchpadValidationError
from lp.code.xmlrpc.codehosting import (
    datetime_from_tuple, iter_split)
from canonical.launchpad.xmlrpc import faults


class FakeStore:
    """Fake store that implements find well enough to pass tests.

    This is needed because some of the `test_codehosting` tests use
    assertSqlAttributeEqualsDate, which relies on ORM behaviour. Here, we fake
    enough of the ORM to pass the tests.
    """

    def __init__(self, object_set):
        self._object_set = object_set

    def find(self, cls, **kwargs):
        """Implement Store.find that takes two attributes: id and one other.

        This is called by `assertSqlAttributeEqualsDate`, which relies on
        `find` returning either a single match or None. Returning a match
        implies that the given attribute has the expected value. Returning
        None implies the opposite.
        """
        branch_id = kwargs.pop('id')
        assert len(kwargs) == 1, (
            'Expected only id and one other. Got %r' % kwargs)
        attribute = kwargs.keys()[0]
        expected_value = kwargs[attribute]
        branch = self._object_set.get(branch_id)
        if branch is None:
            return None
        if expected_value is getattr(branch, attribute):
            return branch
        return None


class FakeDatabaseObject:
    """Base class for fake database objects."""

    def _set_object_set(self, object_set):
        self.__storm_object_info__ = {'store': FakeStore(object_set)}


class ObjectSet:
    """Generic set of database objects."""

    def __init__(self):
        self._objects = {}
        self._next_id = 1

    def _add(self, db_object):
        self._objects[self._next_id] = db_object
        db_object.id = self._next_id
        self._next_id += 1
        db_object._set_object_set(self)
        return db_object

    def _delete(self, db_object):
        del self._objects[db_object.id]

    def __iter__(self):
        return self._objects.itervalues()

    def _find(self, **kwargs):
        [(key, value)] = kwargs.items()
        for obj in self:
            if getattr(obj, key) == value:
                return obj

    def get(self, id):
        return self._objects.get(id, None)

    def getByName(self, name):
        return self._find(name=name)


class FakeSourcePackage:
    """Fake ISourcePackage."""

    def __init__(self, sourcepackagename, distroseries):
        self.sourcepackagename = sourcepackagename
        self.distroseries = distroseries

    def __hash__(self):
        return hash((self.sourcepackagename.id, self.distroseries.id))

    def __eq__(self, other):
        return (self.sourcepackagename.id == other.sourcepackagename.id
                and self.distroseries.id == other.distroseries.id)

    def __ne__(self, other):
        return not (self == other)

    @property
    def distribution(self):
        if self.distroseries is not None:
            return self.distroseries.distribution
        else:
            return None

    @property
    def development_version(self):
        name = '%s-devel' % self.distribution.name
        dev_series = self._distroseries_set.getByName(name)
        if dev_series is None:
            dev_series = FakeDistroSeries(name, self.distribution)
            self._distroseries_set._add(dev_series)
        return self.__class__(self.sourcepackagename, dev_series)

    @property
    def path(self):
        return '%s/%s/%s' % (
            self.distribution.name,
            self.distroseries.name,
            self.sourcepackagename.name)

    def getBranch(self, pocket):
        return self.distroseries._linked_branches.get(
            (self, pocket), None)

    def setBranch(self, pocket, branch, registrant):
        self.distroseries._linked_branches[self, pocket] = branch


@adapter(FakeSourcePackage)
@implementer(IBranchTarget)
def fake_source_package_to_branch_target(fake_package):
    return PackageBranchTarget(fake_package)


class FakeBranch(FakeDatabaseObject):
    """Fake branch object."""

    def __init__(self, branch_type, name, owner, url=None, product=None,
                 stacked_on=None, private=False, registrant=None,
                 distroseries=None, sourcepackagename=None):
        self.branch_type = branch_type
        self.last_mirror_attempt = None
        self.last_mirrored = None
        self.last_mirrored_id = None
        self.next_mirror_time = None
        self.url = url
        self.mirror_failures = 0
        self.name = name
        self.owner = owner
        self.stacked_on = None
        self.mirror_status_message = None
        self.stacked_on = stacked_on
        self.private = private
        self.product = product
        self.registrant = registrant
        self._mirrored = False
        self.distroseries = distroseries
        self.sourcepackagename = sourcepackagename

    @property
    def unique_name(self):
        if self.product is None:
            if self.distroseries is None:
                product = '+junk'
            else:
                product = '%s/%s/%s' % (
                    self.distroseries.distribution.name,
                    self.distroseries.name,
                    self.sourcepackagename.name)
        else:
            product = self.product.name
        return '~%s/%s/%s' % (self.owner.name, product, self.name)

    def getPullURL(self):
        return 'lp-fake:///' + self.unique_name

    @property
    def target(self):
        if self.product is None:
            if self.distroseries is None:
                target = self.owner
            else:
                target = self.sourcepackage
        else:
            target = self.product
        return IBranchTarget(target)

    def requestMirror(self):
        self.next_mirror_time = UTC_NOW


class FakePerson(FakeDatabaseObject):
    """Fake person object."""

    def __init__(self, name):
        self.name = self.displayname = name

    def isTeam(self):
        return False

    def inTeam(self, person_or_team):
        if self is person_or_team:
            return True
        if not person_or_team.isTeam():
            return False
        return self in person_or_team._members


class FakeTeam(FakePerson):
    """Fake team."""

    def __init__(self, name, members=None):
        super(FakeTeam, self).__init__(name)
        if members is None:
            self._members = []
        else:
            self._members = list(members)

    def isTeam(self):
        return True


class FakeProduct(FakeDatabaseObject):
    """Fake product."""

    def __init__(self, name):
        self.name = name
        self.development_focus = FakeProductSeries()


@adapter(FakeProduct)
@implementer(IBranchTarget)
def fake_product_to_branch_target(fake_product):
    """Adapt a `FakeProduct` to `IBranchTarget`."""
    return ProductBranchTarget(fake_product)


class FakeProductSeries(FakeDatabaseObject):
    """Fake product series."""

    branch = None


class FakeScriptActivity(FakeDatabaseObject):
    """Fake script activity."""

    def __init__(self, name, hostname, date_started, date_completed):
        self.id = self.name = name
        self.hostname = hostname
        self.date_started = datetime_from_tuple(date_started)
        self.date_completed = datetime_from_tuple(date_completed)


class FakeDistribution(FakeDatabaseObject):

    def __init__(self, name):
        self.name = name


class FakeDistroSeries(FakeDatabaseObject):
    """Fake distroseries."""

    def __init__(self, name, distribution):
        self.name = name
        self.distribution = distribution
        self._linked_branches = {}


class FakeSourcePackageName(FakeDatabaseObject):
    """Fake SourcePackageName."""

    def __init__(self, name):
        self.name = name


DEFAULT_PRODUCT = object()


class FakeObjectFactory(ObjectFactory):

    def __init__(self, branch_set, person_set, product_set, distribution_set,
                 distroseries_set, sourcepackagename_set):
        super(FakeObjectFactory, self).__init__()
        self._branch_set = branch_set
        self._person_set = person_set
        self._product_set = product_set
        self._distribution_set = distribution_set
        self._distroseries_set = distroseries_set
        self._sourcepackagename_set = sourcepackagename_set

    def makeBranch(self, branch_type=None, stacked_on=None, private=False,
                   product=DEFAULT_PRODUCT, owner=None, name=None,
                   registrant=None, sourcepackage=None):
        if branch_type is None:
            branch_type = BranchType.HOSTED
        if branch_type == BranchType.MIRRORED:
            url = self.getUniqueURL()
        else:
            url = None
        if name is None:
            name = self.getUniqueString()
        if owner is None:
            owner = self.makePerson()
        if product is DEFAULT_PRODUCT:
            product = self.makeProduct()
        if registrant is None:
            registrant = self.makePerson()
        if sourcepackage is None:
            sourcepackagename = None
            distroseries = None
        else:
            sourcepackagename = sourcepackage.sourcepackagename
            distroseries = sourcepackage.distroseries
        IBranch['name'].validate(unicode(name))
        branch = FakeBranch(
            branch_type, name=name, owner=owner, url=url,
            stacked_on=stacked_on, product=product, private=private,
            registrant=registrant, distroseries=distroseries,
            sourcepackagename=sourcepackagename)
        self._branch_set._add(branch)
        return branch

    def makeAnyBranch(self, **kwargs):
        return self.makeProductBranch(**kwargs)

    def makePackageBranch(self, sourcepackage=None, **kwargs):
        if sourcepackage is None:
            sourcepackage = self.makeSourcePackage()
        return self.makeBranch(
            product=None, sourcepackage=sourcepackage, **kwargs)

    def makePersonalBranch(self, owner=None, **kwargs):
        if owner is None:
            owner = self.makePerson()
        return self.makeBranch(
            owner=owner, product=None, sourcepackage=None, **kwargs)

    def makeProductBranch(self, product=None, **kwargs):
        if product is None:
            product = self.makeProduct()
        return self.makeBranch(product=product, sourcepackage=None, **kwargs)

    def makeDistribution(self):
        distro = FakeDistribution(self.getUniqueString())
        self._distribution_set._add(distro)
        return distro

    def makeDistroRelease(self):
        distro = self.makeDistribution()
        distroseries_name = self.getUniqueString()
        distroseries = FakeDistroSeries(distroseries_name, distro)
        self._distroseries_set._add(distroseries)
        return distroseries

    def makeSourcePackageName(self):
        sourcepackagename = FakeSourcePackageName(self.getUniqueString())
        self._sourcepackagename_set._add(sourcepackagename)
        return sourcepackagename

    def makeSourcePackage(self, distroseries=None, sourcepackagename=None):
        if distroseries is None:
            distroseries = self.makeDistroRelease()
        if sourcepackagename is None:
            sourcepackagename = self.makeSourcePackageName()
        package = FakeSourcePackage(sourcepackagename, distroseries)
        package._distroseries_set = self._distroseries_set
        return package

    def makeTeam(self, owner):
        team = FakeTeam(name=self.getUniqueString(), members=[owner])
        self._person_set._add(team)
        return team

    def makePerson(self):
        person = FakePerson(name=self.getUniqueString())
        self._person_set._add(person)
        return person

    def makeProduct(self):
        product = FakeProduct(self.getUniqueString())
        self._product_set._add(product)
        return product

    def enableDefaultStackingForProduct(self, product, branch=None):
        """Give 'product' a default stacked-on branch.

        :param product: The product to give a default stacked-on branch to.
        :param branch: The branch that should be the default stacked-on
            branch.  If not supplied, a fresh branch will be created.
        """
        if branch is None:
            branch = self.makeBranch(product=product)
        product.development_focus.branch = branch
        branch.last_mirrored = 'rev1'
        return branch

    def enableDefaultStackingForPackage(self, package, branch):
        """Give 'package' a default stacked-on branch.

        :param package: The package to give a default stacked-on branch to.
        :param branch: The branch that should be the default stacked-on
            branch.
        """
        package.development_version.setBranch(
            PackagePublishingPocket.RELEASE, branch, branch.owner)
        branch.last_mirrored = 'rev1'
        return branch


class FakeBranchPuller:

    def __init__(self, branch_set, script_activity_set):
        self._branch_set = branch_set
        self._script_activity_set = script_activity_set

    def _getBranchPullInfo(self, branch):
        default_branch = ''
        if branch.product is not None:
            series = branch.product.development_focus
            user_branch = series.branch
            if (user_branch is not None
                and not (
                    user_branch.private
                    and branch.branch_type == BranchType.MIRRORED)):
                default_branch = '/' + user_branch.unique_name
        return (
            branch.id, branch.getPullURL(), branch.unique_name,
            default_branch)

    def getBranchPullQueue(self, branch_type):
        queue = []
        branch_type = BranchType.items[branch_type]
        for branch in self._branch_set:
            if (branch.branch_type == branch_type
                and branch.next_mirror_time < UTC_NOW):
                queue.append(self._getBranchPullInfo(branch))
        return queue

    def acquireBranchToPull(self):
        branches = sorted(
            [branch for branch in self._branch_set
            if branch.next_mirror_time is not None],
            key=operator.attrgetter('next_mirror_time'))
        if branches:
            branch = branches[-1]
            self.startMirroring(branch.id)
            default_branch = branch.target.default_stacked_on_branch
            if default_branch:
                default_branch_name = default_branch.unique_name
            else:
                default_branch_name = ''
            return (branch.id, branch.getPullURL(), branch.unique_name,
                    default_branch_name, branch.branch_type.name)
        else:
            return ()

    def startMirroring(self, branch_id):
        branch = self._branch_set.get(branch_id)
        if branch is None:
            return faults.NoBranchWithID(branch_id)
        branch.last_mirror_attempt = UTC_NOW
        branch.next_mirror_time = None
        return True

    def mirrorComplete(self, branch_id, last_revision_id):
        branch = self._branch_set.get(branch_id)
        if branch is None:
            return faults.NoBranchWithID(branch_id)
        branch.last_mirrored_id = last_revision_id
        branch.last_mirrored = UTC_NOW
        branch.mirror_failures = 0
        for stacked_branch in self._branch_set:
            if stacked_branch.stacked_on is branch:
                stacked_branch.requestMirror()
        return True

    def mirrorFailed(self, branch_id, reason):
        branch = self._branch_set.get(branch_id)
        if branch is None:
            return faults.NoBranchWithID(branch_id)
        branch.mirror_failures += 1
        branch.mirror_status_message = reason
        return True

    def recordSuccess(self, name, hostname, date_started, date_completed):
        self._script_activity_set._add(
            FakeScriptActivity(name, hostname, date_started, date_completed))
        return True

    def setStackedOn(self, branch_id, stacked_on_location):
        branch = self._branch_set.get(branch_id)
        if branch is None:
            return faults.NoBranchWithID(branch_id)
        if stacked_on_location == '':
            branch.stacked_on = None
            return True
        stacked_on_location = stacked_on_location.rstrip('/')
        for stacked_on_branch in self._branch_set:
            if stacked_on_location == stacked_on_branch.url:
                branch.stacked_on = stacked_on_branch
                break
            if stacked_on_location == '/' + stacked_on_branch.unique_name:
                branch.stacked_on = stacked_on_branch
                break
        else:
            return faults.NoSuchBranch(stacked_on_location)
        return True


class FakeBranchFilesystem:

    def __init__(self, branch_set, person_set, product_set, distribution_set,
                 distroseries_set, sourcepackagename_set, factory):
        self._branch_set = branch_set
        self._person_set = person_set
        self._product_set = product_set
        self._distribution_set = distribution_set
        self._distroseries_set = distroseries_set
        self._sourcepackagename_set = sourcepackagename_set
        self._factory = factory

    def createBranch(self, requester_id, branch_path):
        if not branch_path.startswith('/'):
            return faults.InvalidPath(branch_path)
        escaped_path = unescape(branch_path.strip('/')).encode('utf-8')
        try:
            namespace_path, branch_name = escaped_path.rsplit('/', 1)
        except ValueError:
            return faults.PermissionDenied(
                "Cannot create branch at '%s'" % branch_path)
        data = BranchNamespaceSet().parse(namespace_path)
        owner = self._person_set.getByName(data['person'])
        if owner is None:
            return faults.NotFound(
                "User/team %r does not exist." % (data['person'],))
        registrant = self._person_set.get(requester_id)
        # The real code consults the branch creation policy of the product. We
        # don't need to do so here, since the tests above this layer never
        # encounter that behaviour. If they *do* change to rely on the branch
        # creation policy, the observed behaviour will be failure to raise
        # exceptions.
        if not registrant.inTeam(owner):
            return faults.PermissionDenied(
                ('%s cannot create branches owned by %s'
                 % (registrant.displayname, owner.displayname)))
        product = sourcepackage = None
        if data['product'] == '+junk':
            product = None
        elif data['product'] is not None:
            product = self._product_set.getByName(data['product'])
            if product is None:
                return faults.NotFound(
                    "Project %r does not exist." % (data['product'],))
        elif data['distribution'] is not None:
            distro = self._distribution_set.getByName(data['distribution'])
            if distro is None:
                return faults.NotFound(
                    "No such distribution: '%s'." % (data['distribution'],))
            distroseries = self._distroseries_set.getByName(
                data['distroseries'])
            if distroseries is None:
                return faults.NotFound(
                    "No such distribution series: '%s'."
                    % (data['distroseries'],))
            sourcepackagename = self._sourcepackagename_set.getByName(
                data['sourcepackagename'])
            if sourcepackagename is None:
                return faults.NotFound(
                    "No such source package: '%s'."
                    % (data['sourcepackagename'],))
            sourcepackage = self._factory.makeSourcePackage(
                distroseries, sourcepackagename)
        else:
            return faults.PermissionDenied(
                "Cannot create branch at '%s'" % branch_path)
        try:
            return self._factory.makeBranch(
                owner=owner, name=branch_name, product=product,
                sourcepackage=sourcepackage, registrant=registrant,
                branch_type=BranchType.HOSTED).id
        except LaunchpadValidationError, e:
            return faults.PermissionDenied(str(e))

    def requestMirror(self, requester_id, branch_id):
        self._branch_set.get(branch_id).requestMirror()

    def _canRead(self, person_id, branch):
        """Can the person 'person_id' see 'branch'?"""
        # This is a substitute for an actual launchpad.View check on the
        # branch. It doesn't have to match the behaviour exactly, as long as
        # it's stricter than the real implementation (that way, mismatches in
        # behaviour should generate explicit errors.)
        if person_id == LAUNCHPAD_SERVICES:
            return True
        if person_id == LAUNCHPAD_ANONYMOUS:
            return not branch.private
        if not branch.private:
            return True
        person = self._person_set.get(person_id)
        return person.inTeam(branch.owner)

    def _canWrite(self, person_id, branch):
        """Can the person 'person_id' write to 'branch'?"""
        if person_id in [LAUNCHPAD_ANONYMOUS, LAUNCHPAD_SERVICES]:
            return False
        if branch.branch_type != BranchType.HOSTED:
            return False
        person = self._person_set.get(person_id)
        return person.inTeam(branch.owner)

    def _get_product_target(self, path):
        try:
            owner_name, product_name = path.split('/')
        except ValueError:
            # Wrong number of segments -- can't be a product.
            return
        product = self._product_set.getByName(product_name)
        return product

    def _get_package_target(self, path):
        try:
            owner_name, distro_name, series_name, package_name = (
                path.split('/'))
        except ValueError:
            # Wrong number of segments -- can't be a package.
            return
        distro = self._distribution_set.getByName(distro_name)
        distroseries = self._distroseries_set.getByName(series_name)
        sourcepackagename = self._sourcepackagename_set.getByName(
            package_name)
        if None in (distro, distroseries, sourcepackagename):
            return
        return self._factory.makeSourcePackage(
            distroseries, sourcepackagename)

    def _serializeControlDirectory(self, requester, product_path,
                                   trailing_path):
        if not ('.bzr' == trailing_path or trailing_path.startswith('.bzr/')):
            return
        target = self._get_product_target(product_path)
        if target is None:
            target = self._get_package_target(product_path)
        if target is None:
            return
        default_branch = IBranchTarget(target).default_stacked_on_branch
        if default_branch is None:
            return
        if not self._canRead(requester, default_branch):
            return
        return (
            CONTROL_TRANSPORT,
            {'default_stack_on': escape('/' + default_branch.unique_name)},
            trailing_path)

    def _serializeBranch(self, requester_id, branch, trailing_path):
        if not self._canRead(requester_id, branch):
            return faults.PermissionDenied()
        elif branch.branch_type == BranchType.REMOTE:
            return None
        else:
            return (
                BRANCH_TRANSPORT,
                {'id': branch.id,
                 'writable': self._canWrite(requester_id, branch),
                 }, trailing_path)

    def translatePath(self, requester_id, path):
        if not path.startswith('/'):
            return faults.InvalidPath(path)
        stripped_path = path.strip('/')
        for first, second in iter_split(stripped_path, '/'):
            first = unescape(first).encode('utf-8')
            # Is it a branch?
            branch = self._branch_set._find(unique_name=first)
            if branch is not None:
                branch = self._serializeBranch(requester_id, branch, second)
                if isinstance(branch, Fault):
                    return branch
                elif branch is None:
                    break
                return branch

            # Is it a product?
            product = self._serializeControlDirectory(
                requester_id, first, second)
            if product:
                return product
        return faults.PathTranslationError(path)


class InMemoryFrontend:
    """A in-memory 'frontend' to Launchpad's branch services.

    This is an in-memory version of `LaunchpadDatabaseFrontend`.
    """

    def __init__(self):
        self._branch_set = ObjectSet()
        self._script_activity_set = ObjectSet()
        self._person_set = ObjectSet()
        self._product_set = ObjectSet()
        self._distribution_set = ObjectSet()
        self._distroseries_set = ObjectSet()
        self._sourcepackagename_set = ObjectSet()
        self._factory = FakeObjectFactory(
            self._branch_set, self._person_set, self._product_set,
            self._distribution_set, self._distroseries_set,
            self._sourcepackagename_set)
        self._puller = FakeBranchPuller(
            self._branch_set, self._script_activity_set)
        self._branchfs = FakeBranchFilesystem(
            self._branch_set, self._person_set, self._product_set,
            self._distribution_set, self._distroseries_set,
            self._sourcepackagename_set, self._factory)
        sm = getSiteManager()
        sm.registerAdapter(fake_product_to_branch_target)
        sm.registerAdapter(fake_source_package_to_branch_target)

    def getFilesystemEndpoint(self):
        """See `LaunchpadDatabaseFrontend`.

        Return an in-memory implementation of IBranchFileSystem that passes
        the tests in `test_codehosting`.
        """
        return self._branchfs

    def getPullerEndpoint(self):
        """See `LaunchpadDatabaseFrontend`.

        Return an in-memory implementation of IBranchPuller that passes the
        tests in `test_codehosting`.
        """
        return self._puller

    def getLaunchpadObjectFactory(self):
        """See `LaunchpadDatabaseFrontend`.

        Returns a partial, in-memory implementation of LaunchpadObjectFactory
        -- enough to pass the tests.
        """
        return self._factory

    def getBranchLookup(self):
        """See `LaunchpadDatabaseFrontend`.

        Returns a partial implementation of `IBranchLookup` -- enough to pass
        the tests.
        """
        return self._branch_set

    def getLastActivity(self, activity_name):
        """Get the last script activity with 'activity_name'."""
        return self._script_activity_set.getByName(activity_name)


class XMLRPCWrapper:
    """Wrapper around the endpoints that emulates an XMLRPC client."""

    def __init__(self, endpoint):
        self.endpoint = endpoint

    def callRemote(self, method_name, *args):
        result = getattr(self.endpoint, method_name)(*args)
        if isinstance(result, Fault):
            raise result
        return result
