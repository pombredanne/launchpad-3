-- Copyright 2010 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

DROP INDEX translationmessage__pofile__idx;

ALTER TABLE TranslationMessage
DROP CONSTRAINT translationmessage__pofile__fk;

ALTER TABLE TranslationMessage
DROP COLUMN pofile;

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 99, 0);

