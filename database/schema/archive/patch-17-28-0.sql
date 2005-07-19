SET client_min_messages=ERROR;

-- remove the UNIQUE requirement on Message.rfc822msgid
ALTER TABLE Message DROP CONSTRAINT bugmessage_rfc822msgid_key;

-- but we do still want an index on rfc822msgid
CREATE INDEX message_rfc822msgid_idx ON Message(rfc822msgid);

-- also remove the NOT NULL requirement on the message title
ALTER TABLE Message ALTER COLUMN title DROP NOT NULL;

-- and rename that to subject
ALTER TABLE Message RENAME COLUMN title TO subject;

-- now, let's get rid of the distribution column
-- ALTER TABLE Message DROP COLUMN distribution;

-- some straightforward cleanups
ALTER TABLE Message DROP CONSTRAINT "$4";
ALTER TABLE Message ADD CONSTRAINT message_distribution_fk FOREIGN KEY
(distribution) REFERENCES Distribution(id);

ALTER TABLE Message DROP CONSTRAINT "$2";
ALTER TABLE Message ADD CONSTRAINT message_owner_fk FOREIGN KEY (owner)
REFERENCES Person(id);

ALTER TABLE BugTracker DROP CONSTRAINT "$1";
ALTER TABLE BugTracker ADD CONSTRAINT bugtracker_bugtrackerttype_fk
    FOREIGN KEY (bugtrackertype) REFERENCES bugtrackertype(id);

ALTER TABLE BugTracker DROP CONSTRAINT "$2";
ALTER TABLE BugTracker ADD CONSTRAINT bugtracker_owner_fk
    FOREIGN KEY ("owner") REFERENCES person(id);

ALTER TABLE BugTrackerType DROP CONSTRAINT "$1";
ALTER TABLE BugTrackerType ADD CONSTRAINT bugtrackertype_owner_fk
    FOREIGN KEY ("owner") REFERENCES person(id);

INSERT INTO LaunchpadDatabaseRevision VALUES (17, 28, 0);
