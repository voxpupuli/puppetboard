{%- import '_macros.html' as macros -%}
{
  "draw": {{draw}},
  "recordsTotal": {{total}},
  "recordsFiltered": {{total_filtered}},
  "data": [
    {% for report in reports -%}
      {%- if report_flag %},{%- endif %}
      {%- set report_flag = True -%}
      [
        {%- for column in columns -%}
          {%- if column_flag %},{%- endif -%}
          {%- set column_flag = True -%}
          {%- if column.type == 'datetime' -%}
            "<span rel=\"utctimestamp\">{{ report[column.attr] }}</span>"
          {%- elif column.type == 'status' -%}
            {% filter jsonprint -%}
              {{ macros.status_counts(status=report.status, node_name=report.node, events=report_event_counts[report.hash_], report_hash=report.hash_, current_env=current_env) }}
            {%- endfilter %}
          {%- elif column.type == 'node' -%}
            {% filter jsonprint %}<a href="{{url_for('node', env=current_env, node_name=report.node)}}">{{ report.node }}</a>{% endfilter %}
          {%- else -%}
            {{ report[column.attr] | jsonprint }}
          {%- endif -%}
        {%- endfor -%}
      ]
    {% endfor %}
  ]
}
