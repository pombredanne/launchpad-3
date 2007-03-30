SET client_min_messages=ERROR;

ALTER TABLE Person RENAME COLUMN emblem TO icon;
ALTER TABLE Person RENAME COLUMN gotchi_heading TO logo;
ALTER TABLE Person RENAME COLUMN gotchi TO mugshot;

ALTER TABLE Sprint RENAME COLUMN emblem TO icon;
ALTER TABLE Sprint RENAME COLUMN gotchi_heading TO logo;
ALTER TABLE Sprint RENAME COLUMN gotchi TO mugshot;

ALTER TABLE Product RENAME COLUMN emblem TO icon;
ALTER TABLE Product RENAME COLUMN gotchi_heading TO logo;
ALTER TABLE Product RENAME COLUMN gotchi TO mugshot;

ALTER TABLE Project RENAME COLUMN emblem TO icon;
ALTER TABLE Project RENAME COLUMN gotchi_heading TO logo;
ALTER TABLE Project RENAME COLUMN gotchi TO mugshot;

ALTER TABLE Distribution RENAME COLUMN emblem TO icon;
ALTER TABLE Distribution RENAME COLUMN gotchi_heading TO logo;
ALTER TABLE Distribution RENAME COLUMN gotchi TO mugshot;

INSERT INTO LaunchpadDatabaseRevision VALUES (79, 93, 0);
