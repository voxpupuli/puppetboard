{%- import '_macros.html' as macros -%}
{
  "draw": {{draw}},
  "recordsTotal": {{total}},
  "recordsFiltered": {{total_filtered}},
  "data": [
    {% for node in nodes -%}
      {%- if flag %},{%- endif %}
      {%- set flag = True -%}
      [
        {%- for column in columns -%}
          {%- if column_flag %},{%- endif -%}
          {%- set column_flag = True -%}
          {%- if column.type == 'datetime' -%}
            {%- if column.name == "Catalog" -%}
              "<a rel=\"utctimestamp\" href=\"{{ url_for('catalog_node', env=current_env, node_name=node.name) }}\">{{node.catalog_timestamp}}</a>"
            {%- elif column.name == "Report" -%}
              {%- if node.report_timestamp -%}
                "<a href=\"{{ url_for('report', env=current_env, node_name=node.name, report_id=node.latest_report_hash) }}\" rel=\"utctimestamp\">{{ node.report_timestamp }}</a>"
              {%- else -%}
                "<i class=\"large darkblue ban icon\"></i>"
              {%- endif -%}
            {%- elif column.name == "" -%}
              {% if node.report_timestamp %}
                "<a title=\"Reports\" href=\"{{ url_for('reports', env=current_env, node_name=node.name) }}\"><i class=\"large darkblue book icon\"></i></a>"
              {%- else -%}
                ""
              {% endif %}
            {%- else -%}
              "{{ report[column.attr] }}"
            {%- endif -%}
          {%- elif column.type == 'status' -%}
            {% filter jsonprint -%}
                {{ macros.report_status(status=node.status, report=node.report, unreported_time=node.unreported_time, current_env=current_env) }}
            {%- endfilter %}
          {%- elif column.type == 'node' -%}
            {% filter jsonprint %}<a href="{{ url_for('node', env=current_env, node_name=node.name) }}">{{ node.name }}</a>{% endfilter %}
          {%- else -%}
            {{ report[column.attr] | jsonprint }}
          {%- endif -%}
        {%- endfor -%}
      ]
    {% endfor %}
  ]
}
