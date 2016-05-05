-- Copyright 2016 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

-- Add ID sort indexes.
CREATE INDEX gitrepository__distribution__spn__id__idx
    ON gitrepository(distribution, sourcepackagename, id)
    WHERE distribution IS NOT NULL;
CREATE INDEX gitrepository__owner__distribution__spn__id__idx
    ON gitrepository(owner, distribution, sourcepackagename, id)
    WHERE distribution IS NOT NULL;
CREATE INDEX gitrepository__project__id__idx
    ON gitrepository(project, id)
    WHERE project IS NOT NULL;
CREATE INDEX gitrepository__owner__project__id__idx
    ON gitrepository(owner, project, id)
    WHERE project IS NOT NULL;
CREATE INDEX gitrepository__owner__id__idx
    ON gitrepository(owner, id);

-- Replace owner/target_default indexes with unique and partial ones.
CREATE UNIQUE INDEX gitrepository__distribution__spn__target_default__key
    ON gitrepository(distribution, sourcepackagename)
    WHERE distribution IS NOT NULL AND target_default;
DROP INDEX gitrepository__distribution__spn__target_default__idx;
CREATE UNIQUE INDEX gitrepository__owner__distribution__spn__owner_default__key
    ON gitrepository(owner, distribution, sourcepackagename)
    WHERE distribution IS NOT NULL AND owner_default;
DROP INDEX gitrepository__owner__distribution__spn__owner_default__idx;

CREATE UNIQUE INDEX gitrepository__project__target_default__key
    ON gitrepository(project)
    WHERE project IS NOT NULL AND target_default;
DROP INDEX gitrepository__project__target_default__idx;
CREATE UNIQUE INDEX gitrepository__owner__project__owner_default__key
    ON gitrepository(owner, project)
    WHERE project IS NOT NULL AND owner_default;
DROP INDEX gitrepository__owner__project__owner_default__idx;


INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 77, 1);
