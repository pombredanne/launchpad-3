YUI.add('lp.comment', function(Y) {
var lp_client = new LP.client.Launchpad();
/*var lp_bug_entry = new LP.client.Entry(
            lp_client, bug_repr, bug_repr.self_link);*/


/*
 * Set up and handle submitting a comment inline.
 *
 * @method setup_inline_commenting
 */
function setup_inline_commenting() {
    var submit_button = Y.get('[id="field.actions.save"]');
    var progress_message = Y.Node.create(
        '<span class="update-in-progress-message">Saving...</span>');
    var comment_input = Y.get('[id="field.comment"]');

    var error_handler = new LP.client.ErrorHandler();
    error_handler.clearProgressUI = function () {
        clearProgressUI();
    };
    error_handler.showError = function (error_msg) {
        display_error(submit_button, error_msg);
    };

    function clearProgressUI() {
        progress_message.get('parentNode').replaceChild(
            submit_button, progress_message);
        comment_input.removeAttribute('disabled');
    }

    function hide_or_show_submit_button(e) {
        if (comment_input.get('value') === '') {
            submit_button.set('disabled', true);
        }
        else {
            submit_button.set('disabled', false);
        }
    }
    /* Hook up hide_or_show_submit_button on both keyup and mouseup to
       handle both entering text with the keyboard, and pasting with the
       mouse.  */
    comment_input.on('keyup', hide_or_show_submit_button);
    comment_input.on('mouseup', hide_or_show_submit_button);
    hide_or_show_submit_button(null);
    submit_button.addClass('js-action');
    submit_button.setStyle('display', 'inline');
    submit_button.on('click', function(e) {
        e.halt();
        var comment_text = comment_input.get('value');
        /* Don't try to add an empty comment. */
        if (trim(comment_text) === '') {
            return;
        }
        var config = {
            on: {
                success: function(message_entry) {
                    var config = {
                        on: {
                            success: function(message_html) {
                                var fieldset = Y.get('#add-comment-form');
                                var legend = Y.get('#add-comment-form legend');
                                var comment = Y.Node.create(message_html);
                                fieldset.get('parentNode').insertBefore(
                                    comment, fieldset);
                                clearProgressUI();
                                comment_input.set('value', '');
                                Y.lazr.anim.green_flash({node: comment}).run();
                            }
                        },
                        accept: LP.client.XHTML
                    };
                    lp_client.get(message_entry.get('self_link'), config);
                },
                failure: error_handler.getFailureHandler()
            },
            parameters: {
                content: comment_input.get('value')
            }
        };
        comment_input.set('disabled', 'true');
        submit_button.get('parentNode').replaceChild(
            progress_message, submit_button);
        lp_client.named_post(
            bug_repr.self_link, 'newMessage', config);
    });
}

var Comment = function () {
        Comment.superclass.constructor.apply(this, arguments);
};

Comment.NAME = 'comment';

Comment.ATTRS = {
};
Y.extend( Comment, Y.Widget, {

    render: function() {
        setup_inline_commenting();
    }
});

Y.Comment = Comment;


}, '0.1' ,{requires:['oop', 'widget']});
