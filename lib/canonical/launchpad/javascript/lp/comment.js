YUI.add('lp.comment', function(Y) {

var Comment = function () {
        Comment.superclass.constructor.apply(this, arguments);
};


/*
 * Create a form button for canceling an error form
 * that won't reload the page on submit.
 *
 * @method cancel_form_button
 * @return button {Node} The form's cancel button.
*/
function cancel_form_button() {
    var button = Y.Node.create('<button>OK</button>');
    button.on('click', function(e) {
        e.preventDefault();
        error_overlay.hide();
    });
    return button;
}


var error_overlay;
/*
 * Create the form overlay to use when encountering errors.
 *
 * @method create_error_overlay
*/
function create_error_overlay() {
    if (error_overlay === undefined) {
        error_overlay = new Y.lazr.FormOverlay({
            headerContent: '<h2>Error</h2>',
            form_header:  '',
            form_content:  '',
            form_submit_button: Y.Node.create(
                '<button style="display:none"></button>'),
            form_cancel_button: cancel_form_button(),
            centered: true,
            visible: false
        });
        error_overlay.render();
    }
}


/*
 * Take an error message and display in an overlay (creating it if necessary).
 *
 * @method display_error
 * @param flash_node {Node} The node to red flash.
 * @param msg {String} The message to display.
*/
function display_error(flash_node, msg) {
    create_error_overlay();
    if (flash_node) {
        var anim = Y.lazr.anim.red_flash({ node: flash_node });
        anim.on('end', function(e) {
            error_overlay.showError(msg);
            error_overlay.show();
        });
        anim.run();
    } else {
        error_overlay.showError(msg);
        error_overlay.show();
    }
}

Comment.NAME = 'comment';

Comment.ATTRS = {
};
Y.extend( Comment, Y.Widget, {
    initializer: function() {
        this.submit_button = Y.get('[id="field.actions.save"]');
        this.comment_input = Y.get('[id="field.comment"]');
    },
    renderUI: function() {
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
    addComment: function(e){
        var error_handler = new LP.client.ErrorHandler();
        error_handler.clearProgressUI = function () {
            clearProgressUI();
        };
        error_handler.showError = function (error_msg) {
            display_error(this.submit_button, error_msg);
        };

        clearProgressUI = bind(function clearProgressUI() {
            progress_message.get('parentNode').replaceChild(
                this.submit_button, progress_message);
            this.comment_input.removeAttribute('disabled');
        }, this);
        e.halt();
        var comment_text = this.comment_input.get('value');
        /* Don't try to add an empty comment. */
        if (trim(comment_text) === '') {
            return;
        }
        var config = {
            on: {
                success: bind(function(message_entry) {
                    var config = {
                        on: {
                            success: bind(function(message_html) {
                                var fieldset = Y.get('#add-comment-form');
                                var legend = Y.get('#add-comment-form legend');
                                var comment = Y.Node.create(message_html);
                                fieldset.get('parentNode').insertBefore(
                                    comment, fieldset);
                                clearProgressUI();
                                this.comment_input.set('value', '');
                                Y.lazr.anim.green_flash({node: comment}).run();
                            }, this)
                        },
                        accept: LP.client.XHTML
                    };
                    var lp_client = new LP.client.Launchpad();
                    lp_client.get(message_entry.get('self_link'), config);
                }, this),
                failure: error_handler.getFailureHandler()
            },
            parameters: {
                content: this.comment_input.get('value')
            }
        };
        this.comment_input.set('disabled', 'true');
        var progress_message = Y.Node.create(
            '<span class="update-in-progress-message">Saving...</span>');
        this.submit_button.get('parentNode').replaceChild(
            progress_message, this.submit_button);
        var lp_client = new LP.client.Launchpad();
        bug_repr = LP.client.cache.bug;
        lp_client.named_post(
            bug_repr.self_link, 'newMessage', config);
    },
    bindUI: function(){
        /* Hook up updateSsubmitButton on both keyup and mouseup to
           handle both entering text with the keyboard, and pasting with the
           mouse.  */
        this.comment_input.on('keyup', bind(this.updateSubmitButton, this));
        this.comment_input.on('mouseup', bind(this.updateSubmitButton, this));
        this.submit_button.on('click', bind(this.addComment, this));
    },
    syncUI: function(){
        this.updateSubmitButton(null);
    }
});

Y.Comment = Comment;


}, '0.1' ,{requires:['oop', 'widget', 'lp.client.plugins',
                     'lazr.formoverlay']});
