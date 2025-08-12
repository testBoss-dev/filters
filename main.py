import os
import uuid
import asyncio
from flask import Flask, request, jsonify, send_file
from dotenv import load_dotenv
from pyppeteer import launch
import base64

# Load .env
load_dotenv()

DEEPar_LICENSE_KEY = os.getenv("DEEPar_LICENSE_KEY", "your-license-key-here")

# Ensure directories exist safely
def ensure_dir(path):
    if os.path.exists(path):
        if not os.path.isdir(path):
            os.remove(path)  # remove file with same name
            os.makedirs(path)
    else:
        os.makedirs(path)

ensure_dir("uploads")
ensure_dir("outputs")

app = Flask(__name__)

HTML_TEMPLATE = "deepar_filter.html"

async def run_deepar(input_path, filter_name, output_path):
    browser = await launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-gpu",
            "--disable-dev-shm-usage"
        ]
    )
    page = await browser.newPage()

    # Expose a function to save image from JS
    async def node_save_image(data_url):
        header, encoded = data_url.split(",", 1)
        data = base64.b64decode(encoded)
        with open(output_path, "wb") as f:
            f.write(data)
    await page.exposeFunction("nodeSaveImage", node_save_image)

    # Load HTML template
    await page.goto(f"file://{os.path.abspath(HTML_TEMPLATE)}")

    # Call JS function in HTML to process image
    await page.evaluate(
        f'applyDeepARFilter("{os.path.abspath(input_path)}", "{filter_name}")'
    )

    await asyncio.sleep(2)  # allow rendering time
    await browser.close()

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "DeepAR API server running"})

@app.route("/process", methods=["POST"])
def process_image():
    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    filter_name = request.form.get("filter", "hair")
    image_file = request.files["image"]

    input_path = os.path.join("uploads", f"{uuid.uuid4()}.jpg")
    output_path = os.path.join("outputs", f"{uuid.uuid4()}.png")
    image_file.save(input_path)

    try:
        # Create a new event loop for this thread (fix for Thread-1 crash)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_deepar(input_path, filter_name, output_path))
        loop.close()

        return send_file(output_path, mimetype="image/png")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
