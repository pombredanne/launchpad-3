SET client_min_messages=ERROR;

-- Schema modifications for SupportTrackerWorkflowSpec implementation

-- answer is a foreign key to the ticket message that answered the request.
ALTER TABLE ticket ADD COLUMN answer integer;
ALTER TABLE ticket ADD CONSTRAINT ticket_answer_fk
  FOREIGN KEY (answer) REFERENCES ticketmessage(id);

-- action is a value from TicketAction enum
ALTER TABLE ticketmessage ADD COLUMN action integer;
-- newstatus is a value from TicketStatus enum
ALTER TABLE ticketmessage ADD COLUMN newstatus integer;

-- Set action of old TicketMessages to COMMENT and newstatus to OPEN
UPDATE ticketmessage SET action = 30, newstatus = 10;

-- Set the NOT NULL constraint after the old data was migated
ALTER TABLE ticketmessage ALTER COLUMN action SET NOT NULL;
 ALTER TABLE ticketmessage ALTER COLUMN newstatus SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 99, 0);
