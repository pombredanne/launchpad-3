-- Copyright 2010 Canonical Ltd. This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

-- Update the flag restricted of LibraryFileAlias records which belong
-- to bug attachments of private bugs.

SET client_min_messages=ERROR;

UPDATE LibraryFileAlias SET restricted=true
    WHERE id IN (
        SELECT libraryfile from BugAttachment, Bug
            WHERE BugAttachment.bug = Bug.id AND Bug.private);

INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 99, 0);
