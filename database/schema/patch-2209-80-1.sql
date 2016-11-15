-- Copyright 2016 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE UNIQUE INDEX codeimport__url__branch__idx
    ON CodeImport(url) WHERE branch IS NOT NULL;
CREATE UNIQUE INDEX codeimport__url__git_repository__idx
    ON CodeImport(url) WHERE git_repository IS NOT NULL;
DROP INDEX codeimport__url__idx;

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 80, 1);
