# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Helper functions for the migration of work items from whiteboards to the
SpecificationWorkItem table.

This will be removed once the migration is done.
"""

__metaclass__ = type
__all__ = [
    'extractWorkItemsFromWhiteboard',
    'SpecificationWorkitemMigratorProcess',
    ]

import re

from zope.component import getUtility
from zope.interface import implements
from zope.security.proxy import removeSecurityProxy

from lp.services.database.lpstorm import IStore
from lp.services.database.sqlbase import quote_like
from lp.services.looptuner import DBLoopTuner, ITunableLoop

from lp.blueprints.enums import SpecificationWorkItemStatus
from lp.blueprints.model.specification import Specification

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
        '[', ' ').replace(']', ' ').replace('<wbr></wbr>', '').split()
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
            milestone=milestone)
        work_items.append(workitem)

    removeSecurityProxy(spec).whiteboard = "\n".join(new_whiteboard)
    return work_items


class SpecificationWorkitemMigrator:
    """Migrate work-items from Specification.whiteboard to
    SpecificationWorkItem.

    Migrating work items from the whiteboard is an all-or-nothing thing; if we
    encounter any errors when parsing the whiteboard of a spec, we abort the
    transaction and leave its whiteboard unchanged.

    On a test with production data, only 100 whiteboards (out of almost 2500)
    could not be migrated. On 24 of those the assignee in at least one work
    item is not valid, on 33 the status of a work item is not valid and on 42
    one or more milestones are not valid.
    """
    implements(ITunableLoop)

    def __init__(self, transaction, logger, start_at=0):
        self.transaction = transaction
        self.logger = logger
        self.start_at = start_at
        query = "whiteboard ilike '%%' || %s || '%%'" % quote_like(
            'work items')
        self.specs = IStore(Specification).find(Specification, query)
        self.total = self.specs.count()
        self.logger.info(
            "Migrating work items from the whiteboard of %d specs"
            % self.total)

    def getNextBatch(self, chunk_size):
        end_at = self.start_at + int(chunk_size)
        return self.specs[self.start_at:end_at]

    def isDone(self):
        # When the main loop hits the end of the Specifications with work
        # items to migrate it sets start_at to None.  Until we know we hit the
        # end, it always has a numerical value.
        return self.start_at is None

    def __call__(self, chunk_size):
        specs = self.getNextBatch(chunk_size)
        specs_count = specs.count()
        if specs_count == 0:
            self.start_at = None
            return

        for spec in specs:
            try:
                work_items = extractWorkItemsFromWhiteboard(spec)
            except Exception, e:
                self.logger.info(
                    "Failed to parse whiteboard of %s: %s" % (
                        spec, unicode(e)))
                #self.transaction.abort()
                #self.transaction.begin()
                continue

            if len(work_items) > 0:
                self.logger.info(
                    "Migrated %d work items from the whiteboard of %s" % (
                        len(work_items), spec))
                #self.transaction.commit()
                #self.transaction.begin()
            else:
                self.logger.info(
                    "No work items found on the whiteboard of %s" %
                        spec)

        self.transaction.abort()
        self.transaction.begin()
        self.start_at += specs_count


class SpecificationWorkitemMigratorProcess:

    def __init__(self, transaction, logger):
        self.transaction = transaction
        self.logger = logger

    def run(self):
        loop = SpecificationWorkitemMigrator(self.transaction, self.logger)
        DBLoopTuner(loop, 3, log=self.logger).run()
        self.logger.info("Done.")
