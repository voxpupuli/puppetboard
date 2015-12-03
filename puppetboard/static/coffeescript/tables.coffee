$ = jQuery
$ ->

if $('th.default-sort').data()
  $('table.sortable').tablesort().data('tablesort').sort($("th.default-sort"),"desc")

$('thead th.date').data 'sortBy', (th, td, tablesort) ->
  return moment.utc(td.text()).unix()

$('input.filter-table').parent('div').removeClass('hide')
$("input.filter-table").on "keyup", (e) ->
  rex = new RegExp($(this).val(), "i")

  $(".searchable tr").hide()
  $(".searchable tr").filter( ->
    rex.test $(this).text()
  ).show()

  if e.keyCode is 27
    $(e.currentTarget).val ""
    ev = $.Event("keyup")
    ev.keyCode = 13
    $(e.currentTarget).trigger(ev)
    e.currentTarget.blur()
