YUI.add('lp.comment', function(Y) {

var Comment = function () {
	
	Comment.superclass.constructor.apply( this, arguments );
	
};

Comment.NAME = 'comment';

Comment.HTML_PARSER = {};

Comment.ATTRS = {
	
	text : {
		value : ''
	
	}
};
Y.extend( Comment, Y.Widget, {
  initializer : function() {}
});

Y.Comment = Comment;


}, '@VERSION@' ,{requires:['oop', 'node', 'widget']});
