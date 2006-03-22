set client_min_messages=error;

CREATE TABLE BugBranch (
    id SERIAL NOT NULL,
    datecreated timestamp without time zone DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone) NOT NULL,
    bug INTEGER NOT NULL REFERENCES Bug(id),
    branch INTEGER NOT NULL REFERENCES Branch(id),
    fixed_in_revision INTEGER REFERENCES Revision(id),
    status INTEGER NOT NULL,
    whiteboard TEXT);

ALTER TABLE BugBranch ADD CONSTRAINT bug_branch_unique UNIQUE (bug, branch);

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 38, 0);
