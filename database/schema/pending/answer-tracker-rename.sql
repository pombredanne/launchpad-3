BEGIN;

-- Rename the janitor.

UPDATE Person SET name = 'answer-tracker-janitor',
    displayname = 'Launchpad Answer Tracker Janitor'
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

COMMIT;

