from flask import Flask, request, jsonify, render_template
from azure.storage.blob import BlobServiceClient
from werkzeug.utils import secure_filename
from datetime import datetime
import os

# --- Configuration ---
# These are read from environment variables (set in Colab or your terminal)
STORAGE_ACCOUNT_URL = os.getenv("STORAGE_ACCOUNT_URL")
CONTAINER_NAME = "lanternfly-images-ks2h6ji7"
AZURE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

# --- Create Blob Service Client ---
bsc = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
cc = bsc.get_container_client(CONTAINER_NAME)

# Create container if not exists (public-read)
try:
    cc.create_container(public_access="blob")
except Exception:
    pass  # already exists

# --- Flask App ---
app = Flask(__name__)

@app.post("/api/v1/upload")
def upload():
    try:
        f = request.files["file"]
        if not f:
            return jsonify(ok=False, error="No file provided"), 400

        # Allow only images
        if not f.mimetype.startswith("image/"):
            return jsonify(ok=False, error="Only image uploads allowed"), 400

        # Limit size to 10MB
        f.seek(0, os.SEEK_END)
        size = f.tell()
        f.seek(0)
        if size > 10 * 1024 * 1024:
            return jsonify(ok=False, error="File too large (max 10MB)"), 400

        # Sanitize + timestamp filename
        safe_name = secure_filename(f.filename)
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        blob_name = f"{timestamp}-{safe_name}"

        # Upload to Azure Blob Storage
        cc.upload_blob(blob_name, f, overwrite=True)

        blob_url = f"{cc.url}/{blob_name}"
        return jsonify(ok=True, url=blob_url)

    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


@app.get("/api/v1/gallery")
def gallery():
    try:
        blobs = cc.list_blobs()
        urls = [f"{cc.url}/{b.name}" for b in blobs]
        return jsonify(ok=True, gallery=urls)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


@app.get("/api/v1/health")
def health():
    return jsonify(ok=True), 200


@app.get("/")
def index():
    return render_template("index.html")  # optional — if you add a frontend later


if __name__ == "__main__":
    app.run(debug=True)

