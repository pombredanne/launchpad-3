/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Animation for IBugTask:+subscribe LaunchpadForm.
 * Also used in "Edit subscription" advanced overlay.
 *
 * @namespace Y.lp.answers.question_spam
 * @requires  dom, node, lazr.effects
 */

YUI.add('lp.answers.question_spam', function(Y) {
var namespace = Y.namespace('lp.answers.question_spam');

var hidden_class = "adminHiddenClass";
var spam_text = "Mark as spam";
var not_spam_text = "Mark as not spam";

function toggle_spam_setting(e) {
    alert(e);
}

namespace.toggle_spam_setting = toggle_spam_setting;

function setup_spam_links() {
    Y.all('.mark-spam').on('click', function(e) {
        namespace.toggle_spam_setting(e);
    });
}
}, "0.1", {"requires": ["dom", "event-custom", "node", "lazr.effects"]});
