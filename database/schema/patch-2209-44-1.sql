-- Copyright 2013 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE INDEX previewdiff__merge_proposal__idx
    ON previewdiff (merge_proposal);
ALTER TABLE previewdiff ALTER COLUMN merge_proposal SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 44, 1);
