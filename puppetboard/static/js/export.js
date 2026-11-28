(function () {
  function exportOptions(table) {
    return {
      columns: function (index) {
        const header = table.column(index).header();
        return table.column(index).visible() &&
          header.textContent.trim() !== '' && !$(header).hasClass('no-export');
      },
      orthogonal: 'export',
      modifier: {search: 'applied', order: 'applied', selected: null},
      format: {
        body: function (data, row, column) {
          if (data === null || data === undefined) return '';
          if (typeof data === 'object') return JSON.stringify(data);
          if ($(table.column(column).header()).hasClass('fact_value') ||
              table.table().node().id === 'query_table') return String(data);
          return $.fn.dataTable.Buttons.stripData(String(data), {
            stripHtml: true, stripNewlines: false, decodeEntities: true, trim: false
          }).trim();
        }
      },
      customizeData: function (data) {
        // Quoting CSV fields alone does not prevent spreadsheet formula execution.
        const escapeFormula = value => /^[\s]*[=+\-@]|^[\t\r]/.test(String(value)) ? "'" + value : value;
        data.header = data.header.map(escapeFormula);
        data.body = data.body.map(row => row.map(escapeFormula));
      }
    };
  }

  async function serverRows(table) {
    const params = table.ajax.params();
    if (!params) throw new Error('Wait for the table to finish loading and try again.');
    const request = $.extend(true, {}, params, {start: 0, length: 1000});
    const rows = [];
    let total;

    do {
      const response = await $.ajax({
        url: table.ajax.url(),
        data: request,
        dataType: 'json'
      });
      if (response.error) throw new Error(response.error);
      if (!Array.isArray(response.data) || !Number.isInteger(response.recordsFiltered) ||
          response.recordsFiltered < 0) {
        throw new Error('The server returned an invalid table response.');
      }
      if (total !== undefined && total !== response.recordsFiltered) {
        throw new Error('The data changed during export. Please try again.');
      }
      total = response.recordsFiltered;
      rows.push(...response.data);
      if (rows.length > total || (response.data.length === 0 && rows.length < total)) {
        throw new Error('The server returned incomplete table data. Please try again.');
      }
      request.start = rows.length;
    } while (rows.length < total);

    return rows;
  }

  $(document).on('init.dt.puppetboardExport', function (event, settings) {
    const table = new $.fn.dataTable.Api(settings);
    const element = $(table.table().node());
    if (element.hasClass('csv-export-copy')) return;

    const message = $('<div class="ui negative message" role="alert" hidden></div>');
    const buttons = new $.fn.dataTable.Buttons(table, {
      name: 'csv-export',
      buttons: [{
        extend: 'csvHtml5',
        text: 'Download as CSV',
        filename: 'Puppetboard_' + element.attr('id'),
        bom: true,
        header: true,
        exportOptions: exportOptions(table),
        action: async function (event, dt, node, config) {
          const button = this;
          let copy;
          let container;
          button.enable(false);
          message.prop('hidden', true);
          try {
            let source = dt;
            if (dt.page.info().serverSide) {
              const rows = await serverRows(dt);
              const initial = dt.init();
              container = $('<div hidden></div>').appendTo(document.body);
              const clone = $('<table class="csv-export-copy"></table>')
                .append($('<thead></thead>').append(
                  $('<tr></tr>').append($(dt.columns().header().toArray()).clone())
                )).appendTo(container);
              // Render server rows without replacing the live table or changing its paging/filter state.
              copy = clone.DataTable({
                data: rows,
                columns: initial.columns || null,
                columnDefs: initial.columnDefs || [],
                ordering: false,
                searching: false,
                deferRender: true,
                pageLength: 1,
                autoWidth: false,
                dom: 't'
              });
              source = copy;
            }
            $.fn.dataTable.ext.buttons.csvHtml5.action.call(button, event, source, node, config);
          } catch (error) {
            console.error('CSV export failed', error);
            message.text('CSV export failed: ' + (error.message || error.statusText || 'Request failed.'))
              .prop('hidden', false);
          } finally {
            if (copy) copy.destroy();
            if (container) container.remove();
            button.enable(true);
          }
        }
      }]
    });
    const controls = $('<div class="puppetboard-export-buttons"></div>')
      .append(buttons.container()).append(message)
      .insertBefore(table.table().container());
    table.on('destroy.dt.puppetboardExport', function () {
      controls.remove();
    });
  });
})();
