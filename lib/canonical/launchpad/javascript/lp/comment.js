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
        this.submit_button = this.get_submit();
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
    get_submit: function(){
        return Y.get('[id="field.actions.save"]')
    },
    renderUI: function() {
        this.submit_button.addClass('js-action');
        this.submit_button.setStyle('display', 'inline');
    },
    validate: function() {
        return trim(this.comment_input.get('value')) !== '';
    },
    update_submit_button: function(){
        this.submit_button.set('disabled', !this.validate());
    },
    set_disabled: function(disabled){
        this.comment_input.set('disabled', disabled);
    },
    add_comment: function(e){
        e.halt();
        /* Don't try to add an empty comment. */
        if (!this.validate()) {
            return;
        }
        this.set_disabled(true)
        this.submit_button.get('parentNode').replaceChild(
            this.progress_message, this.submit_button);
        this.post_comment(bind(function(message_entry) {
            this.get_comment_HTML(
                message_entry, bind(this.insert_comment_HTML, this))
        }, this))
    },
    post_comment: function(callback) {
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
    get_comment_HTML: function(message_entry, callback){
        var config = {
            on: {
                success: callback
            },
            accept: LP.client.XHTML
        };
        this.lp_client.get(message_entry.get('self_link'), config);
    },
    insert_comment_HTML: function(message_html) {
        var fieldset = Y.get('#add-comment-form');
        var comment = Y.Node.create(message_html);
        fieldset.get('parentNode').insertBefore(comment, fieldset);
        this.reset_contents()
        Y.lazr.anim.green_flash({node: comment}).run();
    },
    reset_contents: function() {
          this.clearProgressUI();
          this.comment_input.set('value', '');
          this.syncUI();
    },
    clearProgressUI: function(){
          this.progress_message.get('parentNode').replaceChild(
              this.submit_button, this.progress_message);
          this.set_disabled(false);
    },
    bindUI: function(){
        /* Hook up updateSsubmitButton on both keyup and mouseup to
           handle both entering text with the keyboard, and pasting with the
           mouse.  */
        this.comment_input.on('keyup', bind(this.syncUI, this));
        this.comment_input.on('mouseup', bind(this.syncUI, this));
        this.submit_button.on('click', bind(this.add_comment, this));
    },
    syncUI: function(){
        this.update_submit_button();
    }
});

Y.lp.Comment = Comment;


}, '0.1' ,{requires:['oop', 'widget', 'lp.client.plugins', 'lp.errors']});
