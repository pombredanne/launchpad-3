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

SELECT bug_update_latest_patch_uploaded(bug.id)
    FROM bug WHERE EXISTS (
        SELECT bugattachment.id FROM bugattachment, bug
            WHERE bugattachment.bug=bug.id AND bugattachment.type=1);

INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 99, 0);
