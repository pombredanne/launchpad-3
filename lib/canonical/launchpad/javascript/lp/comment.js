YUI.add('lp.comment', function(Y) {

Y.lp = Y.namespace('lp')

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
            Y.lp.display_error(this.submit_button, error_msg);
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
        this.submit_button.set('disabled', !this.validate());
    },
    setDisabled: function(disabled){
        this.comment_input.set('disabled', disabled);
    },
    addComment: function(e){
        e.halt();
        /* Don't try to add an empty comment. */
        if (!this.validate()) {
            return;
        }
        this.setDisabled(true)
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
          this.syncUI();
    },
    clearProgressUI: function(){
          this.progress_message.get('parentNode').replaceChild(
              this.submit_button, this.progress_message);
          this.setDisabled(false);
    },
    bindUI: function(){
        /* Hook up updateSsubmitButton on both keyup and mouseup to
           handle both entering text with the keyboard, and pasting with the
           mouse.  */
        this.comment_input.on('keyup', bind(this.syncUI, this));
        this.comment_input.on('mouseup', bind(this.syncUI, this));
        this.submit_button.on('click', bind(this.addComment, this));
    },
    syncUI: function(){
        this.updateSubmitButton(null);
    }
});

Y.lp.Comment = Comment;

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
        return CodeReviewComment.superclass.validate.apply(this);
    },
    setDisabled: function(disabled){
        CodeReviewComment.superclass.setDisabled.call(this, disabled);
        this.vote_input.set('disabled', disabled);
        this.review_type.set('disabled', disabled);
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
        var conversation = Y.get('[id=conversation]');
        var comment = Y.Node.create(message_html)
        conversation.appendChild(comment)
        this.resetContents()
        Y.lazr.anim.green_flash({node: comment}).run()
    },
    bindUI: function() {
        CodeReviewComment.superclass.bindUI.apply(this);
        this.vote_input.on('mouseup', bind(this.syncUI, this));
        this.review_type.on('keyup', bind(this.syncUI, this));
        this.review_type.on('mouseup', bind(this.syncUI, this));
    },
    syncUI: function() {
        CodeReviewComment.superclass.syncUI.apply(this)
        var review_type_disabled = (this.getVote() === null);
        this.review_type.set('disabled', review_type_disabled);
    }
});
Y.CodeReviewComment = CodeReviewComment

}, '0.1' ,{requires:['oop', 'io', 'widget', 'node', 'lp.client.plugins', 'lp.errors']});
