{%- import '_macros.html' as macros -%}
{
  "draw": {{draw}},
  "recordsTotal": {{total}},
  "recordsFiltered": {{total_filtered}},
  "data": [
    {%- set report_flag = false -%}
    {% for report in reports -%}
      {%- if not loop.first %},{%- endif -%}
      [
        {%- set column_flag = false -%}
        {%- for column in columns -%}
          {%- if not loop.first %},{%- endif -%}
          {%- if column.type == 'datetime' -%}
            "<span data-localise=\"{{ config.LOCALISE_TIMESTAMP|lower }}\">{{ report[column.attr] }}</span>"
          {%- elif column.type == 'status' -%}
            {% filter jsonprint -%}
              {{ macros.report_status(status=report.status, node_name=report.node, metrics=metrics[report.hash_], report_hash=report.hash_, current_env=current_env) }}
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
