/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * @namespace Y.lp.comments.hide
 * @requires dom, node, lp.anim, lp.client
 */
YUI.add('lp.comments.hide', function(Y) {
var namespace = Y.namespace('lp.comments.hide');

var hidden_class = "adminHiddenComment";
var hide_text = "Hide comment";
var unhide_text = "Unhide comment";

function update_comment(link, comment) {
    var text = link.get('text').trim();
    if (text === hide_text) {
        comment.removeClass(hidden_class);
        link.set('text', unhide_text);
    } else {
        comment.addClass(hidden_class);
        link.set('text', hide_text);
    }
}

function set_visibility(parameters, callbacks) {
    // comment_context must be setup on pages using this js, and is the
    // context for a comment (e.g. bug).
    var comment_context = LP.cache.comment_context;
    var lp_client = new Y.lp.client.Launchpad();
    var config = {
        on: {
            success: callbacks.success,
            failure: callbacks.failure
            },
        parameters: parameters
        }
    lp_client.named_post(
        comment_context.self_link, 'setCommentVisibility', config);
}

function toggle_hidden(link) {
    var comment = link.get('parentNode').get('parentNode');
    var visible = comment.hasClass('adminHiddenComment');
    var comment_number = parseInt(
            link.get('id').replace('mark-spam-', ''), 10);
    parameters = {
        visible: visible,
        comment_number: comment_number
        };
    set_visibility(parameters, {
        // We use red flash on failure so admins know it didn't work.
        // There's no green flash on success, b/c the change in bg
        // color provides an immediate visual cue.
        success: function () {
            update_comment(link, comment);
            comment.toggleClass(hidden_class);
            },
        failure: function () {
            Y.lp.anim.red_flash({node:comment});
            }
        });
}
namespace.toggle_hidden = toggle_hidden;

function setup_hide_controls() {
  Y.on('click', function(e) {
      e.halt();
      namespace.toggle_hidden(this);
  }, '.mark-spam');
}
namespace.setup_hide_controls = setup_hide_controls;
}, "0.1", {"requires": ["dom", "node", "lp.anim", "lp.client"]});
