YUI().add('lp.comment', function(Y) {

module = Y.namespace('lp.comment')
function Comment(config) {
    Comment.superclass.constructor.apply(this, arguments);
}

Comment.NAME = "Comment";

Comment.ATTRS = {};

Y.extend(Comment, Y.Widget, {
    renderUI: function (){
        alert ('foo');
    }
});
module.Comment = Comment

}, '1.0', {requires: ['widget']});
