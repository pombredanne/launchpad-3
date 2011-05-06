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

var hidden_class = "adminHiddenComment";
var spam_text = "Mark as spam";
var not_spam_text = "Mark as not spam";

function update_text(link) {
    var text = link.get('text').trim();
    if (text == spam_text) {
        link.set('text', not_spam_text);
    } else {
        link.set('text', spam_text);
    }
}

function set_visibility(parameters, callback) {
    var question = LP.cache.context
    var lp_client = new Y.lp.client.Launchpad()
    var config = {
        on: {
            success: callback,
            failure: function () {}
            },
        parameters: parameters
        }
    lp_client.named_post(
        question.self_link, 'setCommentVisibility', config)
}

function toggle_spam_setting(link) {
    var comment = link.get('parentNode').get('parentNode');
    var visible = comment.hasClass('adminHiddenComment');
    var comment_number = parseInt(link.get('id').replace('mark-spam-', ''));
    comment_number = comment_number - 1;
    parameters = {
        visible: visible,
        comment_number: comment_number
        };
    set_visibility(parameters, function () { 
        update_text(link);
        comment.toggleClass(hidden_class);
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
}, "0.1", {"requires": ["dom", "node", "lp.client"]});
