-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE BugAffectsPerson
ADD COLUMN affected BOOLEAN DEFAULT TRUE NOT NULL;

UPDATE BugAffectsPerson
SET affected = TRUE;

ALTER TABLE Bug
ADD COLUMN users_unaffected_count INTEGER DEFAULT 0;

DROP TRIGGER set_bug_users_affected_count_t ON BugAffectsPerson;

CREATE TRIGGER set_bug_users_affected_count_t
    AFTER INSERT OR DELETE OR UPDATE ON BugAffectsPerson
    FOR EACH ROW
    EXECUTE PROCEDURE set_bug_users_affected_count();

CREATE INDEX bug__users_unaffected_count__idx ON Bug(users_unaffected_count);

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 4, 0);
