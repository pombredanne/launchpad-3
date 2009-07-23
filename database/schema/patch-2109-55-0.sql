-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages = ERROR;

alter table tm__potmsgset__potemplate__language__no_variant__diverged__current__key owner to postgres;
alter table tm__potmsgset__potemplate__language__no_variant__diverged__imported__key owner to postgres;
DROP INDEX tm__old__diverged__current__key;
DROP INDEX tm__old__diverged__imported__key;

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 55, 0);

