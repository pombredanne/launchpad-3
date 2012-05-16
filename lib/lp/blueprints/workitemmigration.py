# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Helper functions for the migration of work items from whiteboards to the
SpecificationWorkItem table.

This will be removed once the migration is done.
"""

__metaclass__ = type
__all__ = [
    'extractWorkItemsFromWhiteboard',
    ]

import re

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from lp.blueprints.enums import SpecificationWorkItemStatus
from lp.registry.interfaces.person import IPersonSet


class WorkItemParseError(Exception):
    """An error when parsing a work item line from a blueprint's whiteboard."""


class WorkitemParser(object):
    """A parser to extract work items from Blueprint whiteboards."""

    def __init__(self, blueprint):
        self.blueprint = blueprint

    def _normalize_status(self, status, desc):
        status = status.strip().lower()
        if not status:
            status = SpecificationWorkItemStatus.TODO
        elif status == u'completed':
            status = SpecificationWorkItemStatus.DONE
        elif status in (u'postpone', u'dropped', u'drop'):
            status = SpecificationWorkItemStatus.POSTPONED
        else:
            valid_statuses = SpecificationWorkItemStatus.items
            if status not in [item.name.lower() for item in valid_statuses]:
                raise WorkItemParseError('Unknown status: %s' % status)
            return valid_statuses[status.upper()]
        return status

    def _parse_line(self, line):
        try:
            desc, status = line.rsplit(':', 1)
        except ValueError:
            desc = line
            status = ""
        assignee_name = None
        if desc.startswith('['):
            if ']' in desc:
                off = desc.index(']')
                assignee_name = desc[1:off]
                desc = desc[off + 1:].strip()
            else:
                raise WorkItemParseError('Missing closing "]" for assignee')
        return assignee_name, desc, status

    def parse_blueprint_workitem(self, line):
        line = line.strip()
        assert line, "Please don't give us an empty line"
        assignee_name, desc, status = self._parse_line(line)
        if not desc:
            raise WorkItemParseError(
                'No work item description found on "%s"' % line)
        status = self._normalize_status(status, desc)
        return assignee_name, desc, status


def milestone_extract(text, valid_milestones):
    words = text.replace('(', ' ').replace(')', ' ').replace(
        '[', ' ').replace(']', ' ').replace('<wbr />', '').split()
    for milestone in valid_milestones:
        for word in words:
            if word == milestone.name:
                return milestone
    raise WorkItemParseError("No valid milestones found in %s" % words)


def extractWorkItemsFromWhiteboard(spec):
    work_items = []
    if not spec.whiteboard:
        return work_items
    work_items_re = re.compile('^work items(.*)\s*:\s*$', re.I)
    meta_re = re.compile('^Meta.*?:$', re.I)
    complexity_re = re.compile('^Complexity.*?:$', re.I)
    in_wi_block = False
    new_whiteboard = []

    target_milestones = list(spec.target.milestones)
    wi_lines = []
    # Iterate over all lines in the whiteboard and whenever we find a line
    # matching work_items_re we 'continue' and store the following lines
    # until we reach the end of the whiteboard or a line matching meta_re or
    # complexity_re.
    for line in spec.whiteboard.splitlines():
        new_whiteboard.append(line)
        wi_match = work_items_re.search(line)
        if wi_match:
            in_wi_block = True
            milestone = None
            milestone_part = wi_match.group(1).strip()
            if milestone_part:
                milestone = milestone_extract(
                    milestone_part, target_milestones)
            new_whiteboard.pop()
            continue
        if meta_re.search(line):
            milestone = None
            in_wi_block = False
            continue
        if complexity_re.search(line):
            milestone = None
            in_wi_block = False
            continue

        if not in_wi_block:
            # We only care about work-item lines.
            continue

        if line.strip() == '':
            # An empty line signals the end of the work-item block:
            # https://wiki.ubuntu.com/WorkItemsHowto.
            in_wi_block = False
            milestone = None
            continue

        # This is a work-item line, which we don't want in the new
        # whiteboard because we're migrating them into the
        # SpecificationWorkItem table.
        new_whiteboard.pop()

        wi_lines.append((line, milestone))

    # Now parse the work item lines and store them in SpecificationWorkItem.
    parser = WorkitemParser(spec)
    sequence = 0
    for line, milestone in wi_lines:
        assignee_name, title, status = parser.parse_blueprint_workitem(line)
        if assignee_name is not None:
            assignee_name = assignee_name.strip()
            assignee = getUtility(IPersonSet).getByName(assignee_name)
            if assignee is None:
                raise ValueError("Unknown person name: %s" % assignee_name)
        else:
            assignee = None
        workitem = removeSecurityProxy(spec).newWorkItem(
            status=status, title=title, assignee=assignee,
            milestone=milestone, sequence=sequence)
        work_items.append(workitem)
        sequence += 1

    removeSecurityProxy(spec).whiteboard = "\n".join(new_whiteboard)
    return work_items
