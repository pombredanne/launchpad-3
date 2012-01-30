# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""SpecificationWorkItem interfaces."""

__metaclass__ = type

__all__ = [
    'ISpecificationWorkItem',
    ]


class ISpecificationWorkItem(Interface):
    """SpecificationWorkItem's public attributes and methods."""

    id = Int(title=_("Database ID"), required=True, readonly=True)

    title = exported(
        SpecNameField(
            title=_('Title'), required=True, readonly=False,
            description=_(
                "Work item title.")),
        as_of="devel")

    assignee = exported(
        PublicPersonChoice(
            title=_('Assignee'), required=False,
            description=_(
                "The person responsible for implementing the work item."),
            vocabulary='ValidPersonOrTeam'),
        as_of="devel")

    datecreated = exported(
        Datetime(
            title=_('Date Created'), required=True, readonly=True),
        as_of="devel",
        exported_as="date_created",
        )

    # milestone
    milestone = exported(
        ReferenceChoice(
            title=_('Milestone'), required=False, vocabulary='Milestone',
            description=_(
                "The milestone to which this work item is targetted. If this "
                "is not set, then the target is the specification's"
                " milestone."),
            schema=IMilestone),
        as_of="devel")

    status = exported(
        Choice(
            title=_("Work Item Status"), required=True, readonly=True,
            default=SpecificationWorkItemStatus.UNKNOWN,
            vocabulary=SpecificationWorkItemStatus,
            description=_(
                "The state of progress being made on the actual "
                "implementation of this work item.")),
        as_of="devel")

    specification = exported(
        Object(title=_('The specification that the work item is linked to.'),
        required=True, readonly=True, schema=ISpecification),
        as_of="devel")

    deleted = exported(
        Bool(title=_('Is this work item deleted?'),
             required=True, default=False,
             description=_(
                "Marks the work item as deleted.")),
        as_of="devel")

