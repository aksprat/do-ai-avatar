import os
import csv
import uuid
import json
import secrets
import requests
from datetime import datetime, timezone
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    jsonify,
    send_file,
)
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "uploads")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB

LEADS_CSV = os.path.join(os.path.dirname(__file__), "leads.csv")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

DO_API_KEY = os.environ.get("DIGITALOCEAN_API_KEY", "")
DO_INFERENCE_BASE_URL = "https://inference.do-ai.run/v1/async-invoke"
MODEL_ID = "fal-ai/flux/schnell"

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


def init_csv():
    if not os.path.exists(LEADS_CSV):
        with open(LEADS_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["Name", "Email ID", "Company Name", "Designation", "Timestamp"]
            )


init_csv()


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def save_lead(name, email, company, designation):
    with open(LEADS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [name, email, company, designation, datetime.now(timezone.utc).isoformat()]
        )


def build_prompt(name):
    return (
        f"Create a stunning superhero avatar portrait of a tech innovator named {name} "
        f"conquering cloud challenges with DigitalOcean Serverless Inference. "
        f"The hero wears a futuristic high-tech suit in DigitalOcean's signature blue (#0069FF) "
        f"and teal (#00B4D8) colors with glowing circuit patterns. "
        f"A glowing DigitalOcean logo emblem is prominently featured on the chest. "
        f"The dynamic background shows a vibrant cloud cityscape with floating server nodes "
        f"and glowing data streams. The art style is cinematic comic-book with bold, vivid colors, "
        f"dramatic lighting, and heroic perspective. The character is depicted in a powerful, "
        f"confident pose. "
        f"Ultra-high quality, detailed, professional digital artwork."
    )


def start_avatar_generation(name):
    if not DO_API_KEY:
        raise ValueError(
            "DIGITALOCEAN_API_KEY environment variable is not set."
        )

    headers = {
        "Authorization": f"Bearer {DO_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model_id": MODEL_ID,
        "input": {
            "prompt": build_prompt(name),
            "image_size": "square_hd",
            "num_inference_steps": 4,
            "num_images": 1,
            "enable_safety_checker": True,
        },
    }

    response = requests.post(
        DO_INFERENCE_BASE_URL, headers=headers, json=payload, timeout=30
    )
    response.raise_for_status()
    return response.json()


def check_generation_status(request_id):
    if not DO_API_KEY:
        raise ValueError(
            "DIGITALOCEAN_API_KEY environment variable is not set."
        )

    headers = {
        "Authorization": f"Bearer {DO_API_KEY}",
        "Content-Type": "application/json",
    }

    response = requests.get(
        f"{DO_INFERENCE_BASE_URL}/{request_id}",
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    company = request.form.get("company", "").strip()
    designation = request.form.get("designation", "").strip()

    if not all([name, email, company, designation]):
        return render_template(
            "index.html", error="Please fill in all fields before generating your avatar."
        )

    # Save lead to CSV
    save_lead(name, email, company, designation)

    # Handle optional selfie upload
    selfie_filename = None
    if "photo" in request.files:
        photo = request.files["photo"]
        if photo and photo.filename and allowed_file(photo.filename):
            ext = photo.filename.rsplit(".", 1)[1].lower()
            selfie_filename = f"{uuid.uuid4()}.{ext}"
            photo.save(
                os.path.join(app.config["UPLOAD_FOLDER"], secure_filename(selfie_filename))
            )

    # Start avatar generation via DO Serverless Inference
    try:
        result = start_avatar_generation(name)
        request_id = result.get("request_id") or result.get("id") or result.get("requestId")
        if not request_id:
            raise ValueError(f"No request_id in API response: {json.dumps(result)}")
        return redirect(
            url_for("result_page", request_id=request_id, name=name)
        )
    except Exception as exc:
        return render_template(
            "index.html",
            error=f"Avatar generation could not be started: {exc}",
        )


@app.route("/result/<request_id>")
def result_page(request_id):
    name = request.args.get("name", "Hero")
    return render_template("result.html", request_id=request_id, name=name)


@app.route("/api/status/<request_id>")
def api_status(request_id):
    try:
        data = check_generation_status(request_id)
        return jsonify(data)
    except requests.HTTPError as exc:
        return jsonify({"error": str(exc)}), exc.response.status_code
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/leads/download")
def download_leads():
    """Download the collected leads as a CSV file."""
    admin_key = request.args.get("key", "")
    expected_key = os.environ.get("ADMIN_KEY", "")
    if expected_key and not secrets.compare_digest(admin_key, expected_key):
        return jsonify({"error": "Unauthorized"}), 401
    init_csv()
    return send_file(
        LEADS_CSV,
        mimetype="text/csv",
        as_attachment=True,
        download_name="leads.csv",
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
