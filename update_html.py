
import os

def update_html():
    file_path = 'app/templates/calculator.html'
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Find the start of the extra_js block
    start_index = -1
    for i, line in enumerate(lines):
        if '{% block extra_js %}' in line:
            start_index = i
            break
    
    if start_index == -1:
        print("Could not find {% block extra_js %}")
        return

    # We want to keep the Dropzone script include if it's there
    # Usually it's the next line
    # 1557: {% block extra_js %}
    # 1558: <script src="https://unpkg.com/dropzone@5/dist/min/dropzone.min.js"></script>
    
    # We will slice up to start_index + 2 (inclusive of dropzone script)
    # But let's verify line content
    
    new_lines = lines[:start_index + 1] # Includes {% block extra_js %}
    
    # Add Dropzone script if not already in the slice (it should be next)
    # Actually, let's just rewrite the block content entirely to be safe
    
    new_content = [
        '<script src="https://unpkg.com/dropzone@5/dist/min/dropzone.min.js"></script>\n',
        '<!-- Tabulator for data grid -->\n',
        '<link href="https://unpkg.com/tabulator-tables@5.5.0/dist/css/tabulator.min.css" rel="stylesheet">\n',
        '<script type="text/javascript" src="https://unpkg.com/tabulator-tables@5.5.0/dist/js/tabulator.min.js"></script>\n',
        '\n',
        '<script>\n',
        '    window.CalculatorConfig = {\n',
        '        uploadUrl: "{{ url_for(\'calculator.upload_excel\') }}",\n',
        '        getSheetsUrl: "{{ url_for(\'calculator.get_excel_sheets\') }}",\n',
        '        getDhis2DeUrl: "{{ url_for(\'calculator.get_dhis2_data_elements\') }}",\n',
        '        urls: {\n',
        '            preview: "{{ url_for(\'calculator.preview_json\') }}"\n',
        '        }\n',
        '    };\n',
        '</script>\n',
        '<script src="{{ url_for(\'static\', filename=\'js/calculator.js\') }}?v={{ range(1, 10000) | random }}"></script>\n',
        '{% endblock %}\n'
    ]
    
    final_lines = new_lines + new_content
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(final_lines)
    
    print("calculator.html updated successfully")

if __name__ == '__main__':
    update_html()
