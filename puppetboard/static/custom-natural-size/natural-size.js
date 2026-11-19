/**
 * Custom DataTables sort plugin for human-readable size strings.
 * Handles values like "7.63 GiB", "512 MiB", "1.5 TiB", "2.00 GB", etc.
 * Converts all values to bytes for accurate cross-unit comparison.
 *
 *  @name Natural Size
 *  @summary Sort human-readable size strings by their byte value
 *
 *  @example
 *    $("#example").DataTable({
 *       columnDefs: [
 *         { "type": "natural-size", "targets": 1 }
 *       ]
 *    });
 */

jQuery.extend(jQuery.fn.dataTableExt.oSort, {
    "natural-size-pre": function (data) {
        // DataTables strips HTML before passing to sort functions.
        // Strip any remaining tags just in case, then trim whitespace.
        data = String(data).replace(/<[^>]*>/g, '').trim();

        var units = {
            'b':   1,
            'kb':  1024,
            'kib': 1024,
            'mb':  1024 * 1024,
            'mib': 1024 * 1024,
            'gb':  1024 * 1024 * 1024,
            'gib': 1024 * 1024 * 1024,
            'tb':  1024 * 1024 * 1024 * 1024,
            'tib': 1024 * 1024 * 1024 * 1024,
            'pb':  1024 * 1024 * 1024 * 1024 * 1024,
            'pib': 1024 * 1024 * 1024 * 1024 * 1024,
        };

        var match = data.match(/^([\d.]+)\s*([a-zA-Z]+)?$/);
        if (!match) return parseFloat(data) || 0;

        var value = parseFloat(match[1]);
        var unit  = (match[2] || 'b').toLowerCase();

        return value * (units[unit] || 1);
    },

    "natural-size-asc": function (a, b) {
        return a < b ? -1 : a > b ? 1 : 0;
    },

    "natural-size-desc": function (a, b) {
        return a < b ? 1 : a > b ? -1 : 0;
    }
});
