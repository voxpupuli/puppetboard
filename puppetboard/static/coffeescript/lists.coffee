$ = jQuery
$ ->
$('input.filter-list').parent('div').removeClass('hide')
$("input.filter-list").on "keyup", (e) ->
  rex = new RegExp($(this).val(), "i")

  $(".searchable li").hide()
  $(".searchable li").parent().parent().hide()
  $(".searchable li").filter( ->
    rex.test $(this).text()
  ).show()
  $(".searchable li").filter( ->
    rex.test $(this).text()
  ).parent().parent().show()

  if e.keyCode is 27
    $(e.currentTarget).val ""
    ev = $.Event("keyup")
    ev.keyCode = 13
    $(e.currentTarget).trigger(ev)
    e.currentTarget.blur()
