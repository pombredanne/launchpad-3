/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Animation for IBugTask:+subscribe LaunchpadForm.
 * Also used in "Edit subscription" advanced overlay.
 *
 * @namespace Y.lp.answers.question_spam
 * @requires  dom, node, lazr.effects
 */
YUI.add('lp.bugs.bug_spam', function(Y) {
var namespace = Y.namespace('lp.bugs.bug_spam');

var hidden_class = "adminHiddenComment";
var spam_text = "Mark as spam";
var not_spam_text = "Mark as not spam";

function update_comment(link, comment) {
    var text = link.get('text').trim();
    if (text == spam_text) {
        comment.removeClass(hidden_class);
        link.set('text', not_spam_text);
    } else {
        comment.addClass(hidden_class);
        link.set('text', spam_text);
    }
}

function set_visibility(parameters, callbacks) {
    var bug = LP.cache.bug;
    var lp_client = new Y.lp.client.Launchpad();
    var config = {
        on: {
            success: callbacks.success,
            failure: callbacks.failure
            },
        parameters: parameters
        }
    lp_client.named_post(
        bug.self_link, 'setCommentVisibility', config);
}

function toggle_spam_setting(link) {
    var comment = link.get('parentNode').get('parentNode');
    var visible = comment.hasClass('adminHiddenComment');
    var comment_number = parseInt(link.get('id').replace('mark-spam-', ''));
    parameters = {
        visible: visible,
        comment_number: comment_number
        };
    set_visibility(parameters, {
        // We use red flash on failure so admins no it didn't work.
        // There's no green flash on success, b/c the change in bg
        // color provides an immediate visual cue.
        success: function () { 
            update_comment(link, comment);
            comment.toggleClass(hidden_class);
            },
        failure: function () {
            Y.lazr.anim.red_flash({node:comment});
            }
        });
}
namespace.toggle_spam_setting = toggle_spam_setting;

function setup_spam_links() {
  Y.on('click', function(e) {
      e.halt();
      namespace.toggle_spam_setting(this);
  }, '.mark-spam');
}
namespace.setup_spam_links = setup_spam_links
}, "0.1", {"requires": ["dom", "node", "lazr.anim", "lp.client"]});
