
import re

def extract_js():
    with open('temp_calc.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the last <script> block which contains the main logic
    # The file has: <script src="...dropzone..."></script>
    # Then <script> ... logic ... </script>
    # Then {% endblock %}

    # We look for the script tag that contains "Dropzone.autoDiscover = false;"
    start_marker = 'Dropzone.autoDiscover = false;'
    end_marker = '{% endblock %}'
    
    start_pos = content.find(start_marker)
    if start_pos == -1:
        print("Could not find start marker")
        return

    # Backtrack to the opening <script> tag
    script_start = content.rfind('<script>', 0, start_pos)
    
    # Find the end of that script tag
    script_end = content.find('</script>', start_pos)
    
    if script_start == -1 or script_end == -1:
        print("Could not find script tags")
        return

    js_content = content[start_pos:script_end] # Start from the actual code, excluding <script>
    
    # We want to include the lines before Dropzone.autoDiscover too if they are inside the script?
    # Actually, Dropzone.autoDiscover = false; is likely the first line of code.
    # Let's verify with view_file output.
    # 1559: <script>
    # 1560:     Dropzone.autoDiscover = false;
    
    # So taking from start_pos is correct (it starts at "Dropzone...")
    
    with open('app/static/js/calculator.js', 'w', encoding='utf-8') as f:
        f.write(js_content)
    
    print("JS extracted successfully")

if __name__ == '__main__':
    extract_js()
