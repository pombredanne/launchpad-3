YUI.add('lp.comment', function(Y) {

var Comment = function () {
        Comment.superclass.constructor.apply(this, arguments);
};


Comment.NAME = 'comment';

Comment.ATTRS = {
};
Y.extend(Comment, Y.Widget, {
    initializer: function() {
        this.submit_button = this.getSubmit();
        this.comment_input = Y.get('[id="field.comment"]');
        this.lp_client = new LP.client.Launchpad();
        this.error_handler = new LP.client.ErrorHandler();
        this.error_handler.clearProgressUI = bind(this.clearProgressUI, this);
        this.error_handler.showError = bind(function (error_msg) {
            Y.display_error(this.submit_button, error_msg);
        }, this);
        this.progress_message = Y.Node.create(
            '<span class="update-in-progress-message">Saving...</span>');
    },
    getSubmit: function(){
        return Y.get('[id="field.actions.save"]')
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
        e.halt();
        var comment_text = this.comment_input.get('value');
        /* Don't try to add an empty comment. */
        if (trim(comment_text) === '') {
            return;
        }
        this.comment_input.set('disabled', 'true');
        this.submit_button.get('parentNode').replaceChild(
            this.progress_message, this.submit_button);
        var config = {
            on: {
                success: bind(this.addCommentHTML, this),
                failure: this.error_handler.getFailureHandler()
            },
            parameters: {
                content: this.comment_input.get('value')
            }
        };
       this.lp_client.named_post(
            this.getPostUrl(), 'newMessage', config);
    },
    getPostUrl: function(){
        return LP.client.cache.bug.self_link;
    },
    addCommentHTML: function(message_entry) {
        var config = {
            on: {
                success: bind(function(message_html) {
                    var fieldset = Y.get('#add-comment-form');
                    var comment = Y.Node.create(message_html);
                    fieldset.get('parentNode').insertBefore(
                        comment, fieldset);
                    this.clearProgressUI();
                    this.comment_input.set('value', '');
                    Y.lazr.anim.green_flash({node: comment}).run();
                }, this)
            },
            accept: LP.client.XHTML
        };
        this.lp_client.get(message_entry.get('self_link'), config);
    },
    clearProgressUI: function(){
          this.progress_message.get('parentNode').replaceChild(
              this.submit_button, this.progress_message);
          this.comment_input.removeAttribute('disabled');
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


}, '0.1' ,{requires:['oop', 'widget', 'lp.client.plugins', 'lp.errors']});
