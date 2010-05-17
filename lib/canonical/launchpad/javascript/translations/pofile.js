/** Copyright (c) 2009, Canonical Ltd. All rights reserved.
 *
 * @module lp.pofile
 * @requires anim, cookie, event-key, event, node
 */

YUI.add('lp.pofile', function(Y) {

Y.log('loading lp.pofile');
var self = Y.namespace('lp.pofile');

var KEY_CODE_TAB = 9;
var KEY_CODE_ENTER = 13;
var KEY_CODE_LEFT = 37;
var KEY_CODE_UP = 38;
var KEY_CODE_RIGHT = 39;
var KEY_CODE_DOWN = 40;
var KEY_CODE_0 = 48;
var KEY_CODE_A = 65;
var KEY_CODE_B = 66;
var KEY_CODE_C = 67;
var KEY_CODE_D = 68;
var KEY_CODE_F = 70;
var KEY_CODE_J = 74;
var KEY_CODE_K = 75;
var KEY_CODE_L = 76;
var KEY_CODE_N = 78;
var KEY_CODE_P = 80;
var KEY_CODE_R = 82;
var KEY_CODE_S = 83;

/**
 * Function to disable/enable all suggestions as they are marked/unmarked
 * for dismission.
 */
var setupSuggestionDismissal = function(e) {
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


var updateNotificationBox = function(e) {
  var notice = Y.one('.important-notice-container');
  if (notice === null) {
    // We have no notice container on this page, this is why there is
    // nothing more to be done by this function.
    return;
  }
  var balloon = notice.one('.important-notice-balloon');
  var dismiss_notice_cookie = ('translation-docs-for-' +
                               documentation_cookie);

  // Check the cookie to see if the user has already dismissed
  // the notification box for this session.
  var already_seen = Y.Cookie.get(dismiss_notice_cookie, Boolean);
  if (already_seen !== null) {
     notice.setStyle('display', 'none');
  }

  var cancel_button = notice.one(
      '.important-notice-cancel-button');
  // Cancel button starts out hidden.  If user has JavaScript,
  // then we want to show it.
  if (cancel_button === null) {
    // No cancel button was found to attach the action.
    return;
  }
  cancel_button.setStyle('visibility', 'visible');
  cancel_button.on('click', function(e) {
      e.halt();
      hide_notification(balloon);
      Y.Cookie.set(dismiss_notice_cookie, true);
  });
};


var setFocus = function(field) {
    // if there is nofield, do nothing
    if (Y.one('#' + field) !== null) {
        Y.one('#' + field).focus();
    }
};


var setNextFocus = function(e, field) {
    setFocus(field);
    // stopPropagation() and preventDefault()
    e.halt();
};


var setPreviousFocus = function(e, field, original) {

    // Original singular test is focused first to make sure
    // it is visible when scrolling up
    setFocus(original);
    setFocus(field);
    // stopPropagation() and preventDefault()
    e.halt();
};


var copyOriginalTextOne = function(from_id, to_id, select_id) {
    var from = Y.one('#' + from_id);
    var to = Y.one('#' + to_id);
    // The replacement regex strips all tags from the html.
    to.set('value', unescapeHTML(
        from.get('innerHTML').replace(/<\/?[^>]+>/gi, "")));
    selectWidgetByID(select_id);
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


var copyOriginalTextAll = function(e, msgset_id, translation_stem) {

    var original_singular = msgset_id + '_singular';
    var original_plural = msgset_id + '_plural';
    var singular_select = translation_stem + '_translation_0_new_select';
    var translation_singular = translation_stem + '_translation_0_new';
    var translation_plural = translation_stem + '_translation_';
    // Copy singular text
    copyOriginalTextOne(
        original_singular, translation_singular, singular_select);

    // Copy plural text if needed
    if (Y.one('#' + translation_plural + '1') !== null) {
        copyOriginalTextPlural(
            original_plural, translation_plural, plural_forms);
    }
    // stopPropagation() and preventDefault()
    e.halt();
};


var selectWidgetByID = function(widget) {
    var node = Y.one('#' + widget);
    if (node !== null) {
        node.set('checked', true);
    }
};


var toggleWidget = function(widget) {
    var node = Y.one('#' + widget);
    if (node !== null) {
        if (node.get('checked')) {
            node.set('checked', false);
        } else {
            node.set('checked', true);
        }
    }
};


var selectTranslation = function(e, field) {
    // Don't select when tabbing, navigating and simply pressing
    // enter to submit the form.
    // Also, don't select when using keyboard shortcuts (ie Alt+Shift+KEY)
    // Looks like this is not needed for Epiphany and Chromium
    if (e.keyCode == KEY_CODE_TAB || e.keyCode == KEY_CODE_ENTER ||
        e.keyCode == KEY_CODE_LEFT || e.keyCode == KEY_CODE_UP ||
        e.keyCode == KEY_CODE_RIGHT || e.keyCode == KEY_CODE_DOWN ||
        (e.shiftKey && e.altKey)) {
            return;
    }
    var translation_select_id = field + '_select';
    selectWidgetByID(translation_select_id);
};


var initializeGlobalKeyBindings = function(fields) {

    Y.get('document').on("keyup", function(e) {
        var link;
        // Shift+Alt+S - Save form
        if (e.shiftKey && e.altKey && e.keyCode == KEY_CODE_S) {
            Y.one('#save_and_continue_button').invoke('click');
        }
        // Shift+Alt+F - Go to search field
        if (e.shiftKey && e.altKey && e.keyCode == KEY_CODE_F) {
            setFocus('search_box');
        }
        // Shift+Alt+B - Go to first translation field
        if (e.shiftKey && e.altKey && e.keyCode == KEY_CODE_B) {
            setFocus(fields[0]);
        }
        // Shift+Alt+N - Go to next page in batch
        if (e.shiftKey && e.altKey && e.keyCode == KEY_CODE_N) {
            link = Y.one('#batchnav_next');
            if (link !== null){
                window.location.assign(link.get('href'));
            }
        }
        // Shift+Alt+P - Go to previous page in batch
        if (e.shiftKey && e.altKey && e.keyCode == KEY_CODE_P) {
            link = Y.one('#batchnav_previous');
            if (link !== null){
                window.location.assign(link.get('href'));
            }
        }
        // Shift+Alt+A - Go to first page in batch
        if (e.shiftKey && e.altKey && e.keyCode == KEY_CODE_A) {
            link = Y.one('#batchnav_first');
            if (link !== null){
                window.location.assign(link.get('href'));
            }
        }
        // Shift+Alt+L - Go to last page in batch
        if (e.shiftKey && e.altKey && e.keyCode == KEY_CODE_L) {
            link = Y.one('#batchnav_last');
            if (link !== null){
                window.location.assign(link.get('href'));
            }
        }
    });
};


var initializeSuggestionsKeyBindings = function(stem) {

    suggestions = Y.all('.' + stem.replace(/_new/,"") + ' input');
    suggestions.each(function(node) {
        // Only add keybinding for the first 9 suggestions
        var index = suggestions.indexOf(node);
        if (index < 10) {
            // Shift+Alt+NUMBER - Mark suggestion NUMBER
            Y.on('key', function(e, id) {
                    selectWidgetByID(id);
                },
                '#' + stem, 'down:' + Number(index+49) + '+shift+alt',
                Y, node.get('id'));
        }
    });
};

/*
 * Adapter for calling functions from Y.on().
 * It is used for ingnoring the `event` parameter that is passed to all
 * functions called by Y.on().
 */
var on_event_adapter = function(event, method, argument) {
    method(argument);
};

var initializeFieldsKeyBindings = function (fields) {
    for (var key = 0; key < fields.length; key++) {
        var next = key + 1;
        var previous = key - 1;

        // fields[key] has one of the following formats:
        //  * msgset_1_es_translation_0_new
        //  * msgset_2_pt_BR_translation_0_new
        // msgset_id is 'msgset_1' or 'msgset_2'
        // translation_stem has one of the following formats:
        //  * msgset_1_es
        //  * msgset_2_pt_BR
        // translation_select_id has one of the following formats:
        //  * msgset_1_es_translation_0_new_select
        //  * msgset_2_pt_BR_translation_0_new_select
        var html_parts = fields[key].split('_');
        var msgset_id = html_parts[0] + '_' + html_parts[1];
        var translation_stem = fields[key].replace(
            /_translation_(\d)+_new/,"");

        Y.on(
            'change', selectTranslation,
            '#' + fields[key], Y, fields[key]);
        Y.on(
            'keypress', selectTranslation,
            '#' + fields[key], Y, fields[key]);

        // Set next field and copy text for all but last field
        // (last is Save & Continue button)
        if (key < fields.length - 1) {
            // Shift+Alt+J - Go to next translation
            Y.on(
                'key', setNextFocus, '#' + fields[key],
                'down:' + KEY_CODE_J + '+shift+alt', Y, fields[next]);
            // Shift+Alt+KEY_DOWN - Go to next translation
            Y.on(
                'key', setNextFocus, '#' + fields[key],
                'down:' + KEY_CODE_DOWN + '+shift+alt', Y, fields[next]);
            // Shift+Alt+C - Copy original text
            Y.on(
                'key', copyOriginalTextAll, '#' + fields[key],
                'down:' + KEY_CODE_C + '+shift+alt',
                Y, msgset_id, translation_stem);

            // Shift+Alt+R - Toggle someone should review
            Y.on(
                'key', on_event_adapter,
                '#' + fields[key], 'down:' + KEY_CODE_R + '+shift+alt', Y,
                toggleWidget, msgset_id + '_force_suggestion');

            // Shift+Alt+D - Toggle dismiss all translations
            Y.on(
                'key', on_event_adapter,
                '#' + fields[key], 'down:' + KEY_CODE_D + '+shift+alt', Y,
                toggleWidget, msgset_id + '_dismiss');

            // Shift+Alt+0 - Mark current translation
            Y.on(
                'key', on_event_adapter,
                '#' + fields[key], 'down:' + KEY_CODE_0 + '+shift+alt', Y,
                selectWidgetByID,
                fields[key].replace(/_new/, "_radiobutton"));


            initializeSuggestionsKeyBindings(fields[key]);
        }

        // Set previous field for all but first field
        if (key > 0) {
            var parts = fields[previous].split('_');
            var singular_copy_text = (
                parts[0] + '_' + parts[1] + '_singular_copy_text');
            // Shift+Alt+K - Go to previous translation
            Y.on(
                'key', setPreviousFocus, '#' + fields[key],
                'down:' + KEY_CODE_K + '+shift+alt', Y, fields[previous],
                singular_copy_text);
            // Shift+Alt+KEY_UP - Go to previous translation
            Y.on(
                'key', setPreviousFocus, '#' + fields[key],
                'down:' + KEY_CODE_UP + '+shift+alt', Y, fields[previous],
                singular_copy_text);
        }
    }
};

var initializeKeyBindings = function(e) {

    if (translations_order.length < 1) {
        // If no translations fiels are displayed on the page
        // don't initialize the translations order
        return;
    }

    var fields = translations_order.split(' ');
    // The last field is Save & Continue button
    fields.push('save_and_continue_button');

    initializeGlobalKeyBindings(fields);
    initializeFieldsKeyBindings(fields);
};

/*
 * Controls the behavior for reseting current translations
 */
var resetTranslation = function (event, translation_id) {
    if (this === null) {
        // Don't do nothing if we don't have a context object.
        return;
    }
    if (this.get('checked') === true) {
        var new_translation_select = Y.one(
            '#' + translation_id + '_select');
        if (new_translation_select !== null) {
            new_translation_select.set('checked', true);
        }
    } else {
        var new_translation_field = Y.one('#' + translation_id);
        if (new_translation_field !== null &&
            new_translation_field.get('value') === '') {
           var current_select_id = translation_id.replace(
               /_new$/, '_radiobutton');
           var current_select = Y.one('#' + current_select_id);
           if (current_select !== null) {
               current_select.set('checked', true);
           }
        }
    }
};


var initializeResetBehavior = function (fields) {
    for (var key = 0; key < fields.length; key++) {
        var html_parts = fields[key].split('_');
        var msgset_id = html_parts[0] + '_' + html_parts[1];
        var node = Y.one('#' + msgset_id + '_force_suggestion');
        if (node === null) {
            // If we don't have a force_suggestion checkbox associated with
            // this field, just continue to the next field.
            break;
        }
        Y.on('click', resetTranslation, node , node, fields[key]
        );
    }
};

/**
 * Initialize common Javascript code for POFile and TranslationMessage
 * +translate pages.
 *
 * This will add event-key bindings such as moving to the next or previous
 * field, or copying original text.
 * It will also initializing the reset checkbox behavior and will show the
 * error notifications.
 */
var initializeBaseTranslate = function () {
    try {
      setupSuggestionDismissal();
    } catch (setup_suggestion_dismissal_error) {
      Y.log(setup_suggestion_dismissal_error, "error");
    }

    try {
      initializeKeyBindings();
    } catch (initialize_key_bindings_error) {
      Y.log(initialize_key_bindings_error, "error");
    }

    try {
      var fields = translations_order.split(' ');
      initializeResetBehavior(fields);
    } catch (initialize_reset_behavior_error) {
      Y.log(initialize_reset_behavior_error, "error");
    }

    try {
      setFocus(autofocus_field);
    } catch (set_focus_error) {
      Y.log(set_focus_error, "error");
    }
};

/**
 * Initialize Javascript code for a POFile +translate page.
 *
 * This will initialize the base code and will also show the guidelines
 * if needeed.
 */
self.initializePOFile = function(e) {
    try {
      updateNotificationBox();
    } catch (update_notification_box_error) {
      Y.log(update_notification_box_error, "error");
    }
    initializeBaseTranslate();
};

/**
 * Initialize Javascript code for a TranslationMessage +translate page.
 *
 * This will initialize the base code.
 */
self.initializeTranslationMessage = function(e) {
    initializeBaseTranslate();
};


}, "0.1", {"requires": ["event", "event-key", "node", "cookie", "anim"]});

