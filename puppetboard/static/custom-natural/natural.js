/**
* Created by Allan Jardine on Feb 17, 2023.
* Updated @ Feb 22, 2024
* Modified for the Puppetboard by ArthurWuTW.
*/

/**
 * Data can often be a complicated mix of numbers and letters (file names
 * are a common example) and sorting them in a natural manner is quite a
 * difficult problem.
 *
 * Fortunately the Javascript `localeCompare` method is now widely supported
 * and provides a natural sorting method we can use with DataTables.
 *
 *  @name Natural sorting
 *  @summary Sort data with a mix of numbers and letters _naturally_.
 *
 *  @example
 *   // Natural sorting
 *   new DataTable('#myTable',
 *       columnDefs: [
 *           { type: 'natural', target: 0 }
 *       ]
 *   } );
 *
 */


jQuery.extend(jQuery.fn.dataTableExt.oSort,{

    "natural-asc" : function (a, b) {
        return a.localeCompare(b, navigator.languages[0] || navigator.language, {
            numeric: true,
            ignorePunctuation: true,
        });
    },

    "natural-desc" : function (a, b) {
        return (a.localeCompare(b, navigator.languages[0] || navigator.language, { numeric: true, ignorePunctuation: true }) *
                -1);
    }
});
