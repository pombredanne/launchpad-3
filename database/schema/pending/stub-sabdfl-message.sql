/*
  Make BugMessages able to apply to multiple bugs at once. This is something we
  considered and discarded earlier, but syncing to DebBugs requires it since
  that system explicitly allows and encourages one message to be sent to
  multiple bugs.

  This update is still in design and discussion.
*/

-- first rename the old BugMessage column to Message
ALTER TABLE BugMessage RENAME TO Message;
ALTER TABLE BugMessage_id_seq RENAME TO message_id_seq;
ALTER TABLE Message ALTER COLUMN id SET DEFAULT nextval('message_id_seq');
ALTER TABLE BugMessage_pkey RENAME TO message_pkey;
ALTER TABLE BugMessage_rfc822msgid_key RENAME TO message_rfc822msgid_key;

-- now create the new table to link bugs and messages
CREATE TABLE BugMessage (
  id      serial  NOT NULL PRIMARY KEY,
  bug     integer NOT NULL REFERENCES Bug,
  message integer NOT NULL REFERENCES Message,
  UNIQUE (bug, message)
  );

-- now copy data from the old to the new
INSERT INTO BugMessage (bug, message) SELECT bug, id FROM Message;

-- and get rid of the "bug" column in the old one, because
-- we have the relation table now
ALTER TABLE Message DROP COLUMN Bug;

-- and add comments
COMMENT ON TABLE BugMessage IS 'This table maps a message to a bug. In other words, it shows that a particular message is associated with a particular bug.';
