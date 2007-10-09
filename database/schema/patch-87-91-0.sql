SET client_min_messages=ERROR;

/*

code_approver is the person (or team) who is allowed to transition merge
proposals that target this branch from NEEDS_CODE_APPROVAL to CODE_APPROVED. If
unset, the code approver is the owner of the branch.

landing_approver is used to indicate the person (or team) whose approval is
required to transition from QUEUED to RUNNING. If unset, no one's approval is
required. This can be used to handle release-critical or land-this-branch-now
use cases (see below).

*/

ALTER TABLE Branch
  ADD COLUMN code_approver INT REFERENCES Person;
ALTER TABLE Branch
  ADD COLUMN landing_approver INT REFERENCES Person;


ALTER TABLE BranchMergeProposal
  ADD COLUMN commit_message TEXT;

ALTER TABLE BranchMergeProposal
  ADD COLUMN status INT NOT NULL DEFAULT 1;
/*
  1: New
  2: Code Needs Approval
  3: Code Approved
  4: Queued
  5: Running
  6: Failed
  7: Merged
*/

/*
The date that the merge proposal enters the NEEDS_CODE_APPROVAL state. This is
stored so that we can determine how long a branch has been waiting for code
approval.
*/
ALTER TABLE BranchMergeProposal
  ADD COLUMN date_code_needs_approval TIMESTAMP WITHOUT TIME ZONE;

/*
The individual who said that the code in this branch is OK to land.
*/
ALTER TABLE BranchMergeProposal
  ADD COLUMN code_approver INT REFERENCES Person;

/*
The date when the code in this branch was approved for landing.
*/
ALTER TABLE BranchMergeProposal
  ADD COLUMN date_code_approved TIMESTAMP WITHOUT TIME ZONE;

/*
The Bazaar revision ID that was approved to land.
*/
ALTER TABLE BranchMergeProposal
  ADD COLUMN approved_revision_id TEXT;

/* The individual who submitted the branch to the merge queue. This is usually
the merge proposal registrant.  */

ALTER TABLE BranchMergeProposal
  ADD COLUMN submitter INT REFERENCES Person;
ALTER TABLE BranchMergeProposal
  ADD COLUMN date_submitted TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE BranchMergeProposal
  ADD COLUMN submitted_revision_id TEXT;

/*
Under normal circumstances, the landing_approver is not needed.
If the target branch has specified a landing_approver, then the
function that gets the next branch approved for landing will only
return the queued branches where the landing_approver is in the
landing approval team specified.  This allows a branch to be put
into "release-critical" mode, or to effectively pause the queue
to land a particular branch.
*/
ALTER TABLE BranchMergeProposal
  ADD COLUMN landing_approver INT REFERENCES Person;
ALTER TABLE BranchMergeProposal
  ADD COLUMN date_landing_approved TIMESTAMP WITHOUT TIME ZONE;


/*
The merger is the person who merged the branch.

If a robot is doing the landing, then the merger is the robot.
If a person is marking the merge proposal as merged or failed,
it defaults to the person marking the proposal, but the user
is able to override this.

If the branch scanner is updating the merge proposal then it
stays as NULL.
*/
ALTER TABLE BranchMergeProposal
  ADD COLUMN merger INT REFERENCES Person;
ALTER TABLE BranchMergeProposal
  ADD COLUMN merged_revision_id TEXT;

/*
If the merge proposal is being merged by a bot, then these
two fields will be populated, otherwise they will stay null.
*/
ALTER TABLE BranchMergeProposal
  ADD COLUMN date_merge_started TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE BranchMergeProposal
  ADD COLUMN log_file INT REFERENCES LibraryFileAlias;

/*
Moving to revision ids rather than solely revision numbers.
For all branch types other than REMOTE we can show the user
the revision number from a revision id, and if the branch
is a remote, then the user will be able to store a number
in the text file.

If being updated from the bzr command line (as we will want
to be able to do when the APIs are availalble) then bzrlib
has easy access to the revision ids.
*/
ALTER TABLE BranchMergeProposal
  DROP COLUMN merged_revno;
ALTER TABLE BranchMergeProposal
  DROP COLUMN merge_reporter;

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 91, 0);
