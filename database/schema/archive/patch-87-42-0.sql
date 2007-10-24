SET client_min_messages=ERROR;

CREATE TABLE BranchMergeProposal
(
   id SERIAL PRIMARY KEY,
   registrant INT REFERENCES Person NOT NULL,
   source_branch INT REFERENCES Branch NOT NULL,
   target_branch INT REFERENCES Branch NOT NULL,
   dependent_branch  INT REFERENCES Branch,
   whiteboard TEXT,
   date_merged TIMESTAMP WITHOUT TIME ZONE,
   merged_revno INT,
   merge_reporter INT REFERENCES Person,
   date_created TIMESTAMP WITHOUT TIME ZONE NOT NULL
       DEFAULT timezone('UTC'::text, now()),
   CONSTRAINT different_branches CHECK
       (source_branch != target_branch AND
        dependent_branch != source_branch AND
        dependent_branch != target_branch),
   CONSTRAINT positive_revno CHECK ((merged_revno is NULL) or (merged_revno > 0)),
   UNIQUE(source_branch, target_branch, date_merged)
);

CREATE INDEX branchmergeproposal__source_branch__idx
   ON BranchMergeProposal USING btree(source_branch);
CREATE INDEX branchmergeproposal__target_branch__idx
   ON BranchMergeProposal USING btree(target_branch);
CREATE INDEX branchmergeproposal__dependent_branch__idx
   ON BranchMergeProposal USING btree(dependent_branch);
CREATE INDEX branchmergeproposal__merge_reporter__idx
   ON BranchMergeProposal (merge_reporter) WHERE merge_reporter IS NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (87, 42, 0);

