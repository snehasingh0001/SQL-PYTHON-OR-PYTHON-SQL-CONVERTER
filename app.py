from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
from werkzeug.utils import secure_filename
import os
import json
from datetime import datetime
import re
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import xml.etree.ElementTree as ET
from converter import sql_to_python, python_to_sql, optimize_sql, optimize_python

app = Flask(__name__)
app.secret_key = 'your_secret_key'

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['HISTORY_FILE'] = 'conversion_history.json'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def save_history(entry):
    entry["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    history = []
    if os.path.exists(app.config['HISTORY_FILE']):
        with open(app.config['HISTORY_FILE'], 'r') as f:
            history = json.load(f)
    history.append(entry)
    with open(app.config['HISTORY_FILE'], 'w') as f:
        json.dump(history, f, indent=4)

def generate_pdf(text, output_path):
    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter
    margin = 40
    lines = text.split('\n')
    y = height - margin
    c.setFont("Courier", 10)
    for line in lines:
        if y < margin:
            c.showPage()
            y = height - margin
            c.setFont("Courier", 10)
        c.drawString(margin, y, line)
        y -= 12
    c.save()

def generate_xml(entry, output_path):
    root = ET.Element("Conversion")
    for key, val in entry.items():
        child = ET.SubElement(root, key)
        child.text = val
    tree = ET.ElementTree(root)
    tree.write(output_path, encoding='utf-8', xml_declaration=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
    direction = request.form['direction']
    input_type = request.form['input_type']
    download_format = request.form.get('download_format', 'txt')
    optimize = 'optimize' in request.form
    code = ""

    if input_type == 'manual':
        code = request.form['code']
    else:
        file = request.files['file']
        if file and file.filename:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            with open(filepath, 'r') as f:
                code = f.read()

    # Apply optimizations if selected
    optimized_code = code
    if direction == 'sql_to_python' and optimize:
        optimized_code = optimize_sql(code)
    elif direction == 'python_to_sql' and optimize:
        optimized_code = optimize_python(code)

    # Perform conversion
    if direction == 'sql_to_python':
        result = sql_to_python(optimized_code)
        ext = 'py' if download_format in ['py', 'txt'] else download_format
    else:
        result = python_to_sql(optimized_code)
        ext = 'sql' if download_format in ['sql', 'txt'] else download_format

    # Prepare filename
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    base_filename = f"converted_output_{timestamp}"
    output_filename = base_filename + '.' + ext
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)

    # Save output based on requested format
    if ext == 'pdf':
        generate_pdf(result, output_path)
    elif ext == 'json':
        entry = {
            "direction": direction.replace('_', ' ').title(),
            "input": optimized_code.strip(),
            "output": result.strip(),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(output_path, 'w') as f:
            json.dump(entry, f, indent=4)
    elif ext == 'xml':
        entry = {
            "direction": direction.replace('_', ' ').title(),
            "input": optimized_code.strip(),
            "output": result.strip(),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        generate_xml(entry, output_path)
    else:
        with open(output_path, 'w') as f:
            f.write(result)

    # Save to history
    save_history({
        "direction": direction.replace('_', ' ').title(),
        "input": optimized_code.strip(),
        "output": result.strip()
    })

    flash(f"Conversion done! Download your file: {output_filename}", "success")

    return render_template('index.html', result=result, download_file=output_filename)

@app.route('/history')
def history():
    history_data = []
    if os.path.exists(app.config['HISTORY_FILE']):
        with open(app.config['HISTORY_FILE'], 'r') as f:
            history_data = json.load(f)
    return render_template('history.html', history=history_data)
@app.route('/delete_selected', methods=['POST'])
def delete_selected():
    selected_ids = request.form.getlist('delete_ids')
    if os.path.exists(app.config['HISTORY_FILE']):
        with open(app.config['HISTORY_FILE'], 'r') as f:
            history = json.load(f)

        # Convert selected index values to integers and sort in reverse order
        selected_ids = sorted([int(i) for i in selected_ids], reverse=True)
        for idx in selected_ids:
            if 0 <= idx < len(history):
                del history[idx]

        with open(app.config['HISTORY_FILE'], 'w') as f:
            json.dump(history, f, indent=4)

    flash("Selected entries deleted successfully!", "warning")
    return redirect(url_for('history'))

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
@app.route('/clear_history', methods=['POST'])
def clear_history():
    if os.path.exists(app.config['HISTORY_FILE']):
        with open(app.config['HISTORY_FILE'], 'w') as f:
            json.dump([], f)
    flash("History cleared successfully!", "info")
    return redirect(url_for('history'))


if __name__ == '__main__':
    app.run(debug=True)