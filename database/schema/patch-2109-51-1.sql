-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

create index translationmessage__pofile__idx on translationmessage(pofile);
create index translationmessage__potmsgset__language__idx
    on translationmessage(potmsgset,language);
create index pofiletranslator__pofile__idx on pofiletranslator(pofile);

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 51, 1);
