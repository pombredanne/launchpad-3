# Copyright 2009-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interfaces for searching bug tasks. Mostly used with IBugTaskSet."""

__metaclass__ = type

__all__ = [
    'BugTaskSearchParams',
    ]

import collections

from zope.security.proxy import isinstance as zope_isinstance

from lp.bugs.interfaces.bugtask import (
    BugTagsSearchCombinator,
    UNRESOLVED_BUGTASK_STATUSES,
    )
from lp.services.searchbuilder import (
    all,
    any,
    NULL,
    )


class BugTaskSearchParams:
    """Encapsulates search parameters for BugTask.search()

    Details:

      user is an object that provides IPerson, and represents the
      person performing the query (which is important to know for, for
      example, privacy-aware results.) If user is None, the search
      will be filtered to only consider public bugs.

      product, distribution and distroseries (IBugTargets) should /not/
      be supplied to BugTaskSearchParams; instead, IBugTarget's
      searchTasks() method should be invoked with a single search_params
      argument.

      Keyword arguments should always be used. The argument passing
      semantics are as follows:

        * BugTaskSearchParams(arg='foo', user=bar): Match all IBugTasks
          where IBugTask.arg == 'foo' for user bar.

        * BugTaskSearchParams(arg=any('foo', 'bar')): Match all
          IBugTasks where IBugTask.arg == 'foo' or IBugTask.arg ==
          'bar'. In this case, no user was passed, so all private bugs
          are excluded from the search results.

        * BugTaskSearchParams(arg1='foo', arg2='bar'): Match all
          IBugTasks where IBugTask.arg1 == 'foo' and IBugTask.arg2 ==
          'bar'

    The set will be ordered primarily by the column specified in orderby,
    and then by bugtask id.

    For a more thorough treatment, check out:

        lib/lp/bugs/doc/bugtask-search.txt
    """

    product = None
    project = None
    distribution = None
    distroseries = None
    productseries = None

    def __init__(self, user, bug=None, searchtext=None, fast_searchtext=None,
                 status=None, importance=None, milestone=None,
                 milestone_tag=None, assignee=None, sourcepackagename=None,
                 owner=None, attachmenttype=None, orderby=None,
                 omit_dupes=False, subscriber=None, component=None,
                 pending_bugwatch_elsewhere=False, resolved_upstream=False,
                 open_upstream=False, has_no_upstream_bugtask=False, tag=None,
                 has_cve=False, bug_supervisor=None, bug_reporter=None,
                 nominated_for=None, bug_commenter=None, omit_targeted=False,
                 date_closed=None, affected_user=None, affects_me=False,
                 hardware_bus=None, hardware_vendor_id=None,
                 hardware_product_id=None, hardware_driver_name=None,
                 hardware_driver_package_name=None,
                 hardware_owner_is_bug_reporter=None,
                 hardware_owner_is_affected_by_bug=False,
                 hardware_owner_is_subscribed_to_bug=False,
                 hardware_is_linked_to_bug=False,
                 linked_branches=None, linked_blueprints=None,
                 structural_subscriber=None, modified_since=None,
                 created_since=None, exclude_conjoined_tasks=False, cve=None,
                 upstream_target=None, milestone_dateexpected_before=None,
                 milestone_dateexpected_after=None, created_before=None,
                 information_type=None):

        self.bug = bug
        self.searchtext = searchtext
        self.fast_searchtext = fast_searchtext
        self.status = status
        self.importance = importance
        self.milestone = milestone
        self.milestone_tag = milestone_tag
        self.assignee = assignee
        self.sourcepackagename = sourcepackagename
        self.owner = owner
        self.attachmenttype = attachmenttype
        self.user = user
        self.orderby = orderby
        self.omit_dupes = omit_dupes
        self.omit_targeted = omit_targeted
        self.subscriber = subscriber
        self.component = component
        self.pending_bugwatch_elsewhere = pending_bugwatch_elsewhere
        self.resolved_upstream = resolved_upstream
        self.open_upstream = open_upstream
        self.has_no_upstream_bugtask = has_no_upstream_bugtask
        self.tag = tag
        self.has_cve = has_cve
        self.bug_supervisor = bug_supervisor
        self.bug_reporter = bug_reporter
        self.nominated_for = nominated_for
        self.bug_commenter = bug_commenter
        self.date_closed = date_closed
        self.affected_user = affected_user
        self.affects_me = affects_me
        self.hardware_bus = hardware_bus
        self.hardware_vendor_id = hardware_vendor_id
        self.hardware_product_id = hardware_product_id
        self.hardware_driver_name = hardware_driver_name
        self.hardware_driver_package_name = hardware_driver_package_name
        self.hardware_owner_is_bug_reporter = hardware_owner_is_bug_reporter
        self.hardware_owner_is_affected_by_bug = (
            hardware_owner_is_affected_by_bug)
        self.hardware_owner_is_subscribed_to_bug = (
            hardware_owner_is_subscribed_to_bug)
        self.hardware_is_linked_to_bug = hardware_is_linked_to_bug
        self.linked_branches = linked_branches
        self.linked_blueprints = linked_blueprints
        self.structural_subscriber = structural_subscriber
        self.modified_since = modified_since
        self.created_since = created_since
        self.created_before = created_before
        self.exclude_conjoined_tasks = exclude_conjoined_tasks
        self.cve = cve
        self.upstream_target = upstream_target
        self.milestone_dateexpected_before = milestone_dateexpected_before
        self.milestone_dateexpected_after = milestone_dateexpected_after
        if isinstance(information_type, collections.Iterable):
            self.information_type = set(information_type)
        elif information_type:
            self.information_type = set((information_type,))
        else:
            self.information_type = None

    def setProduct(self, product):
        """Set the upstream context on which to filter the search."""
        self.product = product

    def setProject(self, project):
        """Set the upstream context on which to filter the search."""
        self.project = project

    def setDistribution(self, distribution):
        """Set the distribution context on which to filter the search."""
        self.distribution = distribution

    def setDistroSeries(self, distroseries):
        """Set the distroseries context on which to filter the search."""
        self.distroseries = distroseries

    def setProductSeries(self, productseries):
        """Set the productseries context on which to filter the search."""
        self.productseries = productseries

    def setSourcePackage(self, sourcepackage):
        """Set the sourcepackage context on which to filter the search."""
        # Import this here to avoid circular dependencies
        from lp.registry.interfaces.sourcepackage import (
            ISourcePackage)
        if isinstance(sourcepackage, any):
            # Unwrap the source package.
            self.sourcepackagename = any(*[
                pkg.sourcepackagename for pkg in sourcepackage.query_values])
            distroseries = any(*[pkg.distroseries for pkg in
                sourcepackage.query_values if ISourcePackage.providedBy(pkg)])
            distributions = any(*[pkg.distribution for pkg in
                sourcepackage.query_values
                if not ISourcePackage.providedBy(pkg)])
            if distroseries.query_values and not distributions.query_values:
                self.distroseries = distroseries
            elif not distroseries.query_values and distributions.query_values:
                self.distributions = distributions
            else:
                # At this point we have determined that either we have both
                # distroseries and distributions, or we have neither of them.
                # We will set both.  Doing so will give us the cross-product,
                # because searching source packages is
                # sourcepackagename-specific rather than actually
                # context-specific. This is not ideal but is tolerable given
                # no actual use of mixed-type any() exists today.
                self.distroseries = distroseries
                self.distributions = distributions
            return
        if ISourcePackage.providedBy(sourcepackage):
            # This is a sourcepackage in a distro series.
            self.distroseries = sourcepackage.distroseries
        else:
            # This is a sourcepackage in a distribution.
            self.distribution = sourcepackage.distribution
        self.sourcepackagename = sourcepackage.sourcepackagename

    def setTarget(self, target):
        """Constrain the search to only return items in target.

        This is equivalent to calling setProduct etc but the type of target
        does not need to be known to the caller.

        :param target: A `IHasBug`, or some search term like all/any/none on
            `IHasBug`. If using all/any all the targets must be of the
            same type due to implementation limitations. Currently only
            distroseries and productseries `IHasBug` implementations are
            supported.
        """
        # Yay circular deps.
        from lp.registry.interfaces.distribution import IDistribution
        from lp.registry.interfaces.distroseries import IDistroSeries
        from lp.registry.interfaces.product import IProduct
        from lp.registry.interfaces.productseries import IProductSeries
        from lp.registry.interfaces.milestone import IMilestone
        from lp.registry.interfaces.projectgroup import IProjectGroup
        from lp.registry.interfaces.sourcepackage import ISourcePackage
        from lp.registry.interfaces.distributionsourcepackage import \
            IDistributionSourcePackage
        if isinstance(target, (any, all)):
            assert len(target.query_values), \
                'cannot determine target with no targets'
            instance = target.query_values[0]
        else:
            instance = target
        if IDistribution.providedBy(instance):
            self.setDistribution(target)
        elif IDistroSeries.providedBy(instance):
            self.setDistroSeries(target)
        elif IProduct.providedBy(instance):
            self.setProduct(target)
        elif IProductSeries.providedBy(instance):
            self.setProductSeries(target)
        elif IMilestone.providedBy(instance):
            self.milestone = target
        elif ISourcePackage.providedBy(instance):
            self.setSourcePackage(target)
        elif IDistributionSourcePackage.providedBy(instance):
            self.setSourcePackage(target)
        elif IProjectGroup.providedBy(instance):
            self.setProject(target)
        else:
            raise AssertionError("unknown target type %r" % target)

    @classmethod
    def _anyfy(cls, value):
        """If value is a sequence, wrap its items with the `any` combinator.

        Otherwise, return value as is, or None if it's a zero-length sequence.
        """
        if zope_isinstance(value, (list, tuple)):
            if len(value) > 1:
                return any(*value)
            elif len(value) == 1:
                return value[0]
            else:
                return None
        else:
            return value

    @classmethod
    def fromSearchForm(cls, user,
                       order_by=('-importance', ), search_text=None,
                       status=list(UNRESOLVED_BUGTASK_STATUSES),
                       importance=None,
                       assignee=None, bug_reporter=None, bug_supervisor=None,
                       bug_commenter=None, bug_subscriber=None, owner=None,
                       affected_user=None, affects_me=False,
                       has_patch=None, has_cve=None,
                       distribution=None, tags=None,
                       tags_combinator=BugTagsSearchCombinator.ALL,
                       omit_duplicates=True, omit_targeted=None,
                       status_upstream=None, milestone_assignment=None,
                       milestone=None, component=None, nominated_for=None,
                       sourcepackagename=None, has_no_package=None,
                       hardware_bus=None, hardware_vendor_id=None,
                       hardware_product_id=None, hardware_driver_name=None,
                       hardware_driver_package_name=None,
                       hardware_owner_is_bug_reporter=None,
                       hardware_owner_is_affected_by_bug=False,
                       hardware_owner_is_subscribed_to_bug=False,
                       hardware_is_linked_to_bug=False, linked_branches=None,
                       linked_blueprints=None, structural_subscriber=None,
                       modified_since=None, created_since=None,
                       created_before=None, information_type=None):
        """Create and return a new instance using the parameter list."""
        search_params = cls(user=user, orderby=order_by)

        search_params.searchtext = search_text
        search_params.status = cls._anyfy(status)
        search_params.importance = cls._anyfy(importance)
        search_params.assignee = assignee
        search_params.bug_reporter = bug_reporter
        search_params.bug_supervisor = bug_supervisor
        search_params.bug_commenter = bug_commenter
        search_params.subscriber = bug_subscriber
        search_params.owner = owner
        search_params.affected_user = affected_user
        search_params.distribution = distribution
        if has_patch:
            # Import this here to avoid circular imports
            from lp.bugs.interfaces.bugattachment import (
                BugAttachmentType)
            search_params.attachmenttype = BugAttachmentType.PATCH
        search_params.has_cve = has_cve
        if zope_isinstance(tags, (list, tuple)):
            if len(tags) > 0:
                if tags_combinator == BugTagsSearchCombinator.ALL:
                    search_params.tag = all(*tags)
                else:
                    search_params.tag = any(*tags)
        elif zope_isinstance(tags, str):
            search_params.tag = tags
        elif tags is None:
            pass  # tags not supplied
        else:
            raise AssertionError(
                'Tags can only be supplied as a list or a string.')
        search_params.omit_dupes = omit_duplicates
        search_params.omit_targeted = omit_targeted
        if status_upstream is not None:
            if 'pending_bugwatch' in status_upstream:
                search_params.pending_bugwatch_elsewhere = True
            if 'resolved_upstream' in status_upstream:
                search_params.resolved_upstream = True
            if 'open_upstream' in status_upstream:
                search_params.open_upstream = True
            if 'hide_upstream' in status_upstream:
                search_params.has_no_upstream_bugtask = True
        search_params.milestone = cls._anyfy(milestone)
        search_params.component = cls._anyfy(component)
        search_params.sourcepackagename = sourcepackagename
        if has_no_package:
            search_params.sourcepackagename = NULL
        search_params.nominated_for = nominated_for

        search_params.hardware_bus = hardware_bus
        search_params.hardware_vendor_id = hardware_vendor_id
        search_params.hardware_product_id = hardware_product_id
        search_params.hardware_driver_name = hardware_driver_name
        search_params.hardware_driver_package_name = (
            hardware_driver_package_name)
        search_params.hardware_owner_is_bug_reporter = (
            hardware_owner_is_bug_reporter)
        search_params.hardware_owner_is_affected_by_bug = (
            hardware_owner_is_affected_by_bug)
        search_params.hardware_owner_is_subscribed_to_bug = (
            hardware_owner_is_subscribed_to_bug)
        search_params.hardware_is_linked_to_bug = (
            hardware_is_linked_to_bug)
        search_params.linked_branches = linked_branches
        search_params.linked_blueprints = linked_blueprints
        search_params.structural_subscriber = structural_subscriber
        search_params.modified_since = modified_since
        search_params.created_since = created_since
        search_params.created_before = created_before
        search_params.information_type = information_type

        return search_params


