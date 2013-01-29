# Copyright 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Helper methods to search specifications."""

__metaclass__ = type
__all__ = [
    'get_specification_filters',
    'get_specification_active_product_filter',
    'get_specification_privacy_filter',
    'search_specifications',
    ]

from storm.expr import (
    And,
    Coalesce,
    Join,
    LeftJoin,
    Not,
    Or,
    Select,
    )
from storm.locals import (
    Desc,
    SQL,
    )
from zope.component import getUtility

from lp.app.enums import PUBLIC_INFORMATION_TYPES
from lp.blueprints.enums import (
    SpecificationDefinitionStatus,
    SpecificationFilter,
    SpecificationGoalStatus,
    SpecificationImplementationStatus,
    SpecificationSort,
    )
from lp.blueprints.model.specification import Specification
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.product import IProduct
from lp.registry.interfaces.productseries import IProductSeries
from lp.registry.interfaces.role import IPersonRoles
from lp.registry.model.teammembership import TeamParticipation
from lp.services.database.decoratedresultset import DecoratedResultSet
from lp.services.database.lpstorm import IStore
from lp.services.database.stormexpr import (
    Array,
    ArrayAgg,
    ArrayIntersects,
    fti_search,
    )
from lp.services.propertycache import get_property_cache


def search_specifications(context, base_clauses, user, sort=None,
                          quantity=None, spec_filter=None, prejoin_people=True,
                          tables=[], default_acceptance=False):
    store = IStore(Specification)
    if not default_acceptance:
        default = SpecificationFilter.INCOMPLETE
        options = set([
            SpecificationFilter.COMPLETE, SpecificationFilter.INCOMPLETE])
    else:
        default = SpecificationFilter.ACCEPTED
        options = set([
            SpecificationFilter.ACCEPTED, SpecificationFilter.DECLINED,
            SpecificationFilter.PROPOSED])
    if not spec_filter:
        spec_filter = [default]

    if not set(spec_filter) & options:
        spec_filter.append(default)

    if not tables:
        tables = [Specification]
    clauses = base_clauses
    product_table, product_clauses = get_specification_active_product_filter(
        context)
    tables.extend(product_table)
    for extend in (get_specification_privacy_filter(user),
        get_specification_filters(spec_filter), product_clauses):
        clauses.extend(extend)

    # Sort by priority descending, by default.
    if sort is None or sort == SpecificationSort.PRIORITY:
        order = [
            Desc(Specification.priority), Specification.definition_status,
            Specification.name]
    elif sort == SpecificationSort.DATE:
        if SpecificationFilter.COMPLETE in spec_filter:
            # If we are showing completed, we care about date completed.
            order = [Desc(Specification.date_completed), Specification.id]
        else:
            # If not specially looking for complete, we care about date
            # registered.
            order = []
            show_proposed = set(
                [SpecificationFilter.ALL, SpecificationFilter.PROPOSED])
            if default_acceptance and not (set(spec_filter) & show_proposed):
                order.append(Desc(Specification.date_goal_decided))
            order.extend([Desc(Specification.datecreated), Specification.id])
    else:
        order = [sort]
    # Set the _known_viewers property for each specification, as well as
    # preloading the people involved, if asked.
    decorators = []
    if user is not None and not IPersonRoles(user).in_admin:
        decorators.append(_make_cache_user_can_view_spec(user))
    if prejoin_people:
        decorators.append(_preload_specification_people())
    results = store.using(*tables).find(
        Specification, *clauses).order_by(*order).config(limit=quantity)
    return DecoratedResultSet(
        results,
        lambda row: reduce(lambda task, dec: dec(task), decorators, row))


def get_specification_active_product_filter(context):
    if (IDistribution.providedBy(context) or IDistroSeries.providedBy(context)
        or IProduct.providedBy(context) or IProductSeries.providedBy(context)):
        return [], []
    from lp.registry.model.product import Product
    tables = [
        LeftJoin(Product, Specification.productID == Product.id)]
    active_products = (
        Or(Specification.product == None, Product.active == True))
    return tables, [active_products]


def get_specification_privacy_filter(user):
    # Circular imports.
    from lp.registry.model.accesspolicy import AccessPolicyGrant
    public_spec_filter = (
        Specification.information_type.is_in(PUBLIC_INFORMATION_TYPES))

    if user is None:
        return [public_spec_filter]
    elif IPersonRoles.providedBy(user):
        user = user.person

    artifact_grant_query = Coalesce(
        ArrayIntersects(
            SQL('Specification.access_grants'),
            Select(
                ArrayAgg(TeamParticipation.teamID),
                tables=TeamParticipation,
                where=(TeamParticipation.person == user)
            )), False)

    policy_grant_query = Coalesce(
        ArrayIntersects(
            Array(SQL('Specification.access_policy')),
            Select(
                ArrayAgg(AccessPolicyGrant.policy_id),
                tables=(AccessPolicyGrant,
                        Join(TeamParticipation,
                            TeamParticipation.teamID ==
                            AccessPolicyGrant.grantee_id)),
                where=(TeamParticipation.person == user)
            )), False)

    return [Or(public_spec_filter, artifact_grant_query, policy_grant_query)]


def get_specification_filters(filter, goalstatus=True):
    """Return a list of Storm expressions for filtering Specifications.

    :param filters: A collection of SpecificationFilter and/or strings.
        Strings are used for text searches.
    """
    clauses = []
    # ALL is the trump card.
    if SpecificationFilter.ALL in filter:
        return clauses
    # Look for informational specs.
    if SpecificationFilter.INFORMATIONAL in filter:
        clauses.append(
            Specification.implementation_status ==
            SpecificationImplementationStatus.INFORMATIONAL)
    # Filter based on completion.  See the implementation of
    # Specification.is_complete() for more details.
    if SpecificationFilter.COMPLETE in filter:
        clauses.append(get_specification_completeness_clause())
    if SpecificationFilter.INCOMPLETE in filter:
        clauses.append(Not(get_specification_completeness_clause()))

    # Filter for goal status.
    if goalstatus:
        goalstatus = None
        if SpecificationFilter.ACCEPTED in filter:
            goalstatus = SpecificationGoalStatus.ACCEPTED
        elif SpecificationFilter.PROPOSED in filter:
            goalstatus = SpecificationGoalStatus.PROPOSED
        elif SpecificationFilter.DECLINED in filter:
            goalstatus = SpecificationGoalStatus.DECLINED
        if goalstatus:
            clauses.append(Specification.goalstatus == goalstatus)

    if SpecificationFilter.STARTED in filter:
        clauses.append(get_specification_started_clause())

    # Filter for validity. If we want valid specs only, then we should exclude
    # all OBSOLETE or SUPERSEDED specs.
    if SpecificationFilter.VALID in filter:
        clauses.append(Not(Specification.definition_status.is_in([
            SpecificationDefinitionStatus.OBSOLETE,
            SpecificationDefinitionStatus.SUPERSEDED])))
    # Filter for specification text.
    for constraint in filter:
        if isinstance(constraint, basestring):
            # A string in the filter is a text search filter.
            clauses.append(fti_search(Specification, constraint))
    return clauses


def _make_cache_user_can_view_spec(user):
    userid = user.id

    def cache_user_can_view_spec(spec):
        get_property_cache(spec)._known_viewers = set([userid])
        return spec
    return cache_user_can_view_spec


def _preload_specification_people():

    def preload_specification_related_people(spec):
        list(getUtility(IPersonSet).getPrecachedPersonsFromIDs(
            [spec._assigneeID, spec._approverID, spec._drafterID],
            need_validity=True))
        return spec
    return preload_specification_related_people


def get_specification_started_clause():
    return Or(Not(Specification.implementation_status.is_in([
        SpecificationImplementationStatus.UNKNOWN,
        SpecificationImplementationStatus.NOTSTARTED,
        SpecificationImplementationStatus.DEFERRED,
        SpecificationImplementationStatus.INFORMATIONAL])),
        And(Specification.implementation_status ==
                SpecificationImplementationStatus.INFORMATIONAL,
            Specification.definition_status ==
                SpecificationDefinitionStatus.APPROVED))


def get_specification_completeness_clause():
    return Or(
        Specification.implementation_status ==
            SpecificationImplementationStatus.IMPLEMENTED,
        Specification.definition_status.is_in([
            SpecificationDefinitionStatus.OBSOLETE,
            SpecificationDefinitionStatus.SUPERSEDED,
            ]),
        And(
            Specification.implementation_status ==
                SpecificationImplementationStatus.INFORMATIONAL,
            Specification.definition_status ==
                SpecificationDefinitionStatus.APPROVED))
