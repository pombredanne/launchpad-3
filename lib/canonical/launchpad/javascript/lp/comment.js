YUI.add('lp.comment', function(Y) {

var Comment = function () {
        Comment.superclass.constructor.apply(this, arguments);
};

Comment.NAME = 'comment';

Comment.ATTRS = {
};
Y.extend( Comment, Y.Widget, {
});

Y.Comment = Comment;


}, '0.1' ,{requires:['oop', 'widget']});
