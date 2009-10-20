YUI.add('lp.errors', function(Y) {

Y.lp = Y.namespace('lp');

/*
 * Create a form button for canceling an error form
 * that won't reload the page on submit.
 *
 * @method cancel_form_button
 * @return button {Node} The form's cancel button.
*/
var cancel_form_button = function() {
    var button = Y.Node.create('<button>OK</button>');
    button.on('click', function(e) {
        e.preventDefault();
        error_overlay.hide();
    });
    return button;
};


var error_overlay;
/*
 * Create the form overlay to use when encountering errors.
 *
 * @method create_error_overlay
*/
var create_error_overlay = function() {
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
};

/**
 * Run a callback, optionally flashing a specified node red beforehand.
 *
 * If the supplied node evaluates false, the callback is invoked immediately.
 *
 * @method maybe_red_flash
 * @param flash_node The node to flash red, or null for no flash.
 * @param callback The callback to invoke.
 */
var maybe_red_flash = function(flash_node, callback)
{
    if (flash_node) {
        var anim = Y.lazr.anim.red_flash({ node: flash_node });
        anim.on('end', callback);
        anim.run();
    } else {
        callback();
    }
};


/*
 * Take an error message and display in an overlay (creating it if necessary).
 *
 * @method display_error
 * @param flash_node {Node} The node to red flash.
 * @param msg {String} The message to display.
*/
var display_error = function(flash_node, msg) {
    create_error_overlay();
    maybe_red_flash(flash_node, function(){
        error_overlay.showError(msg);
        error_overlay.show();
    });
};

Y.lp.display_error = display_error;
}, '0.1', {requires:['lazr.formoverlay']});
