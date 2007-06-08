SET client_min_messages=ERROR;

-- Rename tables.

ALTER TABLE Ticket RENAME TO Question;
ALTER TABLE TicketBug RENAME TO QuestionBug;
ALTER TABLE TicketMessage RENAME TO QuestionMessage;
ALTER TABLE TicketReopening RENAME TO QuestionReopening;
ALTER TABLE TicketSubscription RENAME TO QuestionSubscription;

ALTER TABLE SupportContact RENAME TO AnswerContact;

-- Update the fticache table so the full text indexes don't get rebuilt
UPDATE FtiCache SET tablename='question' WHERE tablename='ticket';

-- Rename sequences.

ALTER TABLE ticket_id_seq RENAME TO question_id_seq;
ALTER TABLE ticketbug_id_seq RENAME TO questionbug_id_seq;
ALTER TABLE ticketmessage_id_seq RENAME TO questionmessage_id_seq;
ALTER TABLE ticketreopening_id_seq RENAME TO questionreopening_id_seq;
ALTER TABLE ticketsubscription_id_seq RENAME TO questionsubscription_id_seq;

ALTER TABLE supportcontact_id_seq RENAME TO answercontact_id_seq;

-- And ensure SERIAL columns use the renamed sequences
-- Yay - PostgreSQL 8.2 now does this automatically for us.

-- Rename indexes.

ALTER INDEX ticket_answerer_idx RENAME TO question__answerer__idx;
ALTER INDEX ticket_assignee_idx RENAME TO question__assignee__idx;
ALTER INDEX ticket_distribution_sourcepackagename_idx
    RENAME TO question__distribution__sourcepackagename__idx;
ALTER INDEX ticket_distro_datecreated_idx
    RENAME TO question__distro__datecreated__idx;
ALTER INDEX ticket_fti RENAME TO question__fti;
ALTER INDEX ticket_owner_idx RENAME TO question__owner__idx;
ALTER INDEX ticket_pkey RENAME TO question_pkey;
ALTER INDEX ticket_product_datecreated_idx
    RENAME TO question__product__datecreated__idx;
ALTER INDEX ticket_product_idx RENAME TO question__product__idx;
ALTER INDEX ticketbug_bug_ticket_uniq
    RENAME TO questionbug__bug__question__uniq;
ALTER INDEX ticketbug_pkey RENAME TO questionbug_pkey;
ALTER INDEX ticketbug_ticket_idx RENAME TO questionbug__question__idx;
ALTER INDEX ticketmessage_message_ticket_uniq
    RENAME TO questionmessage__message__question__uniq;
ALTER INDEX ticketmessage_pkey RENAME TO questionmessage_pkey;
ALTER INDEX ticketmessage_ticket_idx RENAME TO questionmessage__question__idx;
ALTER INDEX ticketreopening_answerer_idx
    RENAME TO questionreopening__answerer__idx;
ALTER INDEX ticketreopening_datecreated_idx
    RENAME TO questionreopening__datecreated__idx;
ALTER INDEX ticketreopening_pkey RENAME TO questionreopening_pkey;
ALTER INDEX ticketreopening_reopener_idx
    RENAME TO questionreopening__reopener__idx ;
ALTER INDEX ticketreopening_ticket_idx
    RENAME TO questionreopening__question__idx;
ALTER INDEX ticketsubscription_pkey RENAME TO questionsubscription_pkey;
ALTER INDEX ticketsubscription_subscriber_idx
    RENAME TO questionsubscription__subscriber__idx;
ALTER INDEX ticketsubscription_ticket_person_uniq
    RENAME TO questionsubscription__question__person__uniq;

ALTER INDEX supportcontact__distribution__person__key
    RENAME TO answercontact__distribution__person__key;
ALTER INDEX  supportcontact__distribution__sourcepackagename__person__key
    RENAME TO answercontact__distribution__sourcepackagename__person__key;
ALTER INDEX  supportcontact__person__idx
    RENAME TO answercontact__person__idx;
ALTER INDEX supportcontact__product__person__key
    RENAME TO answercontact__product__person__key;
ALTER INDEX  supportcontact_pkey
    RENAME TO answercontact_pkey;

-- Rename columns.

ALTER TABLE QuestionBug RENAME COLUMN ticket TO question;
ALTER TABLE QuestionMessage RENAME COLUMN ticket TO question;
ALTER TABLE QuestionReopening RENAME COLUMN ticket TO question;
ALTER TABLE QuestionSubscription RENAME COLUMN ticket TO question;

-- Rename constraints on Question.

ALTER TABLE Question
    DROP CONSTRAINT ticket__answer__fk;
ALTER TABLE Question
    ADD CONSTRAINT question__answer__fk
        FOREIGN KEY (answer) REFERENCES questionmessage(id);

ALTER TABLE Question
    DROP CONSTRAINT ticket_answerer_fk;
ALTER TABLE Question
    ADD CONSTRAINT question__answerer__fk
        FOREIGN KEY (answerer) REFERENCES person(id);

ALTER TABLE Question
    DROP CONSTRAINT ticket_assignee_fk;
ALTER TABLE Question
    ADD CONSTRAINT question__assignee__fk
        FOREIGN KEY (assignee) REFERENCES person(id);

ALTER TABLE Question
    DROP CONSTRAINT ticket_distribution_fk;
ALTER TABLE Question
    ADD CONSTRAINT question__distribution__fk
        FOREIGN KEY (distribution) REFERENCES distribution(id);

ALTER TABLE Question
    DROP CONSTRAINT ticket_language_fkey;
ALTER TABLE Question
    ADD CONSTRAINT question__language__fkey
    FOREIGN KEY ("language") REFERENCES "language"(id);

ALTER TABLE Question
    DROP CONSTRAINT ticket_owner_fk;
ALTER TABLE Question
    ADD CONSTRAINT question__owner__fk
        FOREIGN KEY ("owner") REFERENCES person(id);

ALTER TABLE Question
    DROP CONSTRAINT ticket_product_fk;
ALTER TABLE Question
    ADD CONSTRAINT question__product__fk
        FOREIGN KEY (product) REFERENCES product(id);

ALTER TABLE Question
    DROP CONSTRAINT ticket_sourcepackagename_fk;
ALTER TABLE Question
    ADD CONSTRAINT question__sourcepackagename__fk
    FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);

-- Rename constraints on QuestionBug.

ALTER TABLE QuestionBug
    DROP CONSTRAINT ticketbug_bug_fk;
ALTER TABLE QuestionBug
    ADD CONSTRAINT questionbug__bug__fk
         FOREIGN KEY (bug) REFERENCES bug(id);

ALTER TABLE QuestionBug
    DROP CONSTRAINT ticketbug_ticket_fk;
ALTER TABLE QuestionBug
    ADD CONSTRAINT questionbug__question__fk
         FOREIGN KEY (question) REFERENCES question(id);

-- Rename constraints on QuestionMessage.
ALTER TABLE QuestionMessage
    DROP CONSTRAINT ticketmessage_message_fk;
ALTER TABLE QuestionMessage
    ADD CONSTRAINT questionmessage__message__fk
        FOREIGN KEY (message) REFERENCES message(id);

ALTER TABLE QuestionMessage
    DROP CONSTRAINT ticketmessage_ticket_fk;
ALTER TABLE QuestionMessage
    ADD CONSTRAINT questionmessage__question__fk
        FOREIGN KEY (question) REFERENCES question(id);

-- Rename constraints on QuestionReopening
ALTER TABLE QuestionReopening
    DROP CONSTRAINT ticketreopening_answerer_fk;
ALTER TABLE QuestionReopening
    ADD CONSTRAINT questionreopening__answerer__fk
        FOREIGN KEY (answerer) REFERENCES person(id);

ALTER TABLE QuestionReopening
    DROP CONSTRAINT ticketreopening_reopener_fk;
ALTER TABLE QuestionReopening
    ADD CONSTRAINT questionreopening__reopener__fk
        FOREIGN KEY (reopener) REFERENCES person(id);

ALTER TABLE QuestionReopening
    DROP CONSTRAINT ticketreopening_ticket_fk;
ALTER TABLE QuestionReopening
    ADD CONSTRAINT questionreopening__question__fk
        FOREIGN KEY (question) REFERENCES question(id);

-- Rename constraints on QuestionSubscription
ALTER TABLE QuestionSubscription
    DROP CONSTRAINT ticketsubscription_person_fk;
ALTER TABLE QuestionSubscription
    ADD CONSTRAINT questionsubscription__person__fk
        FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE QuestionSubscription
    DROP CONSTRAINT ticketsubscription_ticket_fk;
ALTER TABLE QuestionSubscription
    ADD CONSTRAINT questionsubscription__question__fk
        FOREIGN KEY (question) REFERENCES question(id);

-- Rename constraints on AnswerContact

ALTER TABLE AnswerContact
    DROP CONSTRAINT supportcontact_distribution_fkey;
ALTER TABLE AnswerContact
    ADD CONSTRAINT answercontact__distribution__fkey
        FOREIGN KEY (distribution) REFERENCES distribution(id);

ALTER TABLE AnswerContact
    DROP CONSTRAINT supportcontact_person_fkey;
ALTER TABLE AnswerContact
    ADD CONSTRAINT answercontact__person__fkey
        FOREIGN KEY (person) REFERENCES person(id);

ALTER TABLE AnswerContact
    DROP CONSTRAINT supportcontact_product_fkey;
ALTER TABLE AnswerContact
    ADD CONSTRAINT answercontact__product__fkey
        FOREIGN KEY (product) REFERENCES product(id);

ALTER TABLE AnswerContact
    DROP CONSTRAINT supportcontact_sourcepackagename_fkey;
ALTER TABLE AnswerContact
    ADD CONSTRAINT answercontact__sourcepackagename__fkey
        FOREIGN KEY (sourcepackagename) REFERENCES sourcepackagename(id);

-- Rename the janitor.

UPDATE Person SET name = 'answer-tracker-janitor',
    displayname = 'Launchpad Answers Janitor'
    WHERE name = 'support-tracker-janitor';


-- Rename KarmaAction.

UPDATE KarmaAction SET
    name = 'questioncommentadded',
    title = 'Comment made on a question',
    summary = 'User made a comment on a question in the Answer Tracker'
    WHERE name = 'ticketcommentadded';

UPDATE KarmaAction SET
    name = 'questiontitlechanged',
    title = 'Question title changed',
    summary = 'User changed the title of a question in the Answer Tracker'
    WHERE name = 'tickettitlechanged';

UPDATE KarmaAction SET
    name = 'questiondescriptionchanged',
    title = 'Question description changed',
    summary = 'User changed the description of a question in the Answer Tracker'
    WHERE name = 'ticketdescriptionchanged';

UPDATE KarmaAction SET
    name = 'questionlinkedtobug',
    title = 'Question linked to a bug',
    summary = 'User linked a question in the Answer Tracker to a bug.'
    WHERE name = 'ticketlinkedtobug';

UPDATE KarmaAction SET
    name = 'questionansweraccepted',
    title = 'Question owner accepted answer',
    summary = 'User accepted one of the message as the actual answer to his question.'
    WHERE name = 'ticketansweraccepted';

UPDATE KarmaAction SET
    name = 'questionanswered',
    title = 'Answered question',
    summary = 'User posed a message that was accepted by the question owner as answering the question.'
    WHERE name = 'ticketanswered';

UPDATE KarmaAction SET
    name = 'questionrequestedinfo',
    title = 'Requested for information on a question',
    summary = 'User post a message requesting for more information from a question owner in the Answer Tracker.'
    WHERE name = 'ticketrequestedinfo';

UPDATE KarmaAction SET
    name = 'questiongaveinfo',
    title = 'Gave more information on a question',
    summary = 'User replied to a message asking for more information on a question in the Answer Tracker.'
    WHERE name = 'ticketgaveinfo';

UPDATE KarmaAction SET
    name = 'questiongaveanswer',
    title = 'Gave answer on a question',
    summary = 'User post a message containing an answer to a question in the Answer Tracker. This is distinct from having that message confirmed as solving the problem.'
    WHERE name = 'ticketgaveanswer';

UPDATE KarmaAction SET
    name = 'questionrejected',
    title = 'Rejected question',
    summary = 'User rejected a question in the Answer Tracker.'
    WHERE name = 'ticketrejected';

UPDATE KarmaAction SET
    name = 'questionownersolved',
    title = 'Solved own question',
    summary = 'User post a message explaining how he solved his own problem.'
    WHERE name = 'ticketownersolved';

UPDATE KarmaAction SET
    name = 'questionreopened',
    title = 'Reopened question',
    summary = 'User posed a message to reopen his question in the Answer Tracker.'
    WHERE name = 'ticketreopened';

UPDATE KarmaAction SET
    name = 'questionasked',
    title = 'Asked question',
    summary = 'User asked a question in the Answer Tracker.'
    WHERE name = 'ticketcreated';

-- Rename category.

UPDATE KarmaCategory SET
    name = 'answers',
    title = 'Answer Tracker',
    summary = 'This is the category for all karma associated with helping with users questions in the Launchpad Answer Tracker. Help solve users problems to earn this karma.'
    WHERE name = 'support';

INSERT INTO LaunchpadDatabaseRevision VALUES (79, 15, 0);

