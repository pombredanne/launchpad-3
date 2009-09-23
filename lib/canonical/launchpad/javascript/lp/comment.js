YUI.add('lp.comment', function(Y) {


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
    function addComment(e){
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
                    var lp_client = new LP.client.Launchpad();
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
        var lp_client = new LP.client.Launchpad();
        bug_repr = LP.client.cache.bug;
        lp_client.named_post(
            bug_repr.self_link, 'newMessage', config);
    }
    submit_button.on('click', addComment);
}

var Comment = function () {
        Comment.superclass.constructor.apply(this, arguments);
};

Comment.NAME = 'comment';

Comment.ATTRS = {
};
Y.extend( Comment, Y.Widget, {
    initializer: function() {
        this.submit_button = Y.get('[id="field.actions.save"]');
        this.comment_input = Y.get('[id="field.comment"]');
    },
    renderUI: function() {
        setup_inline_commenting();
        this.submit_button.addClass('js-action');
        this.submit_button.setStyle('display', 'inline');
    },
    updateSubmitButton: function(e){
            if (this.comment_input.get('value') === '') {
                this.submit_button.set('disabled', true);
            }
            else {
                this.submit_button.set('disabled', false);
            }
    },
    bindUI: function(){
        /* Hook up updateSsubmitButton on both keyup and mouseup to
           handle both entering text with the keyboard, and pasting with the
           mouse.  */
        this.comment_input.on('keyup', bind(this.updateSubmitButton, this));
        this.comment_input.on('mouseup', bind(this.updateSubmitButton, this));
    },
    syncUI: function(){
        this.updateSubmitButton(null);
    }
});

Y.Comment = Comment;


}, '0.1' ,{requires:['oop', 'widget', 'lp.client.plugins']});
