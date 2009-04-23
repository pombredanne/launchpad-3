SET client_min_messages=ERROR;

-- The branch should not be included in the uniqueness constraint. We want
-- only one of these per sourcepackage, pocket.

ALTER TABLE ONLY seriessourcepackagebranch
  DROP CONSTRAINT branchsourcepackageseries__ds__spn__pocket__branch__key,
  ADD CONSTRAINT seriessourcepackagebranch__ds__spn__pocket__key
  UNIQUE (distroseries, sourcepackagename, pocket);

INSERT INTO LaunchpadDatabaseRevision VALUES (2109, 51, 0);
