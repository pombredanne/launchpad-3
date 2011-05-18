YUI.add('lp.app.multicheckbox', function(Y) {

var namespace = Y.namespace('lp.app.multicheckbox');

/* Add a multicheckbox widget which will PATCH a given attribute on
 * a given resource.
 *
 * @method addMultiCheckboxPatcher
 * @param {Array} items The items which to display as checkboxes.
 * @param {String} help_text The text to display beneath the checkboxes.
 * @param {String} resource_uri The object being modified.
 * @param {String} attribute_name The attribute on the resource being
 *                                modified.
 * @param {String} attribute_type The attribute type.
 *     "reference": the items are object references
 *     Other values are currently ignored.
 * @param {String} content_box_id
 * @param {Object} config Object literal of config name/value pairs.
 *     config.header: a line of text at the top of the widget.
 *     config.step_title: overrides the subtitle.
 */
namespace.addMultiCheckboxPatcher = function (
    items, help_text, resource_uri, attribute_name, attribute_type,
    content_box_id, config, client) {


    if (Y.UA.ie) {
        return;
    }

    // We may have been passed a mock client for testing but if not, create
    // a proper one.
    if (client === undefined)
        client = new Y.lp.client.Launchpad();

    var content_box = Y.one('#'+content_box_id);
    var result_node = Y.one('#'+content_box_id+'-items');
    var widget_node = Y.one('#'+attribute_name);
    var activator = new Y.lazr.activator.Activator(
        {contentBox: content_box, animationNode: widget_node});

    var failure_handler = function (id, response, args) {
        activator.renderFailure(
            Y.Node.create(
                '<div>' + response.statusText +
                    '<pre>' + response.responseText + '</pre>' +
                '</div>'));
    };

    // The function called to save the selected items.
    function save(editform, item_value_mapping) {
        var choice_nodes = Y.one('[id="'+attribute_name+'.items"]');
        var result = namespace.getSelectedItems(
            choice_nodes, item_value_mapping, attribute_type);
        activator.renderProcessing();
        var success_handler = function (entry) {
            result_node.setContent(entry.getHTML(attribute_name));
            activator.renderSuccess(result_node);
        };

        var patch_payload = {};
        patch_payload[attribute_name] = result;
        client.patch(editform._resource_uri, patch_payload, {
            accept: 'application/json;include=lp_html',
            on: {
                success: success_handler,
                failure: failure_handler
            }
        });
    }

    config.save = save;
    config.content_box_id = content_box_id;
    var editform = namespace.create(attribute_name, items, help_text, config);
    editform._resource_uri = resource_uri;
    var extra_buttons = Y.Node.create('<div class="extra-form-buttons"/>');
    activator.subscribe('act', function (e) {
        editform.show();
    });
    activator.render();
    return editform;
};


/**
  * Creates a multicheckbox widget that has already been rendered and hidden.
  *
  * @requires dom, lazr.activator, lazr.overlay
  * @method create
  * @param {String} attribute_name The attribute on the resource being
  *                                modified.
  * @param {Array} items Items for which to create checkbox elements.
  * @param {String} help_text text display below the checkboxes.
  * @param {Object} config Optional Object literal of config name/value pairs.
  *                        config.header is a line of text at the top of
  *                        the widget.
  *                        config.save is a Function (optional) which takes
  *                        a single string argument.
  */
namespace.create = function (attribute_name, items, help_text, config) {
    if (Y.UA.ie) {
        return;
    }

    if (config !== undefined) {
        var header = 'Choose an item.';
        if (config.header !== undefined) {
            header = config.header;
        }
    }

    var new_config = Y.merge(config, {
        align: {
            points: [Y.WidgetPositionAlign.CC,
                     Y.WidgetPositionAlign.CC]
        },
        progressbar: true,
        progress: 100,
        headerContent: "<h2>" + header + "</h2>",
        centered: true,
        zIndex: 1000,
        visible: false
        });

    // We use a pretty overlay to display the checkboxes.
    var editform = new Y.lazr.PrettyOverlay(new_config);

    // The html for each checkbox.
    var CHECKBOX_TEMPLATE =
        ['<label style="{item_style}" for="{field_name}.{field_index}">',
        '<input id="{field_name}.{field_index}" ',
        'name="{field_name}.{field_index}" ',
        'class="checkboxType" type="checkbox" value="{field_value}" ',
        '{item_checked}>&nbsp;{field_text}</label>'].join("");

    var content = Y.Node.create("<div/>");
    var header_node = Y.Node.create(
        "<div class='yui3-lazr-formoverlay-form-header'/>");
    content.appendChild(header_node);
    var body = Y.Node.create("<div class='yui3-widget-bd'/>");

    // Set up the nodes for each checkbox.
    var choices_nodes = Y.Node.create('<ul id="'+attribute_name+'.items"/>');
    // A mapping from checkbox value attributes (data token) -> data values
    var item_value_mapping = {};
    Y.Array.each(items, function(data, i) {
        var checked_html = '';
        if (data.checked)
            checked_html = 'checked="checked"';
        var checkbox_html = Y.Lang.substitute(
            CHECKBOX_TEMPLATE,
            {field_name: "field."+attribute_name, field_index:i,
            field_value: data.token, field_text: Y.Escape.html(data.name),
            item_style: data.style, item_checked: checked_html});

        var choice_item = Y.Node.create("<li/>");
        choice_item.set("innerHTML", checkbox_html);
        choices_nodes.appendChild(choice_item);
        item_value_mapping[data.token] = data.value;
    }, this);
    body.appendChild(choices_nodes);
    content.appendChild(body);
    var help_node = Y.Node.create("<p class='formHelp'>"+help_text+"</p>");
    content.appendChild(help_node);
    editform.set('bodyContent', content);

    // We replace the default Close button (x) with our own save/cancel ones.
    var close_node = editform.get('boundingBox').one('div.close');
    var orig_close_button = close_node.one('a');
    orig_close_button.setAttribute('style', 'display: none');
    var save_button = Y.Node.create(
        '<button id="'+config.content_box_id+'-save" ' +
        'class="overlay-close-button lazr-pos lazr-btn">Ok</button>');
    var close_button = Y.Node.create(
        '<button class="overlay-close-button lazr-neg lazr-btn">Cancel' +
        '</button>');
    save_button.on('click', function(e) {
        e.halt();
        editform.hide();
        config.save(editform, item_value_mapping);
    });
    close_button.on('click', function(e) {
        e.halt();
        editform.fire('cancel');
    });
    close_node.appendChild(close_button);
    close_node.appendChild(save_button);
    editform.render();
    editform.hide();
    return editform;
};


/*
 * Return a list of the selected checkbox values.
 * Exposed via the namespace so it is accessible to tests.
 */
namespace.getSelectedItems = function(choice_nodes, item_value_mapping,
                                      attribute_type) {
    var result = [];
    choice_nodes.all('.checkboxType').each(function(item) {
        if (item.get("checked")) {
            var item_token = item.getAttribute("value");
            var item_value = item_value_mapping[item_token];
            var marshalled_value = marshall(item_value, attribute_type);
            result.push(marshalled_value);
        }
    });
    return result;
};


/*
 * Transform the selected value according to the attribute type we are editing
 */
function marshall(value, attribute_type) {
    switch (attribute_type) {
        case "reference":
            var item_value = Y.lp.client.normalize_uri(value);
            return Y.lp.client.get_absolute_uri(item_value);
        break;
        default:
            return value;
    }
}

}, "0.1", {"requires": [
    "dom", "escape", "lazr.overlay", "lazr.activator", "lp.client"
    ]});
