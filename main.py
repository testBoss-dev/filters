from flask import Flask, request, jsonify, send_file
import requests
import os
import uuid
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

DEEPar_API_URL = "https://filters-production.up.railway.app"  # Example endpoint, adjust if needed
DEEPar_LICENSE_KEY = os.getenv("d9d76c4291a877dfd04c83997cfe75f64e799ae46d3b85acbccf07efb1f1bd6693d01aa488cef941")  # Store in Railway environment variables

# Ensure uploads & outputs directory exists
os.makedirs("uploads", exist_ok=True)
os.makedirs("outputs", exist_ok=True)

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "DeepAR API server running"})

@app.route("/process", methods=["POST"])
def process_image():
    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    image_file = request.files["image"]
    filter_name = request.form.get("filter", "default_filter")  # Pass filter name in request
    image_path = os.path.join("uploads", f"{uuid.uuid4()}.jpg")
    image_file.save(image_path)

    # Send request to DeepAR Web API
    try:
        with open(image_path, "rb") as img:
            response = requests.post(
                DEEPar_API_URL,
                headers={
                    "x-api-key": DEEPar_LICENSE_KEY
                },
                data={
                    "effect": filter_name
                },
                files={
                    "image": img
                }
            )

        if response.status_code != 200:
            return jsonify({"error": "DeepAR API error", "details": response.text}), 500

        # Save processed image
        output_path = os.path.join("outputs", f"{uuid.uuid4()}.jpg")
        with open(output_path, "wb") as out:
            out.write(response.content)

        return send_file(output_path, mimetype="image/jpeg")

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
