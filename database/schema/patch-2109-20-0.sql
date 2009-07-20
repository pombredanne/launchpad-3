-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

-- Provide per-project and per-team translation style guide URLs.

ALTER TABLE TranslationGroup ADD COLUMN translation_guide_url text;
ALTER TABLE Translator ADD COLUMN style_guide_url text;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 20, 0);

