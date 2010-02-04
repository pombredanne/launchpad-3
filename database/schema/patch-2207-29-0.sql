-- Copyright 2010 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE bug
    ADD COLUMN latest_patch_uploaded timestamp without time zone
        DEFAULT NULL;

CREATE INDEX bug__latest_patch_uploaded__idx
    ON bug(latest_patch_uploaded);

CREATE TRIGGER bug_latest_patch_uploaded_on_insert_update_t
AFTER INSERT OR UPDATE ON bugattachment
FOR EACH ROW EXECUTE PROCEDURE bug_update_latest_patch_uploaded_on_insert_update();

CREATE TRIGGER bug_latest_patch_uploaded_on_delete_t
AFTER DELETE ON bugattachment
FOR EACH ROW EXECUTE PROCEDURE bug_update_latest_patch_uploaded_on_delete();

CREATE INDEX bugattachment__bug__idx ON BugAttachment(bug);

SELECT DISTINCT ON (bugattachment.bug)
    bug_update_latest_patch_uploaded(bugattachment.bug)
    FROM bugattachment WHERE bugattachment.type=1;

INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 29, 0);
