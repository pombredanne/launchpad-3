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
 * @param {Object} config Object literal of config name/value pairs.
 *     config.header: a line of text at the top of the widget.
 *     config.step_title: overrides the subtitle.
 *     config.remove_button_text: Override the default 'Remove' text.
 *     config.null_display_value: Override the default 'None' text.
 *     config.show_remove_button: Should the remove button be shown?
 *         Defaults to false, should be a boolean.
 *     config.show_assign_me_botton: Should the 'assign me' button be shown?
 *         Defaults to false, should be a boolean.
 *     config.non_searchable_vocabulary: No search bar is shown, and the
 *         vocabulary is required to not implement IHugeVocabulary.  The
 *         vocabularies values are then offered in a batched way for
 *         selection.  Defaults to false.
 */
namespace.addPickerPatcher = function (
    vocabulary, resource_uri, attribute_name,
    content_box_id, config) {

    if (Y.UA.ie) {
        return;
    }

    var show_remove_button = false;
    var show_assign_me_button = false;
    var remove_button_text = 'Remove';
    var null_display_value = 'None';
    var non_searchable_vocabulary = false;
    var full_resource_uri = LP.client.get_absolute_uri(resource_uri);
    var current_context_uri = LP.client.cache['context']['self_link'];
    var editing_main_context = (full_resource_uri == current_context_uri);

    if (config !== undefined) {
        if (config.remove_button_text) {
            remove_button_text = config.remove_button_text;
        }

        if (config.null_display_value) {
            null_display_value = config.null_display_value;
        }

        if (config.show_remove_button) {
            show_remove_button = config.show_remove_button;
        }

        if (config.show_assign_me_button) {
            show_assign_me_button = config.show_assign_me_button;
        }

        if (config.non_searchable_vocabulary) {
            non_searchable_vocabulary = config.non_searchable_vocabulary;
        }
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

    var show_hide_buttons = function () {
        var link = content_box.one('.yui3-activator-data-box a');
        if (remove_button) {
            if (link === null || !show_remove_button) {
                remove_button.addClass('yui-picker-hidden');
            } else {
                remove_button.removeClass('yui-picker-hidden');
            }
        }

        if (assign_me_button) {
            if (link !== null
                && link.get('href').indexOf(LP.client.links.me + '/') != -1) {
                assign_me_button.addClass('yui-picker-hidden');
            } else {
                assign_me_button.removeClass('yui-picker-hidden');
            }
        }
    };

    var save = function (picker_result) {
        activator.renderProcessing();
        var success_handler = function (entry) {
            // XXX mars 2009-12-1
            // The approach we use here is deprecated.  Instead of requesting
            // the entire entity we should only request the fields we need.
            // Then most of this code can go away. See bug #490826.
            var success_message_node = null;
            var xhtml = Y.Node.create(entry);
            var current_field = null;
            var content_uri_has_changed = false;
            // The entry is an XHTML document with a <dl> node at the root.  We
            // want to process each <dt><dd> tag pair under that root.
            xhtml.all('dl *').each(function(element) {
                if (element.get('tagName') == 'DT') {
                    current_field = element.get('innerHTML');
                } else if (element.get('tagName') == 'DD') {
                    if (current_field == attribute_name) {
                        // The field value is found
                        success_message_node = Y.Node.create('<span></span>');
                        rendered_content = element.get('innerHTML');
                        success_message_node.set('innerHTML', rendered_content);
                    } else if (current_field == 'self_link') {
                        picker._resource_uri = element.get('innerHTML');
                        content_uri_has_changed = (
                            resource_uri != picker._resource_uri);
                    }
                }
            });
            activator.renderSuccess(success_message_node);
            show_hide_buttons();
            // If the resource_uri of the picker no longer matches
            if (editing_main_context && content_uri_has_changed) {
              // XXX Tim Penhey 2011-01-18 Bug #316694:
              // This is a slightly nasty hack that saves us from the need
              // to have a more established way of getting the web URL of
              // an API object. Once such a solution is available we should
              // fix this.
              var new_url = picker._resource_uri.replace('/api/devel', '');
              window.location = new_url;
            }
        };

        var patch_payload = {};
        patch_payload[attribute_name] = LP.client.get_absolute_uri(
            picker_result.api_uri);

        var client = new LP.client.Launchpad();
        client.patch(picker._resource_uri, patch_payload, {
            accept: 'application/xhtml+xml',
            on: {
                success: success_handler,
                failure: failure_handler
            }
        });
    };

    var assign_me = function () {
        picker.hide();
        save({
            image: '/@@/person',
            title: 'Me',
            api_uri: LP.client.links.me
        });
    };

    var remove = function () {
        picker.hide();
        activator.renderProcessing();
        var success_handler = function (entry) {
            activator.renderSuccess(Y.Node.create(null_display_value));
            show_hide_buttons();
        };

        var patch_payload = {};
        patch_payload[attribute_name] = null;

        var client = new LP.client.Launchpad();
        // Use picker._resource_uri, since it might have been changed
        // from the outside after the widget has already been initialized.
        client.patch(picker._resource_uri, patch_payload, {
            on: {
                success: success_handler,
                failure: failure_handler
            }
        });
    };

    config.save = save;
    var picker = namespace.create(vocabulary, config);
    picker._resource_uri = resource_uri;
    var extra_buttons = Y.Node.create(
        '<div style="text-align: center; height: 3em; ' +
        'white-space: nowrap"/>');
    var remove_button, assign_me_button;
    if (show_remove_button) {
        remove_button = Y.Node.create(
            '<a class="yui-picker-remove-button bg-image" ' +
            'href="javascript:void(0)" ' +
            'style="background-image: url(/@@/remove); padding-right: 1em">' +
            remove_button_text + '</a>');
        remove_button.on('click', remove);
        extra_buttons.appendChild(remove_button);
    }
    if (show_assign_me_button) {
        assign_me_button = Y.Node.create(
            '<a class="yui-picker-assign-me-button bg-image" ' +
            'href="javascript:void(0)" ' +
            'style="background-image: url(/@@/person)">' +
            'Assign Me</a>');
        assign_me_button.on('click', assign_me);
        extra_buttons.appendChild(assign_me_button);
    }
    picker.set('footer_slot', extra_buttons);

    activator.subscribe('act', function (e) {
        if (non_searchable_vocabulary) {
          picker.set('min_search_chars', 0);
          picker.fire('search', '');
          picker.get('contentBox').one('.yui3-picker-search-box').addClass('unseen');
        }
        picker.show();
    });
    activator.render();

    show_hide_buttons();

    return picker;
};

/**
  * Creates a picker widget that has already been rendered and hidden.
  *
  * @requires dom, dump, lazr.overlay, lazr.picker
  * @method create
  * @param {String} vocabulary Name of the vocabulary to query.
  * @param {Object} config Optional Object literal of config name/value pairs.
  *                        config.header is a line of text at the top of
  *                        the widget.
  *                        config.step_title overrides the subtitle.
  *                        config.save is a Function (optional) which takes
  *                        a single string argument.
  */
namespace.create = function (vocabulary, config) {
    if (Y.UA.ie) {
        return;
    }

    if (config !== undefined) {
        var header = 'Choose an item.';
        if (config.header !== undefined) {
            header = config.header;
        }

        var step_title = "Enter search terms";
        if (config.step_title !== undefined) {
            step_title = config.step_title;
        }
    }

    if (typeof vocabulary != 'string') {
        throw new TypeError(
            "vocabulary argument for Y.lp.picker.create() must be a " +
            "string: " + vocabulary);
    }

    var new_config = Y.merge(config, {
        align: {
            points: [Y.WidgetPositionAlign.CC,
                     Y.WidgetPositionAlign.CC]
        },
        progressbar: true,
        progress: 100,
        headerContent: "<h2>" + header + "</h2>",
        steptitle: step_title,
        zIndex: 1000,
        visible: false
        });
    var picker = new Y.lazr.Picker(new_config);

    picker.subscribe('save', function (e) {
        Y.log('Got save event.');
        if (Y.Lang.isFunction(config.save)) {
            config.save(e.details[Y.lazr.Picker.SAVE_RESULT]);
        }
    });

    picker.subscribe('cancel', function (e) {
        Y.log('Got cancel event.');
    });

    // Search for results, create batches and update the display.
    // in the widget.
    var search_handler = function (e) {
        Y.log('Got search event:' + Y.dump(e.details));
        var search_text = e.details[0];
        var selected_batch = e.details[1] || 0;
        var start = BATCH_SIZE * selected_batch;
        var client = new LP.client.Launchpad();

        var success_handler = function (ignore, response, args) {
            var entry = Y.JSON.parse(response.responseText);
            var total_size = entry.total_size;
            var start = entry.start;
            var results = entry.entries;

            if (total_size > (MAX_BATCHES * BATCH_SIZE))  {
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
                        for (var i=0; i<stop; i++) {
                            batches.push({
                                    name: i+1,
                                    value: i
                                });
                        }
                    }

                    picker.set('batches', batches);
                }
            }
        };

        var qs = '';
        qs = LP.client.append_qs(qs, 'name', vocabulary);
        qs = LP.client.append_qs(qs, 'search_text', search_text);
        qs = LP.client.append_qs(qs, 'batch', BATCH_SIZE);
        qs = LP.client.append_qs(qs, 'start', start);

        // The uri needs to be relative, so that the vocabulary
        // has the same context as the form. Some vocabularies
        // use the context to limit the results to the same project.
        var uri = '@@+huge-vocabulary?' + qs;

        Y.io(uri, {
            headers: {'Accept': 'application/json'},
            timeout: 20000,
            on: {
                success: success_handler,
                failure: function (arg) {
                    picker.set('error', 'Loading results failed.');
                    picker.set('search_mode', false);
                    Y.log("Loading " + uri + " failed.");
                }
            }
        });
    };

    picker.after('search', search_handler);

    picker.render();
    picker.hide();
    return picker;
};

}, "0.1", {"requires": [
    "io", "dom", "dump", "lazr.picker", "lazr.activator", "json-parse",
    "lp.client.helpers"
    ]});
