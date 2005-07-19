
SET client_min_messages=ERROR;

-- we are going to point to this tuple from BugTask, so we need to ensure
-- that it's UNIQUE. that's no problem since id will be unique already

ALTER TABLE BugWatch ADD CONSTRAINT bugwatch_bugtask_target UNIQUE (id, bug);

ALTER TABLE BugTask ADD COLUMN bugwatch integer NULL;
ALTER TABLE BugTask ADD CONSTRAINT bugtask_bugwatch_fk
    FOREIGN KEY (bugwatch, bug) REFERENCES BugWatch(id, bug);

-- clean up old constraint names
ALTER TABLE BugWatch DROP CONSTRAINT "$1";
ALTER TABLE BugWatch ADD CONSTRAINT bugwatch_bug_fk
    FOREIGN KEY (bug) REFERENCES bug(id);
ALTER TABLE BugWatch DROP CONSTRAINT "$2";
ALTER TABLE BugWatch ADD CONSTRAINT bugwatch_bugtracker_fk
    FOREIGN KEY (bugtracker) REFERENCES bugtracker(id);
ALTER TABLE BugWatch DROP CONSTRAINT "$3";
ALTER TABLE BugWatch ADD CONSTRAINT bugwatch_owner_fk
    FOREIGN KEY ("owner") REFERENCES person(id);

INSERT INTO LaunchpadDatabaseRevision VALUES (17, 25, 0);
