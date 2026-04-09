import json
from pathlib import Path
from flask import (
    Flask,
    render_template_string,
    request,
    send_from_directory,
    redirect,
    url_for,
)

app = Flask(__name__)
# Use absolute path for output directory
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
FEEDBACK_FILE = OUTPUT_DIR / "feedback.json"


def load_feedback():
    if FEEDBACK_FILE.exists():
        with open(FEEDBACK_FILE, "r") as f:
            return json.load(f)
    return {}


def save_feedback(feedback):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(FEEDBACK_FILE, "w") as f:
        json.dump(feedback, f, indent=4)


INDEX_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Map Georeferencing Review</title>
    <style>
        body { font-family: sans-serif; margin: 20px; background: #f0f0f0; }
        .report-list { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .report-item { margin-bottom: 10px; display: flex; align-items: center; justify-content: space-between; padding: 10px; border-bottom: 1px solid #eee; }
        .status-badge { padding: 4px 8px; border-radius: 4px; font-size: 0.8em; }
        .status-done { background: #d4edda; color: #155724; }
        .status-pending { background: #fff3cd; color: #856404; }
        a { color: #007bff; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <h1>Map Georeferencing Review</h1>
    <div class="report-list">
        {% for report in reports %}
        <div class="report-item">
            <span><a href="{{ url_for('view_report', report_name=report.name) }}">{{ report.display_name }}</a></span>
            {% if report.name in feedback %}
            <span class="status-badge status-done">Reviewed</span>
            {% else %}
            <span class="status-badge status-pending">Pending Review</span>
            {% endif %}
        </div>
        {% endfor %}
    </div>
</body>
</html>
"""

REPORT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Review: {{ display_name }}</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        body { font-family: sans-serif; margin: 20px; background: #f0f0f0; display: flex; flex-direction: column; height: 100vh; }
        .header { margin-bottom: 20px; }
        .content { display: grid; grid-template-columns: 1fr 400px; gap: 20px; flex: 1; min-height: 0; }
        .main-view { display: flex; flex-direction: column; gap: 20px; min-height: 0; }
        .corners { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
        .corner-box { background: white; padding: 5px; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border: 2px solid transparent; }
        .corner-box.selected { border-color: #007bff; }
        .corner-box img { width: 100%; height: auto; display: block; }
        .corner-label { font-size: 0.8em; font-weight: bold; margin-bottom: 2px; }
        #map { height: 400px; width: 100%; border-radius: 4px; }
        .feedback-panel { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); overflow-y: auto; }
        .feedback-form h3 { margin-top: 0; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; font-weight: bold; }
        .radio-group { display: flex; gap: 20px; }
        .btn-submit { background: #28a745; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; width: 100%; font-size: 1em; }
        .btn-back { display: inline-block; margin-bottom: 10px; color: #6c757d; text-decoration: none; }
    </style>
</head>
<body>
    <div class="header">
        <a href="{{ url_for('index') }}" class="btn-back">&larr; Back to list</a>
        <h1>Review: {{ display_name }}</h1>
    </div>

    <div class="content">
        <div class="main-view">
            <div id="map"></div>
            <div class="corners">
                <div class="corner-box">
                    <div class="corner-label">Top Left</div>
                    <img src="{{ url_for('serve_report_file', report_name=report_name, filename='corner_top_left.jpg') }}" />
                </div>
                <div class="corner-box">
                    <div class="corner-label">Top Right</div>
                    <img src="{{ url_for('serve_report_file', report_name=report_name, filename='corner_top_right.jpg') }}" />
                </div>
                <div class="corner-box">
                    <div class="corner-label">Bottom Left</div>
                    <img src="{{ url_for('serve_report_file', report_name=report_name, filename='corner_bottom_left.jpg') }}" />
                </div>
                <div class="corner-box">
                    <div class="corner-label">Bottom Right</div>
                    <img src="{{ url_for('serve_report_file', report_name=report_name, filename='corner_bottom_right.jpg') }}" />
                </div>
            </div>
        </div>

        <div class="feedback-panel">
            <form class="feedback-form" action="{{ url_for('submit_feedback', report_name=report_name) }}" method="POST">
                <h3>Quality Check</h3>
                
                <div class="form-group">
                    <label>Is the overall crop correct?</label>
                    <div class="radio-group">
                        <label><input type="radio" name="overall_crop" value="yes" {% if current_feedback.overall_crop == 'yes' %}checked{% endif %} required> Yes</label>
                        <label><input type="radio" name="overall_crop" value="no" {% if current_feedback.overall_crop == 'no' %}checked{% endif %}> No</label>
                    </div>
                </div>

                <h4>Corner Accuracy</h4>
                {% for corner in ["top_left", "top_right", "bottom_left", "bottom_right"] %}
                <div class="form-group">
                    <label>{{ corner.replace('_', ' ').capitalize() }} selected correctly?</label>
                    <div class="radio-group">
                        <label><input type="radio" name="corner_{{ corner }}" value="yes" {% if current_feedback['corner_' + corner] == 'yes' %}checked{% endif %} required> Yes</label>
                        <label><input type="radio" name="corner_{{ corner }}" value="no" {% if current_feedback['corner_' + corner] == 'no' %}checked{% endif %}> No</label>
                    </div>
                </div>
                {% endfor %}

                <div class="form-group">
                    <label>Notes (optional):</label>
                    <textarea name="notes" style="width: 100%; height: 80px;">{{ current_feedback.notes or '' }}</textarea>
                </div>

                <button type="submit" class="btn-submit">Save Feedback</button>
            </form>
        </div>
    </div>

    <script>
        // Load map config from the actual index.html if possible, or just parse from server
        // Here we'll just hardcode or fetch the overview image
        var map = L.map('map');
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap contributors'
        }).addTo(map);

        // Fetch coordinates from the original report index.html (we'll simplified this for now)
        // Ideally the visualizer outputs a JSON as well.
        // For now, let's just show the overview if it exists.
        var imageUrl = "{{ url_for('serve_report_file', report_name=report_name, filename='overview.jpg') }}";
        // We need the bounds. Let's assume the server passed them or we extracted them.
        {% if bounds %}
        var imageBounds = [[{{ bounds[1] }}, {{ bounds[0] }}], [{{ bounds[3] }}, {{ bounds[2] }}]];
        L.imageOverlay(imageUrl, imageBounds, { opacity: 0.5 }).addTo(map);
        map.fitBounds(imageBounds);
        {% else %}
        // Fallback or centered
        map.setView([35, 105], 4);
        {% endif %}
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    reports = []
    if OUTPUT_DIR.exists():
        for d in sorted(OUTPUT_DIR.iterdir()):
            if d.is_dir() and d.name.startswith("report_"):
                reports.append(
                    {"name": d.name, "display_name": d.name.replace("report_", "")}
                )
    feedback = load_feedback()
    return render_template_string(INDEX_TEMPLATE, reports=reports, feedback=feedback)


@app.route("/report/<report_name>/")
def view_report(report_name):
    feedback = load_feedback()
    current_feedback = feedback.get(report_name, {})

    report_path = OUTPUT_DIR / report_name / "index.html"
    if not report_path.exists():
        return f"Report not found: {report_name}", 404

    content = report_path.read_text()

    # Feedback form to inject
    feedback_html = f"""
    <div id="feedback-panel" style="background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-top: 20px;">
        <form action="{
        url_for("submit_feedback", report_name=report_name)
    }" method="POST">
            <h3>Quality Check</h3>
            <div style="margin-bottom: 15px;">
                <label style="display: block; font-weight: bold;">Is the overall crop correct?</label>
                <label><input type="radio" name="overall_crop" value="yes" {
        "checked" if current_feedback.get("overall_crop") == "yes" else ""
    } required> Yes</label>
                <label><input type="radio" name="overall_crop" value="no" {
        "checked" if current_feedback.get("overall_crop") == "no" else ""
    }> No</label>
            </div>
            <h4>Corner Accuracy</h4>
            {
        "".join(
            [
                f'''
            <div style="margin-bottom: 10px;">
                <label style="display: block;">{c.replace("_", " ").capitalize()} selected correctly?</label>
                <label><input type="radio" name="corner_{c}" value="yes" {'checked' if current_feedback.get('corner_' + c) == 'yes' else ''} required> Yes</label>
                <label><input type="radio" name="corner_{c}" value="no" {'checked' if current_feedback.get('corner_' + c) == 'no' else ''}> No</label>
            </div>'''
                for c in ["top_left", "top_right", "bottom_left", "bottom_right"]
            ]
        )
    }
            <div style="margin-bottom: 15px;">
                <label style="display: block; font-weight: bold;">Notes (optional):</label>
                <textarea name="notes" style="width: 100%; height: 80px;">{
        current_feedback.get("notes", "")
    }</textarea>
            </div>
            <button type="submit" style="background: #28a745; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; width: 100%; font-size: 1em;">Save Feedback</button>
        </form>
        <div style="margin-top: 10px;">
            <a href="{
        url_for("index")
    }" style="color: #6c757d; text-decoration: none;">&larr; Back to list</a>
        </div>
    </div>
    """

    # Inject before </body>
    if "</body>" in content:
        content = content.replace("</body>", f"{feedback_html}</body>")
    else:
        content += feedback_html

    return content


@app.route("/report/<report_name>/submit", methods=["POST"])
def submit_feedback(report_name):
    feedback = load_feedback()
    data = request.form.to_dict()
    feedback[report_name] = data
    save_feedback(feedback)
    return redirect(url_for("index"))


@app.route("/report/<report_name>/<filename>")
def serve_report_file(report_name, filename):
    return send_from_directory(str(OUTPUT_DIR / report_name), filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
