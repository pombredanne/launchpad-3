# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Interfaces for things which have Specifications."""

__metaclass__ = type

__all__ = [
    'IHasSpecifications',
    'ISpecificationTarget',
    'ISpecificationGoal',
    ]

from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import TextLine

from lazr.lifecycle.snapshot import doNotSnapshot
from lazr.restful.declarations import (
    exported,
    export_as_webservice_entry,
    export_read_operation,
    operation_for_version,
    operation_parameters,
    operation_returns_entry,
    )
from lazr.restful.fields import (
    CollectionField,
    Reference,
    )

from canonical.launchpad import _


class IHasSpecifications(Interface):
    """An object that has specifications attached to it.

    For example, people, products and distributions have specifications
    associated with them, and you can use this interface to query those.
    """

    all_specifications = exported(doNotSnapshot(
        CollectionField(
            title=_("All specifications"),
            value_type=Reference(schema=Interface),  # ISpecification, really.
            readonly=True,
            description=_(
                'A list of all specifications, regardless of status or '
                'approval or completion, for this object.'))),
                                  as_of="devel")

    has_any_specifications = Attribute(
        'A true or false indicator of whether or not this object has any '
        'specifications associated with it, regardless of their status.')

    valid_specifications = exported(doNotSnapshot(
        CollectionField(
            title=_("Valid specifications"),
            value_type=Reference(schema=Interface),  # ISpecification, really.
            readonly=True,
            description=_(
                'All specifications that are not obsolete. When called from '
                'an ISpecificationGoal it will also exclude the ones that '
                'have not been accepted for that goal'))),
                                    as_of="devel")

    latest_specifications = Attribute(
        "The latest 5 specifications registered for this context.")

    latest_completed_specifications = Attribute(
        "The 5 specifications most recently completed for this context.")

    def specifications(quantity=None, sort=None, filter=None,
                       prejoin_people=True):
        """Specifications for this target.

        The sort is a dbschema which indicates the preferred sort order. The
        filter is an indicator of the kinds of specs to be returned, and
        appropriate filters depend on the kind of object this method is on.
        If there is a quantity, then limit the result to that number.

        In the case where the filter is [] or None, the content class will
        decide what its own appropriate "default" filter is. In some cases,
        it will show all specs, in others, all approved specs, and in
        others, all incomplete specs.

        If prejoin_people=False is specified, then the assignee, drafter
        and approver will not be prejoined. This can be used in
        situations in which these are not rendered.
        """


class ISpecificationTarget(IHasSpecifications):
    """An interface for the objects which actually have unique
    specifications directly attached to them.
    """

    export_as_webservice_entry(as_of="devel")

    @operation_parameters(
        name=TextLine(title=_('The name of the specification')))
    @operation_returns_entry(Interface) # really ISpecification
    @export_read_operation()
    @operation_for_version('devel')
    def getSpecification(name):
        """Returns the specification with the given name, for this target,
        or None.
        """


class ISpecificationGoal(ISpecificationTarget):
    """An interface for those things which can have specifications proposed
    as goals for them.
    """
