$ = jQuery
$ ->
$('.nodes').tablesorter(
    headers:
        4:
            sorter: false
    sortList: [[1,0]]
)

$('.facts').tablesorter(
    sortList: [[0,0]]
)

$('.dashboard').tablesorter(
    headers:
        2:
            sorter: false
    sortList: [[0, 1]]
)

$('.catalog').tablesorter(
    sortList: [[0, 0]]
)

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
