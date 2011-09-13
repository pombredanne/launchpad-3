/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 */

YUI.add('lp.app.picker', function(Y) {

var namespace = Y.namespace('lp.app.picker');

var BATCH_SIZE = 6;
var MAX_BATCHES = 20;

/* Add a picker widget which will PATCH a given attribute on
 * a given resource.
 *
 * @method addPickerPatcher
 * @param {String} vocabulary Name of the vocabulary to query.
 * @param {String} resource_uri The object being modified.
 * @param {String} attribute_name The attribute on the resource being
 *                                modified.
 * @param {String} content_box_id
 * @param {Object} config Object literal of config name/value pairs. The
 *                        values listed below are common for all picker types.
 *     config.picker_type: the type of picker to create (default or person).
 *     config.header: a line of text at the top of the widget.
 *     config.step_title: overrides the subtitle.
 *     config.null_display_value: Override the default 'None' text.
 *     config.show_search_box: Should the search box be shown.
 *         Vocabularies that are not huge should not have a search box.
 */
namespace.addPickerPatcher = function (
    vocabulary, resource_uri, attribute_name,
    content_box_id, config) {

    if (Y.UA.ie) {
        return;
    }

    var null_display_value = 'None';
    var show_search_box = true;
    var vocabulary_filters;

    resource_uri = Y.lp.client.normalize_uri(resource_uri);

    if (config !== undefined) {
        if (config.null_display_value !== undefined) {
            null_display_value = config.null_display_value;
        }
        if (config.show_search_box !== undefined) {
            show_search_box = config.show_search_box;
        }
        vocabulary_filters = config.vocabulary_filters;
    }

    var content_box = Y.one('#' + content_box_id);

    var activator = new Y.lazr.activator.Activator(
        {contentBox: content_box});

    var failure_handler = function (xid, response, args) {
        activator.renderFailure(
            Y.Node.create(
                '<div>' + response.statusText +
                    '<pre>' + response.responseText + '</pre>' +
                '</div>'));
    };

    var save = function (picker_result) {
        activator.renderProcessing();
        var success_handler = function (entry) {
          var to_render = null_display_value;
          var selected_value = null;
          if (entry.get(attribute_name) !== null) {
              to_render = entry.getHTML(attribute_name);
              selected_value = picker_result.api_uri;
          }
          // NB We need to set the selected_value_metadata attribute first
          // because we listen for changes to selected_value.
          picker.set('selected_value_metadata', picker_result.metadata);
          picker.set('selected_value', selected_value);
          activator.renderSuccess(to_render);
        };

        var patch_payload = {};
        if (Y.Lang.isValue(picker_result.api_uri)) {
            patch_payload[attribute_name] = Y.lp.client.get_absolute_uri(
                picker_result.api_uri);
        } else {
            patch_payload[attribute_name] = null;
        }

        var client = new Y.lp.client.Launchpad();
        client.patch(picker._resource_uri, patch_payload, {
            accept: 'application/json;include=lp_html',
            on: {
                success: success_handler,
                failure: failure_handler
            }
        });
    };

    config.save = save;
    var picker = namespace.create(
        vocabulary, config, undefined, vocabulary_filters);
    picker._resource_uri = resource_uri;

    // If we are to pre-load the vocab, we need a spinner.
    // We set it up here because we only want to do it once and the
    // activator.subscribe callback below is called each time the picker
    // is activated.
    if( !show_search_box ) {
        // The spinner displays a "Loading..." message while vocab loads.
        config.temp_spinner = create_temporary_spinner(picker);
    }

    activator.subscribe('act', function (e) {
        if (!show_search_box) {
          config.temp_spinner.removeClass('unseen');
          picker.set('min_search_chars', 0);
          picker.fire(Y.lazr.picker.Picker.SEARCH, '');
          picker.get('contentBox').one(
              '.yui3-picker-search-box').addClass('unseen');
        }
        picker.show();
    });
    activator.render();
    return picker;
};

/*
 * Show the Loading.... spinner (used when we preload the entire vocab).
 */
function create_temporary_spinner(picker) {
    var node = picker.get('contentBox').one('.yui3-picker-batches');
    var temp_spinner = Y.Node.create([
    '<div class="unseen" align="center">',
    '<img src="/@@/spinner"/>Loading...',
    '</div>'].join(''));
    node.insert(temp_spinner, node);
    return temp_spinner;
}

/*
 * Remove the Loading.... spinner (if it exists).
 */
function hide_temporary_spinner(temp_spinner) {
    if (temp_spinner !== undefined && temp_spinner !== null) {
        temp_spinner.addClass('unseen');
    }
}

/*
 * After the user selects an item using the picker, this function can be used
 * to present the user with a yes/no prompt to ensure they really want to use
 * the selection. If they answer yes, the selection is processed as normal. If
 * they answer no, they can make another selection.
 *
 * @param {Picker} picker The picker displaying the yes/no content.
 * @param {String} content The html content to display.
 * @param {String} yes_label The label for the "yes" button.
 * @param {String} no_label The label for the "no" button.
 * @param {Object} yes_fn The function to call if the user answers yes.
 * @param {Object} no_fn The function to call if the user answers no.
 */
namespace.yesno_save_confirmation = function(
        picker, content, yes_label, no_label, yes_fn, no_fn) {

    var node = Y.Node.create(
        ['<div class="validation-node">',
          '<div class="step-on" style="width: 100%;"></div>',
          '<div class="transparent important-notice-popup">',
            '<div class="validation-content-placeholder"></div>',
            '<div class="extra-form-buttons">',
              '<button class="yes_button" type="button"></button>',
              '<button class="no_button" type="button"></button>',
            '</div>',
          '</div>',
        '</div>'].join(''));

    var button_callback = function(e, callback_fn) {
        e.halt();
        if (Y.Lang.isFunction(callback_fn) ) {
            callback_fn();
        }
        reset_form(picker);
    };
    node.one(".yes_button")
        .set('text', yes_label)
        .on('click', function(e) { button_callback(e, yes_fn); });

    node.one(".no_button")
        .set('text', no_label)
        .on('click', function(e) { button_callback(e, no_fn); });

    node.one(".validation-content-placeholder").replace(content);
    picker.get('contentBox').one('.yui3-widget-bd').insert(node, 'before');
    animate_validation_content(picker, node.one(".important-notice-popup"));
};

/*
 * Insert the validation content into the form and animate its appearance.
 */
function animate_validation_content(picker, validation_content) {
    picker.get('contentBox').one('.yui3-widget-bd').hide();
    picker.get('contentBox').all('.steps').hide();
    var validation_fade_in = new Y.Anim({
        node: validation_content,
        to: {opacity: 1},
        duration: 0.9
    });
    validation_fade_in.run();
}

/*
 * Restore a picker to its functional state after a validation operation.
 */
function reset_form(picker) {
    picker.get('contentBox').all('.steps').show();
    var validation_node = picker.get('contentBox').one('.validation-node');
    var content_node = picker.get('contentBox').one('.yui3-widget-bd');
    if (validation_node !== null) {
        validation_node.get('parentNode').removeChild(validation_node);
        content_node.addClass('transparent');
        content_node.setStyle('opacity', 0);
        content_node.show();
        var content_fade_in = new Y.Anim({
            node: content_node,
            to: {opacity: 1},
            duration: 0.6
        });
        content_fade_in.run();
    } else {
        content_node.removeClass('transparent');
        content_node.setStyle('opacity', 1);
        content_node.show();
    }
}


/*
 * Connect the onchange event of the select menu to copy the selected value
 * to the text input.
 *
 * @param {Node} select_menu The select menu with suggested matches.
 * @param {Node} text_input The input field to copy the selected match too.
 */
namespace.connect_select_menu = function (select_menu, text_input) {
    if (Y.Lang.isValue(select_menu)) {
        var copy_selected_value = function(e) {
            text_input.value = select_menu.value;
        };
        Y.on('change', copy_selected_value, select_menu);
    }
};

/**
  * Creates a picker widget that has already been rendered and hidden.
  *
  * @requires dom, dump, lazr.overlay
  * @method create
  * @param {String} vocabulary Name of the vocabulary to query.
  * @param {Object} config Optional Object literal of config name/value pairs.
  *                        config.header is a line of text at the top of
  *                        the widget.
  *                        config.step_title overrides the subtitle.
  *                        config.save is a Function (optional) which takes
  *                        a single string argument.
  *                        config.show_search_box: Should the search box be
  *                        shown.
  * @param {String} associated_field_id Optional Id of the text field to
  *                        to be updated with the value selected by the
  *                        picker.
  * @param {Object} vocabulary_filters Optional List of filters which are
  *                        supported by the vocabulary. Filter objects are a
 *                         dict of name, title, description values.
  *
  */
namespace.create = function (vocabulary, config, associated_field_id,
                             vocabulary_filters) {
    if (Y.UA.ie) {
        return;
    }

    var header = 'Choose an item.';
    var step_title = "Enter search terms";
    var show_search_box = true;
    var picker_type = "default";
    if (config !== undefined) {
        if (config.header !== undefined) {
            header = config.header;
        }

        if (config.step_title !== undefined) {
            step_title = config.step_title;
        }

        if (config.show_search_box !== undefined) {
            show_search_box = config.show_search_box;
        }

        if (config.picker_type !== undefined) {
            picker_type = config.picker_type;
        }
    } else {
        config = {};
    }

    if (typeof vocabulary !== 'string' && typeof vocabulary !== 'object') {
        throw new TypeError(
            "vocabulary argument for Y.lp.picker.create() must be a " +
            "string or associative array: " + vocabulary);
    }

    var new_config = Y.merge(config, {
        associated_field_id: associated_field_id,
        align: {
            points: [Y.WidgetPositionAlign.CC,
                     Y.WidgetPositionAlign.CC]
        },
        progressbar: true,
        progress: 100,
        headerContent: "<h2>" + header + "</h2>",
        steptitle: step_title,
        zIndex: 1000,
        visible: false,
        filter_options: vocabulary_filters
        });

    var picker = null;
    if (picker_type === 'person') {
        picker = new Y.lazr.picker.PersonPicker(new_config);
    } else {
        picker = new Y.lazr.picker.Picker(new_config);
    }

    // We don't want the default save to fire since this hides
    // the form. We want to do this ourselves after any validation has had a
    // chance to be performed.
    picker.publish('save', { defaultFn: function(){} } );

    // Has the user performed a search yet?
    var user_has_searched = false;

    picker.subscribe('save', function (e) {
        Y.log('Got save event.');
        var picker_result = e.details[Y.lazr.picker.Picker.SAVE_RESULT];
        var do_save = function() {
            user_has_searched = false;
            picker.hide();
            if (Y.Lang.isFunction(config.save)) {
                config.save(picker_result);
            }
            picker._defaultSave(e);
        };
        var validate_callback = config.validate_callback;
        if (Y.Lang.isFunction(validate_callback)) {
            validate_callback(
                    picker, picker_result, do_save, undefined);
        } else {
            do_save();
        }
    });

    picker.subscribe('cancel', function (e) {
        Y.log('Got cancel event.');
        reset_form(picker);
        user_has_searched = false;
    });

    if (config.extra_no_results_message !== null) {
        picker.before('resultsChange', function (e) {
            var new_results = e.details[0].newVal;
            if (new_results.length === 0) {
                picker.set('footer_slot',
                    Y.Node.create(config.extra_no_results_message));
            } else {
                picker.set('footer_slot', null);
            }
        });
    }

    // Search for results, create batches and update the display.
    // in the widget.
    var search_handler = function (e) {
        Y.log('Got search event:' + Y.dump(e.details));
        var search_text = e.details[0];
        var selected_batch = e.details[1] || 0;
        // Was this search initiated automatically, perhaps to load
        // suggestions?
        var automated_search = e.details[2] || false;
        var search_filter = e.details[3];
        var start = BATCH_SIZE * selected_batch;
        var batch = 0;

        // Record whether or not the user has initiated a search yet.
        user_has_searched = user_has_searched || !automated_search;

        var display_vocabulary = function(results, total_size, start) {
            var max_size = MAX_BATCHES * BATCH_SIZE;
            if (show_search_box && total_size > max_size)  {
                picker.set('error',
                    'Too many matches. Please try to narrow your search.');
                // Display a single empty result item so that the picker
                // doesn't say that no items matched, which is contradictory.
                picker.set('results', [{}]);
                picker.set('batches', []);
            } else {
                picker.set('results', results);

                // Update the batches only if it's a new search.
                if (e.details[1] === undefined) {
                    var batches = [];
                    var stop = Math.ceil(total_size / BATCH_SIZE);
                    if (stop > 1) {
                        for (batch = 0; batch < stop; batch++) {
                            batches.push({
                                    name: batch+1,
                                    value: batch
                                });
                        }
                    }
                    picker.set('batches', batches);
                }
            }
        };

        // We can pass in a vocabulary name
        if (typeof vocabulary === 'string') {
            var success_handler = function (ignore, response, args) {
                var entry = Y.JSON.parse(response.responseText);
                var total_size = entry.total_size;
                var start = entry.start;
                var results = entry.entries;
                hide_temporary_spinner(config.temp_spinner);
                // If this was an automated (preemptive) search and the user
                // has not subsequently initiated their own search, display
                // the results of the search.
                if (user_has_searched !== automated_search) {
                    display_vocabulary(results, total_size, start);
                }
            };

            var failure_handler = function (ignore, response, args) {
                Y.log("Loading " + uri + " failed.");
                hide_temporary_spinner(config.temp_spinner);
                // If this was an automated (preemptive) search and the user
                // has subsequently initiated their own search, don't bother
                // showing an error message about something the user didn't
                // initiate and now doesn't care about.
                if (user_has_searched === automated_search) {
                    return;
                }
                var base_error =
                    "Sorry, something went wrong with your search.";
                if (response.status === 500) {
                    base_error +=
                        " We've recorded what happened, and we'll fix it " +
                        "as soon as possible.";
                } else if (response.status >= 502 && response.status <= 504) {
                    base_error +=
                        " Trying again in a couple of minutes might work.";
                }
                var oops_id = response.getResponseHeader('X-Lazr-OopsId');
                if (oops_id) {
                    base_error += ' (Error ID: ' + oops_id + ')';
                }
                picker.set('error', base_error);
                picker.set('search_mode', false);
            };


            var qs = '';
            qs = Y.lp.client.append_qs(qs, 'name', vocabulary);
            qs = Y.lp.client.append_qs(qs, 'search_text', search_text);
            if (Y.Lang.isValue(search_filter)) {
                qs = Y.lp.client.append_qs(
                    qs, 'search_filter', search_filter);
            }
            qs = Y.lp.client.append_qs(qs, 'batch', BATCH_SIZE);
            qs = Y.lp.client.append_qs(qs, 'start', start);

            // The uri needs to be relative, so that the vocabulary
            // has the same context as the form. Some vocabularies
            // use the context to limit the results to the same project.

            var uri = '';
            if (Y.Lang.isValue(config.context)){
                uri += Y.lp.get_url_path(
                    config.context.get('web_link')) + '/';
            }
            uri += '@@+huge-vocabulary?' + qs;

            var yio = (config.yio !== undefined) ? config.yio : Y;
            yio.io(uri, {
                headers: {'Accept': 'application/json'},
                timeout: 20000,
                on: {
                    success: success_handler,
                    failure: failure_handler
                }
            });
        // Or we can pass in a vocabulary directly.
        } else {
            display_vocabulary(vocabulary, Y.Object.size(vocabulary), 1);
        }
    };

    picker.after(Y.lazr.picker.Picker.SEARCH, search_handler);

    picker.render();
    picker.hide();
    return picker;
};

}, "0.1", {"requires": [
    "io", "dom", "dump", "event", "lazr.activator", "json-parse",
    "lp.client", "lazr.picker", "lazr.person-picker"
    ]});
