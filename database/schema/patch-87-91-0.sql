SET client_min_messages=ERROR;

/*
In order to be able to have a single landing bot land branches
for multiple target branches (that may be on different projects)
we need to have a separate queue entity.

The owner of the robot is the person or team that is able to manipulate
the robot and manage the queue positions for that robot.
*/
CREATE TABLE BranchMergeRobot
(
  id serial NOT NULL PRIMARY KEY,
  registrant INT REFERENCES Person NOT NULL,
  owner INT REFERENCES Person NOT NULL,
  name TEXT NOT NULL,
  status INT NOT NULL, -- 1: Manual, 2: Automatic
  whiteboard TEXT,
  date_created TIMESTAMP WITHOUT TIME ZONE NOT NULL
    DEFAULT timezone('UTC'::text, now()),
  UNIQUE(owner, name)
);

/*
The review team are able to transition merge proposals targetted
a the branch through the CODE_APPROVED stage.
*/
ALTER TABLE Branch
  ADD COLUMN reviewer INT REFERENCES Person;
/*
A null queue means that there is no landing bot, and the owner
of the branch can control the queue positions.
*/
ALTER TABLE Branch
  ADD COLUMN merge_robot INT REFERENCES BranchMergeRobot;


ALTER TABLE BranchMergeProposal
  ADD COLUMN commit_message TEXT;
ALTER TABLE BranchMergeProposal
  ADD COLUMN queue_position INT;
ALTER TABLE BranchMergeProposal
  ADD COLUMN queue_status INT NOT NULL DEFAULT 1;

/*
  1: Work in progress
  2: Review requested
  3: Reviewed
  4: Queued
  5: Merge in progress
  6: Failed
  7: Merged
*/

/*
The date that the merge proposal enters the REVIEW_REQUESTED state. This is
stored so that we can determine how long a branch has been waiting for code
approval.
*/
ALTER TABLE BranchMergeProposal
  ADD COLUMN date_review_requested TIMESTAMP WITHOUT TIME ZONE;

/*
The individual who said that the code in this branch is OK to land.
*/
ALTER TABLE BranchMergeProposal
  ADD COLUMN reviewer INT REFERENCES Person;
ALTER TABLE BranchMergeProposal
  ADD COLUMN date_reviewed TIMESTAMP WITHOUT TIME ZONE;
/*
The Bazaar revision ID that was approved to land.
*/
ALTER TABLE BranchMergeProposal
  ADD COLUMN reviewed_revision_id TEXT;

/*
The individual who submitted the branch to the merge queue. This is usually
the merge proposal registrant.
*/
ALTER TABLE BranchMergeProposal
  ADD COLUMN queuer INT REFERENCES Person;
ALTER TABLE BranchMergeProposal
  ADD COLUMN date_queued TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE BranchMergeProposal
  ADD COLUMN queued_revision_id TEXT;

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
  ADD COLUMN merge_log_file INT REFERENCES LibraryFileAlias;

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
