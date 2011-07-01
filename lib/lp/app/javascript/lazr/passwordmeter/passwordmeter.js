/* Copyright (c) 2009, Canonical Ltd. All rights reserved. */

YUI.add('lazr.passwordmeter', function(Y){

/**
 * A password strength meter widget.
 *
 *
 * Given the id of a password field and the name of a function that will check
 * the strength of the input password this meter will display on each character
 * entered the strength value computed by the function provided.
 *
 * @module lazr.passwordmeter
 * @namespace lazr
 */
Y.namespace('lazr');

/**
 * @class PasswordMeter
 * @extends Widget
 * @constructor
 */
var PasswordMeter = function(){
	PasswordMeter.superclass.constructor.apply(this, arguments);
};

PasswordMeter.NAME = 'passwordmeter';

/**
 * The HTML_PARSER static constant is used by the Widget base class to
 * populate the configuration for the PasswordMeter instance from markup
 * already on the page.
 *
 * @property PasswordMeter.HTML_PARSER
 * @type Object
 * @static
 */
PasswordMeter.HTML_PARSER = {
};

/**
 * This function will be used to determine the password's strength. It only
 * gives a 100% strength if the password has a combination of lower case, upper
 * case, numeric and symbolic characters with at least a length of 8.
 * The function can be replaed by the user of the widget by simply supplying
 * their own function in the "func" attribute.
 * The function returns two values: strength which is an int between 0 and 100
 * and text which is one of the following strings: weak, medium, strong.
 */
var default_password_strength_function = function(password) {
    var color = '#8b0000';
    var text = '';
    if (password) {
        var len = password.length;
        var hasLower = /[a-z]/.test(password) ? 1 : 0;
        var hasUpper = /[A-Z]/.test(password) ? 1 : 0;
        var hasNumber = /\d/.test(password) ? 1 : 0;
        var hasSymbol = /[\~\`\!\@\#\$\%\^\&\*\(\)\_\-\+\=\{\}\[\]\:\;\"\'\<\>\?\|\\\,\.\/]/.test(password) ? 1 : 0;
        var points = hasLower + hasUpper + hasNumber + hasSymbol;
		if (len < 7) {
			return {
				'color': '#8b0000',
				'text': 'Stength: too short'
			}
		}
		sum = hasLower + hasUpper + hasNumber + hasSymbol;
		switch(sum) {
			case 1:
				color = '#f99300';
				text = 'fair';
				break;
			case 2:
			case 3:
				color= '#1e6400';
				text = 'good';
				break;
			case 4:
				color = '#1e6400';
				text = 'strong';
				break;
		}
	}
	return {
		'color': color,
		'text': "Strength: " + text
	}
};

PasswordMeter.ATTRS = {
	/**
	 * Current color for the password strength
	 *
	 * @attribute color
	 * @type String
	 * @default #8b0000
	 */
	color: {
		value: '#8b0000'
	},

	/**
	 * Current description of password strength
	 *
	 * @attribute text
	 * @type String
	 * @default ""
	 */
	text: {
		value: ""
	},

	/**
	 * Password field we will be monitoring
	 *
	 * @attribute input
	 * @type Node
	 * @default null
	 */
	input: {
		value: null,
		setter: function(v){
			return Y.one(v);
		}
	},

	/**
	 * Javascript function that will calculate the password's strength
	 * and strength description
	 * Should return an object literal in the form
	 * {"color": <color of the text displaying the strength>,
	 *  "text": <textual description of the strength>}
	 *
	 * @attribute func
	 * @type function
	 * @default a standard password strength function
	 */
	func: {
		value: default_password_strength_function,
		validator: function(val) {
			return Y.Lang.isFunction(val);
		}
	},
}; //end ATTRS
Y.extend(PasswordMeter, Y.Widget, {
	/**
	 * Initialize the widget.
	 *
	 * @method initializer
	 * @protected
	 */
	initializer: function(cfg){
	},

	/**
	 * Destroy the widget.
	 *
	 * @method dest
	 * @protected
	 */
	destructor: function(){
	},

	/**
	 * Update the DOM structure and edit CSS classes.
	 *
	 * @method renderUI
	 * @protected
	 */
	renderUI: function(){
		this.get("contentBox").setStyle('width', this.get('input').getStyle('width'));
		this.get("contentBox").setStyle('height', this.get('input').getStyle('height'));
		this.updateDesplay();
	},

	/**
	 * Set the event handlers for the input element.
	 *
	 * @method bindUI
	 * @protected
	 */
	bindUI: function(){
		var input = this.get('input');
		input.on('keyup', this._onKeyup, this);
	},

	/**
	 * Synchronize the DOM with our current attribute state
	 *
	 * @method syncUI
	 * @protected
	 */
	syncUI: function(){
		this.updateDesplay();
	},

	/**
	 * Capture each password character
	 *
	 * @method _onKeyup
	 * @protected
	 * @param e {Event.Custom} The event object.
	 */
	_onKeyup: function(e){
		var input = this.get('input');
		var password = input.get('value');
		var result = this.get('func')(password);
		this.set('color', result.color);
		this.set('text', result.text);
		this.syncUI();
	},

	updateDesplay: function() {
		this.get('contentBox').set('innerHTML', this.get('text'));
		this.get('contentBox').setStyle("color", this.get('color'));
	}
}); //end extend

Y.PasswordMeter = PasswordMeter;
}, "0.1", {
    "skinnable": true,
    "requires": ["widget", "lazr.base"]
});
