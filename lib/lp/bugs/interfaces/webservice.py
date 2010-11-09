# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""All the interfaces that are exposed through the webservice."""

__all__ = [
    'BugNominationStatusError',
    'IBug',
    'InvalidBugTargetType',
    'InvalidDuplicateValue',
    'IBugActivity',
    'IBugAttachment',
    'IBugBranch',
    'IBugNomination',
    'IBugSubscription',
    'IBugTarget',
    'IBugTask',
    'IBugTracker',
    'IBugTrackerComponent',
    'IBugTrackerComponentGroup',
    'IBugTrackerSet',
    'IBugWatch',
    'ICve',
    'ICveSet',
    'IHasBugs',
    'IMaloneApplication',
    'IllegalRelatedBugTasksParams',
    'IllegalTarget',
    'NominationError',
    'NominationSeriesObsoleteError',
    'UserCannotEditBugTaskAssignee',
    'UserCannotEditBugTaskImportance',
    'UserCannotEditBugTaskMilestone',
    'UserCannotEditBugTaskStatus',
    ]

from lp.bugs.interfaces.bug import (
    IBug,
    InvalidBugTargetType,
    InvalidDuplicateValue,
    )
from lp.bugs.interfaces.bugactivity import IBugActivity
from lp.bugs.interfaces.bugattachment import IBugAttachment
from lp.bugs.interfaces.bugbranch import IBugBranch
from lp.bugs.interfaces.malone import IMaloneApplication
from lp.bugs.interfaces.bugnomination import (
    BugNominationStatusError,
    IBugNomination,
    NominationError,
    NominationSeriesObsoleteError,
    )
from lp.bugs.interfaces.bugsubscription import IBugSubscription
from lp.bugs.interfaces.bugtarget import (
    IBugTarget,
    IHasBugs,
    )
from lp.bugs.interfaces.bugtask import (
    IBugTask,
    IllegalRelatedBugTasksParams,
    IllegalTarget,
    UserCannotEditBugTaskAssignee,
    UserCannotEditBugTaskImportance,
    UserCannotEditBugTaskMilestone,
    UserCannotEditBugTaskStatus,
    )
from lp.bugs.interfaces.bugtracker import (
    IBugTracker,
    IBugTrackerComponent,
    IBugTrackerComponentGroup,
    IBugTrackerSet,
    )
from lp.bugs.interfaces.bugwatch import IBugWatch
from lp.bugs.interfaces.cve import (
    ICve,
    ICveSet,
    )
