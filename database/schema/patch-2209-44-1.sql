-- Copyright 2013 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE INDEX previewdiff__branch_merge_proposal__date_created__idx
    ON previewdiff (branch_merge_proposal, date_created);
ALTER TABLE previewdiff ALTER COLUMN branch_merge_proposal SET NOT NULL,
                        ALTER COLUMN date_created SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 44, 1);
