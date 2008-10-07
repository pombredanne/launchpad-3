SET client_min_messages=ERROR;

ALTER TABLE BugMessage ADD COLUMN remote_comment_id TEXT;

-- Allow remote_comment_id to be set only if it's an imported
-- comment, i.e.  bugwatch is not NULL.
ALTER TABLE BugMessage ADD CONSTRAINT imported_comment
    CHECK (remote_comment_id IS NULL OR bugwatch IS NOT NULL);

-- Make sure the same comment isn't imported twice. There can be
-- multiple comments having a NULL remote_comment_id associated with the
-- same bug watch.
ALTER TABLE BugMessage
    ADD CONSTRAINT bugmessage__bugwatch__remote_comment_id__key
    UNIQUE (bugwatch, remote_comment_id);

DROP INDEX bugmessage__bugwatch__idx; -- Now unnecessary

-- Fix some naming
ALTER TABLE BugMessage DROP CONSTRAINT "$1";
ALTER TABLE BugMessage ADD CONSTRAINT bugmessage__bug__fk
    FOREIGN KEY (bug) REFERENCES Bug;

DROP INDEX BugMessage_bug_idx; -- Unnecessary
ALTER TABLE BugMessage
    DROP CONSTRAINT bugmessage_bug_key,
    ADD CONSTRAINT bugmessage__bug__message__key UNIQUE (bug, message);

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 30, 0);
