/** Copyright (c) 2009, Canonical Ltd. All rights reserved.
 *
 * @module lp.pofile
 * @requires event, event-key, node, cookie, anim
 */

YUI.add('lp.pofile', function(Y) {

Y.log('loading lp.pofile');
var self = Y.namespace('lp.pofile');

/**
 * Function to disable/enable all suggestions as they are marked/unmarked
 * for dismission.
 */
self.setupSuggestionDismissal = function(e) {
    all_dismiss_boxes = Y.all('.dismiss_action');
    if (all_dismiss_boxes !== null) {
        all_dismiss_boxes.each(function(checkbox) {
            var classbase = checkbox.get('id');
            var current_class = classbase.replace(/dismiss/, 'current');
            var current_radios = Y.all('.' + current_class);
            var dismissables = Y.all('.' + classbase+'able');
            // The button and textarea cannot be fetched beforehand
            // because they are or may be created dynamically.
            var dismissable_inputs_class = [
                '.', classbase, 'able_button input, ',
                '.', classbase, 'able_button button, ',
                '.', classbase, 'able_button textarea'].join("");
            checkbox.on('click', function(e) {
                if (checkbox.get('checked')) {
                    dismissables.addClass('dismissed');
                    Y.all(dismissable_inputs_class).set('disabled', true);
                    current_radios.set('checked', true);
                } else {
                    dismissables.removeClass('dismissed');
                    Y.all(dismissable_inputs_class).set('disabled', false);
                }
            });
        });
    }
};

var hide_notification = function(node) {
    var hide_anim = new Y.Anim({
        node: node,
        to: { height: 0,
            marginTop: 0, marginBottom: 0,
            paddingTop: 0, paddingBottom: 0 }
    });
    node.setStyle('border', 'none');
    hide_anim.set('duration', 0.4);
    hide_anim.on('end', function(e) {
        node.setStyle('display', 'none');
    });
    hide_anim.run();
};


self.updateNotificationBox = function(e) {
    var notice = Y.one('.important-notice-container');
    if (notice === null) {
        return;
    }
    var balloon = notice.one('.important-notice-balloon');
    var dismiss_notice_cookie = ('translation-docs-for-' +
                               documentation_cookie);

    // Check the cookie to see if the user has already dismissed
    // the notification box for this session.
    var already_seen = Y.Cookie.get(dismiss_notice_cookie, Boolean);
    if (already_seen) {
     notice.setStyle('display', 'none');
    }

    var cancel_button = notice.one(
      '.important-notice-cancel-button');
    // Cancel button starts out hidden.  If user has JavaScript,
    // then we want to show it.
    cancel_button.setStyle('visibility', 'visible');
    cancel_button.on('click', function(e) {
      e.halt();
      hide_notification(balloon);
      Y.Cookie.set(dismiss_notice_cookie, true);
    });
};


var setFocus = function(e, field) {
    //Y.log(e.type + ":" + e.keyCode + ': ' + field);
    // if there is nofield, do nothing
    if (Y.one('#' + field)) {
        Y.one('#' + field).focus();
    }
};


var setNextFocus = function(e, field) {
    setFocus(e,field);
    // stopPropagation() and preventDefault()
    e.halt();
};


var setPreviousFocus = function(e, field, original) {

    // Original singular test is focused first to make sure
    // it is visible when scrolling up
    setFocus(e, original);
    setFocus(e, field);
    // stopPropagation() and preventDefault()
    e.halt();
};


var copyOriginalTextOne = function(from_id, to_id, select_id) {
    var from = Y.one('#' + from_id);
    var to = Y.one('#' + to_id);

    // The replacement regex strips all tags from the html.
    to.set('value', unescapeHTML(
        from.get('innerHTML').replace(/<\/?[^>]+>/gi, "")));
    selectWidget(select_id);
};


var copyOriginalTextPlural = function (from_id,
                                              to_id_pattern, nplurals) {
    // skip when x is 0, as that is the singular
    for (var x = 1; x < nplurals; x++) {
        var to_id = to_id_pattern + x + "_new";
        var to_select = to_id_pattern + x + "_new_select";
        copyOriginalTextOne(from_id, to_id, to_select);
    }
};


var copyOriginalTextAll = function(e, original_stem, translation_stem) {

    var original_singular = original_stem + '_singular';
    var original_plural = original_stem + '_plural';
    var singular_select = translation_stem + '_translation_0_new_select';
    var translation_singular = translation_stem + '_translation_0_new';
    var translation_plural = translation_stem + '_translation_';
    //Y.log(e.type + ":" + e.keyCode + ': ' + singular_select);
    // Copy singular text
    copyOriginalTextOne(
        original_singular, translation_singular, singular_select);

    // Copy plural text if needed
    if (Y.one('#' + translation_plural + '1')) {
        copyOriginalTextPlural(
            original_plural, translation_plural, plural_forms);
    }
    // stopPropagation() and preventDefault()
    e.halt();
};


var selectWidget = function(widget) {
    if (Y.one('#' + widget)) {
        Y.one('#' + widget).set('checked', true);
    }
};


var selectTranslation = function(e, widget) {
    //Y.log(e.type + ":" + e.keyCode + ': ' + widget);
    // Don't select when tabbing, navigating Up or Down and simply pressing
    // enter to submit the form.
    if (e.keyCode == 9 || e.keyCode == 13 ||
        e.keyCode == 40 || e.keyCode == 38) {
        return;
    }
    selectWidget(widget);
};


/**
 * Initialize event-key bindings such as moving to the next or previous
 * field, or copying original text
 */
self.initializeKeyBindings = function(e) {

    var fields = tabindex_chain.split(' ');
    // The last field is Save & Continue button
    fields.push('save_and_continue_button');

    for (var key = 0; key < fields.length; key++) {
        var next = key + 1;
        var previous = key - 1;

        var html_parts = fields[key].split('_');
        var original_stem = html_parts[0] + '_' + html_parts[1];
        var translation_stem = original_stem + '_' + html_parts[2];
        var select_widget = (
            translation_stem + '_' + html_parts[3] + '_' +
            html_parts[4] + '_new_select');

        Y.on(
            'change', selectTranslation,
            '#' + fields[key], Y, select_widget);
        Y.on(
            'keypress', selectTranslation,
            '#' + fields[key], Y, select_widget);

        // Set next field and copy text for all but last field
        // (last is Save & Continue button)
        if (key < fields.length - 1) {
            Y.on(
                'key', setNextFocus, '#' + fields[key],
                'down:40+shift+alt', Y, fields[next]);
            Y.on(
                'key', copyOriginalTextAll, '#' + fields[key],
                'down:67+shift+alt', Y, original_stem, translation_stem);
        }

        // Set previous field for all but first field
        if (key > 0) {
            var parts = fields[previous].split('_');
            var singular_copy_text = (
                parts[0] + '_' + parts[1] + '_singular_copy_text');
            Y.on(
                'key', setPreviousFocus, '#' + fields[key],
                'down:38+shift+alt', Y, fields[previous],
                singular_copy_text);
        }
    }
};

}, "0.1", {"requires": ["event", "event-key", "node", 'cookie', 'anim']});
