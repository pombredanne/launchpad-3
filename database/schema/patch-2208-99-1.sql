-- Copyright 2010 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

ALTER TABLE TranslationImportQueueEntry
    RENAME COLUMN is_published TO from_upstream;

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 99, 1);
