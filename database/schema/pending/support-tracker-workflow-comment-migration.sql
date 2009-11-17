-- Copyright 2009 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

BEGIN;
-- Mark all comments from somebody else than the ticket submitter
-- as an answer. Otherwise, no answers posted before the new
-- support tracker workfler is in place can be confirmed.
UPDATE TicketMessage SET ACTION = 35
    WHERE id IN (
    SELECT tm.id FROM TicketMessage tm
                 JOIN Message m ON (tm.message = m.id)
                 JOIN Ticket t ON (t.id = tm.ticket)
                WHERE t.owner != m.owner);

-- Move all Open tickets that received an answer to the 'Answered' state.
UPDATE Ticket SET status = 18
    WHERE status = 10 AND id IN (
    SELECT DISTINCT ticket FROM TicketMessage WHERE action = 35);
COMMIT;

