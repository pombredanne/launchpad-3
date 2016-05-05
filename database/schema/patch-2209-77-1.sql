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

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 77, 1);
