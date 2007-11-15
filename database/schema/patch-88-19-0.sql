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
  whiteboard TEXT,
  date_created TIMESTAMP WITHOUT TIME ZONE NOT NULL
    DEFAULT timezone('UTC'::text, now()),
  UNIQUE(name)
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
/*
When there is no merge_robot set, the merge_control_status
must be set to Manual.  If a merge_robot is set, then the branch
merge_control_status can be set to Automatic which means that the
merge robot will start merging the branches.
*/
ALTER TABLE Branch
  ADD COLUMN merge_control_status INT NOT NULL DEFAULT 1;
-- 1: Manual, 2: Automatic

ALTER TABLE Branch
  ADD CONSTRAINT branch_robotic_control
  CHECK ((merge_robot IS NULL AND merge_control_status = 1) OR
         (merge_robot IS NOT NULL));


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
fields will be populated, otherwise they will stay null.
*/
ALTER TABLE BranchMergeProposal
  ADD COLUMN date_merge_started TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE BranchMergeProposal
  ADD COLUMN date_merge_finished TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE BranchMergeProposal
  ADD COLUMN merge_log_file INT REFERENCES LibraryFileAlias;


-- Need indexes for people merge
CREATE INDEX branchmergerobot__registrant__idx
  ON BranchMergeRobot(registrant);
CREATE INDEX branchmergerobot__owner__idx
  ON BranchMergeRobot(owner);

CREATE INDEX branch__reviewer__idx ON Branch(reviewer);

CREATE INDEX branchmergeproposal__reviewer__idx
  ON BranchMergeProposal(reviewer);
CREATE INDEX branchmergeproposal__queuer__idx
  ON BranchMergeProposal(queuer);
CREATE INDEX branchmergeproposal__merger__idx
  ON BranchMergeProposal(merger);


INSERT INTO LaunchpadDatabaseRevision VALUES (88, 19, 0);
