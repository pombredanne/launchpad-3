SET client_min_messages=ERROR;

ALTER TABLE BugMessage ADD COLUMN remote_comment_id TEXT;

-- Allow remote_comment_id_id to be set only if it's an imported
-- comment, i.e.  bugwatch is not NULL.
ALTER TABLE BugMessage ADD CONSTRAINT imported_comment
    CHECK (remote_comment_id IS NULL OR bugwatch IS NOT NULL);

-- Make sure the same comment isn't imported twice. There can be
-- multiple comments having a NULL remote_comment_id associated with the
-- same bug watch.
ALTER TABLE BugMessage ADD CONSTRAINT imported_comment_key
    UNIQUE (remote_comment_id, bugwatch);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 99, 0);
