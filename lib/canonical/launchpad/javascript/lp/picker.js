YUI.add('lp.picker', function(Y) {

Y.log('loading lp.picker');

Y.namespace('lp.picker');

var BATCH_SIZE = 6;
var MAX_BATCHES = 20;

/* Add a picker widget which will PATCH a given attribute on
 * a given resource.
 *
 * @method addPickerPatcher
 * @param {String} vocabulary Name of the vocabulary to query.
 * @param {String} resource_uri The object being modified.
 * @param {String} attribute_uri_base Canonical URI prefix.
 * @param {String} attribute_name The attribute on the resource being
 *                                modified.
 * @param {String} content_box_id
 * @param {Object} config Object literal of config name/value pairs.
 *                        config.header is a line of text at the top of
 *                        the widget.
 *                        config.step_title overrides the subtitle.
 *                        description strings.
 */
Y.lp.picker.addPickerPatcher = function (
    vocabulary, resource_uri, attribute_uri_base, attribute_name,
    content_box_id, show_remove_button, show_assign_me_button, config) {

    if (Y.UA.ie) {
        return;
    }

    var remove_button_text = 'Remove';
    if (config.remove_button_text) {
        remove_button_text = config.remove_button_text;
    }

    var null_display_value = 'None';
    if (config.null_display_value) {
        null_display_value = config.null_display_value;
    }

    // LP.client won't insert 'api/beta' into an absolute url.
    var index = resource_uri.indexOf('//');
    if (index != -1) {
        index = resource_uri.indexOf('/', index+2);
        resource_uri = resource_uri.substring(index);
    }

    var content_box = Y.get('#' + content_box_id);

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
        var link = content_box.query('.yui-activator-data-box a');
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
            var node = Y.Node.create(
                '<span>' + entry.get('assignee_link') + '</span>');
            activator.renderSuccess(node);
            show_hide_buttons();
        };

        var patch_payload = {};
        patch_payload[attribute_name] = LP.client.get_absolute_uri(
            attribute_uri_base + picker_result.value);

        var client = new LP.client.Launchpad();
        client.patch(resource_uri, patch_payload, {
            accept: 'application/xhtml+xml',
            on: {
                success: success_handler,
                failure: failure_handler
            }
        });
    };

    var assign_me = function () {
        picker.hide();
        // Remove "/~" from the beginning of the name.
        var my_name = LP.client.links.me.substring(2);
        save({
            image: '/@@/person',
            title: 'Me',
            value: my_name
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
        client.patch(resource_uri, patch_payload, {
            on: {
                success: success_handler,
                failure: failure_handler
            }
        });
    };

    var picker = Y.lp.picker.create(vocabulary, save, config);
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
    picker.set('search_slot', extra_buttons);

    activator.subscribe('act', function (e) {
        picker.show();
    });
    activator.render();

    show_hide_buttons();
};

/**
  * Creates a picker widget that has already been rendered and hidden.
  *
  * @requires dom, dump, lazr.overlay, lazr.picker
  * @method create
  * @param {String} vocabulary Name of the vocabulary to query.
  * @param {Function} save Function which takes a single string argument.
  * @param {Object} config Object literal of config name/value pairs.
  *                        config.header is a line of text at the top of
  *                        the widget.
  *                        config.step_title overrides the subtitle.
  *                        description strings.
  */
Y.lp.picker.create = function (vocabulary, save, config) {
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

    var picker = new Y.Picker({
        align: {
            points: [Y.WidgetPositionExt.CC,
                        Y.WidgetPositionExt.CC]
        },
        progressbar: true,
        progress: 100,
        headerContent: "<h2>" + header + "</h2>",
        steptitle: step_title,
        zIndex: 1000
        });

    picker.subscribe('save', function (e) {
        Y.log('Got save event.');
        // Y.get() uses CSS3 selectors which don't work with ids containing
        // a period, so we have to use Y.DOM.byId().
        save(e.details[Y.Picker.SAVE_RESULT]);
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

        var uri = '/+huge-vocabulary?' + qs;

        Y.io(uri, {
            headers: {'Accept': 'application/json'},
            timeout: 20000,
            on: {
                success: success_handler,
                failure: function (arg) {
                    picker.set('error', 'Loading results failed.');
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

}, '0.1', {
requires: [
    'io', 'dom', 'dump', 'lazr.picker', 'lazr.activator', 'json-parse',
    'lp.client.helpers'
    ]});
