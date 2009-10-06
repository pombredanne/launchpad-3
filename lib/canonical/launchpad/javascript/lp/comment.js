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
    validate: function() {
        return trim(this.comment_input.get('value')) !== '';
    },
    updateSubmitButton: function(e){
            if (this.validate()) {
                this.submit_button.set('disabled', false);
            }
            else {
                this.submit_button.set('disabled', true);
            }
    },
    disable: function(){
        this.comment_input.set('disabled', 'disabled');
    },
    enable: function() {
        this.comment_input.removeAttribute('disabled');
    },
    addComment: function(e){
        e.halt();
        /* Don't try to add an empty comment. */
        if (!this.validate()) {
            return;
        }
        this.disable()
        this.submit_button.get('parentNode').replaceChild(
            this.progress_message, this.submit_button);
        this.postComment(bind(function(message_entry) {
            this.getCommentHTML(
                message_entry, bind(this.insertCommentHTML, this))
        }, this))
    },
    postComment: function(callback) {
        var config = {
            on: {
                success: callback,
                failure: this.error_handler.getFailureHandler()
            },
            parameters: {content: this.comment_input.get('value')}
        };
        this.lp_client.named_post(
            LP.client.cache.bug.self_link, 'newMessage', config);
    },
    getCommentHTML: function(message_entry, callback){
        var config = {
            on: {
                success: callback
            },
            accept: LP.client.XHTML
        };
        this.lp_client.get(message_entry.get('self_link'), config);
    },
    insertCommentHTML: function(message_html) {
        var fieldset = Y.get('#add-comment-form');
        var comment = Y.Node.create(message_html);
        fieldset.get('parentNode').insertBefore(comment, fieldset);
        this.resetContents()
        Y.lazr.anim.green_flash({node: comment}).run();
    },
    resetContents: function() {
          this.clearProgressUI();
          this.comment_input.set('value', '');
          this.updateSubmitButton();
    },
    clearProgressUI: function(){
          this.progress_message.get('parentNode').replaceChild(
              this.submit_button, this.progress_message);
          this.enable();
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

var CodeReviewComment = function()
{
        CodeReviewComment.superclass.constructor.apply(this, arguments);
}
CodeReviewComment.NAME = 'codereviewcomment';


Y.extend(CodeReviewComment, Comment, {
    initializer: function() {
        this.vote_input = Y.get('[id="field.vote"]');
        this.review_type = Y.get('[id="field.review_type"]');
    },
    getSubmit: function(){
        return Y.get('[id="field.actions.add"]')
    },
    getVote: function() {
        var selected_idx = this.vote_input.get('selectedIndex');
        var selected = this.vote_input.get('options').item(selected_idx)
        if (selected.get('value') == '')
            return null;
        return selected.get('innerHTML')
    },
    validate: function(){
        if (this.getVote() !== null)
            return true;
        else {
            if (this.review_type.get('value') !== '')
                return false;
        }
        return CodeReviewComment.superclass.validate.apply(this);
    },
    disable: function(){
        CodeReviewComment.superclass.disable.apply(this);
        this.vote_input.set('disabled', 'disabled');
        this.review_type.set('disabled', 'disabled');
    },
    enable: function() {
        CodeReviewComment.superclass.enable.apply(this);
        this.vote_input.removeAttribute('disabled');
        this.review_type.removeAttribute('disabled');
    },

    postComment: function(callback) {
        var config = {
            on: {
                success: callback,
                failure: this.error_handler.getFailureHandler()
            },
            parameters: {
                content: this.comment_input.get('value'),
                subject: '',
                review_type: this.review_type.get('value'),
                vote: this.getVote()
            }
        }
        this.lp_client.named_post(
            LP.client.cache.context.self_link, 'createComment', config);
    },
    getCommentHTML: function(comment_entry, callback) {
        fragment_url = 'comments/' + comment_entry.get('id') + '/+fragment';
        Y.io(fragment_url, {
            on: {
                success: function(id, response){
                    callback(response.responseText)
                },
                failure: this.error_handler.getFailureHandler()
            }
        });
    },
    resetContents: function() {
          this.review_type.set('value', '');
          this.vote_input.set('selectedIndex', 0);
          CodeReviewComment.superclass.resetContents.apply(this);
    },
    insertCommentHTML: function(message_html){
        var conversation = Y.get('#maincontent');
        var comment = Y.Node.create(message_html)
        conversation.appendChild(comment)
        this.resetContents()
        Y.lazr.anim.green_flash({node: comment}).run()
    },
    bindUI: function() {
        CodeReviewComment.superclass.bindUI.apply(this);
        this.vote_input.on('mouseup', bind(this.updateSubmitButton, this));
        this.review_type.on('keyup', bind(this.updateSubmitButton, this));
        this.review_type.on('mouseup', bind(this.updateSubmitButton, this));
    }
});
Y.CodeReviewComment = CodeReviewComment

}, '0.1' ,{requires:['oop', 'io', 'widget', 'node', 'lp.client.plugins', 'lp.errors']});
