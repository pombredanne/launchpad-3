/**
 * Copyright 2011 Canonical Ltd. This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Things that YUI3 really needs.
 *
 * @module lp
 * @submodule extras-dict
 */

YUI.add('lp.extras-dict', function(Y) {

Y.log('loading lp.extras-dict');

var namespace = Y.namespace("lp.extras"),
    isArray = Y.Lang.isArray;

/**
 * An object type that resembles Python's dict.
 *
 * This is *experimental*. It may be useful to have a dict-like type
 * in JavaScript, hence this, but it may turn out to be a distraction,
 * hence why it's in a separate module.
 *
 * @constructor
 * @param {Object} initial An optional object that will be copied (by
 *     being passed into Dict.update).
 */
var Dict = function(initial) {
    if (initial !== undefined) {
        this.update(initial);
    }
};

// Static members.
Y.mix(Dict, {

    /**
     * Creates a new dict with the given keys, with the value
     * defaulting to def.
     *
     * @static
     * @param {Array of String} keys
     * @param {Any} def
     * @return A new dict.
     */
    fromKeys: function(keys, def) {
        var dict = new Dict();
        Y.Array.each(keys, function(key) { dict[key] = def; });
        return dict;
    }

}, true);

// Prototype members.
Y.mix(Dict.prototype, {

    /**
     * Remove all items from this dict.
     *
     * @return This dict.
     */
    clear: function() {
        var del = function(key) { delete this[key]; };
        this.keys().forEach(del, this);
        return this;
    },

    /**
     * Make a shallow copy of this dict.
     *
     * @return A new dict.
     */
    copy: function() {
        return new Dict(this);
    },

    /**
     * Returns the value for the given key, or def if the key is not
     * present in this dict.
     *
     * @param {String} key
     */
    get: function(key, def) {
        return this.hasOwnProperty(key) ? this[key] : def;
    },

    /**
     * Returns true if the given key is present in this dict.
     *
     * @param {String} key
     */
    hasKey: function(key) {
        return this.hasOwnProperty(key);
    },

    /**
     * Returns an array of {key, value} items in this dict.
     */
    items: function() {
        return this.keys().map(function(key) {
            return {key: key, value: this[key]};
        }, this);
    },

    /**
     * Returns an array of keys in this dict.
     */
    keys: function() {
        return Y.Object.keys(this);
    },

    /**
     * Remove the given key (and value) from this dict, returning the
     * value. If key is not found, return def.
     *
     * @param {String} key
     * @param {Any} def The value to return if key is not found.
     */
    pop: function(key, def) {
        var value;
        if (this.hasOwnProperty(key)) {
            value = this[key];
            delete this[key];
            return value;
        }
        else {
            return def;
        }
    },

    /**
     * Remove any key+value from this dict, returning a {key, value}
     * object. Returns undefined if the dict is empty.
     */
    popItem: function() {
        var key, value;
        for (key in this) {
            if (this.hasOwnProperty(key)) {
                value = this[key];
                delete this[key];
                return {key: key, value: value};
            }
        }
        return undefined;
    },

    /**
     * If key is not found in this dict, set it to def, then return
     * the value corresponding to key.
     *
     * @param {String} key
     */
    setDefault: function(key, def) {
        if (this.hasOwnProperty(key)) {
            return this[key];
        }
        else {
            this[key] = def;
            return def;
        }
    },

    /**
     * Update the Dict in place.
     *
     * If source is an object, its *own* properties are copied. If
     * source is array-like, each entry should either be a {key,
     * value} object or a [key, value] array.
     *
     * @param {Object|Dict|Array} source
     * @return This dict.
     */
    update: function(source) {
        var key;
        if (isArray(source)) {
            Y.each(source, function(item) {
                if (isArray(item)) {
                    this[item[0]] = item[1];
                }
                else {
                    this[item.key] = item.value;
                }
            }, this);
        }
        else {
            for (key in source) {
                if (source.hasOwnProperty(key)) {
                    this[key] = source[key];
                }
            }
        }
        return this;
    },

    /**
     * Returns an array of values in this dict.
     */
    values: function() {
        return Y.Object.values(this);
    },

    /**
     * Returns true if this dict is empty, i.e. devoid of keys.
     */
    isEmpty: function() {
        return Y.Object.isEmpty(this);
    },

    /**
     * Compares this dict to another. Returns true only if they both
     * have the same keys and values (and no others).
     *
     * @param {Dict|Object} other The object to compare.
     */
    isSame: function(other) {
        var key, keys = Y.Object.keys(this),
            other_key, other_keys = Y.Object.keys(other);
        if (keys.length !== other_keys.length) {
            return false;
        }
        keys.sort(); other_keys.sort();
        while (keys.length > 0) {
            key = keys.pop(); other_key = other_keys.pop();
            if (key !== other_key || this[key] !== other[key]) {
                return false;
            }
        }
        return true;
    }

}, true);

// Exports.
namespace.Dict = Dict;

}, "0.1", {requires: ["yui-base"]});
