
ALTER TABLE BugAttachment DROP COLUMN "datedeactivated";
/* A descriptive title of the attachment. */
ALTER TABLE BugAttachment RENAME description TO title;
/* The bug that the attachment it attached to. */
ALTER TABLE BugAttachment ADD COLUMN bug INTEGER;
ALTER TABLE BugAttachment ALTER COLUMN bug SET NOT NULL;
ALTER TABLE BugAttachment ADD CONSTRAINT "bugattachment_bug_fk" FOREIGN KEY (bug) REFERENCES bug(id);
/* The type of the attachment, for example Patch or Unspecified. */
ALTER TABLE BugAttachment ADD COLUMN "type" INTEGER;
ALTER TABLE BugAttachment ALTER COLUMN "type" SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (25, 09, 0);

