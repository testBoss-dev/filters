import os
import uuid
import asyncio
import base64
from flask import Flask, request, jsonify, send_file
from dotenv import load_dotenv
from pyppeteer import launch

load_dotenv()

# Safe directory creation: if 'uploads' or 'outputs' exist as files, remove them first
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
browser = None  # Global browser instance

async def init_browser():
    """Launch Pyppeteer browser once at startup."""
    global browser
    if browser is None:
        print("Launching headless browser...")
        browser = await launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage"
            ]
        )
        print("Browser launched.")

# Runs DeepAR filter using a Base64 data URL.
async def run_deepar(image_data_url, filter_name, output_path):
    page = await browser.newPage()
    
    # This function allows JS to send the final image back to Python
    async def save_processed_image(data_url):
        header, encoded = data_url.split(",", 1)
        data = base64.b64decode(encoded)
        with open(output_path, "wb") as f:
            f.write(data)

    await page.exposeFunction("saveProcessedImage", save_processed_image)
    
    # Load the local HTML template
    await page.goto(f"file://{os.path.abspath(HTML_TEMPLATE)}")

    # Call the JS function with the image data URL
    await page.evaluate(
        f'applyDeepARFilter("{image_data_url}", "{filter_name}")'
    )
    
    # Wait for the processing to complete
    await asyncio.sleep(5) 
    await page.close()

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "DeepAR API server running"})

@app.route("/process", methods=["POST"])
def process_image():
    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    filter_name = request.form.get("filter", "hair")
    image_file = request.files["image"]

    # Read image into memory and encode as Base64 Data URL
    image_bytes = image_file.read()
    encoded_string = base64.b64encode(image_bytes).decode('utf-8')
    mime_type = image_file.mimetype
    image_data_url = f"data:{mime_type};base64,{encoded_string}"
    
    output_path = os.path.join("outputs", f"{uuid.uuid4()}.png")

    try:
        loop = asyncio.get_event_loop()
        # Pass the data URL, not a file path
        loop.run_until_complete(run_deepar(image_data_url, filter_name, output_path))
        
        if os.path.exists(output_path):
            return send_file(output_path, mimetype="image/png")
        else:
            return jsonify({"error": "Processing failed, output file not created."}), 500
            
    except Exception as e:
        print(f"Error during processing: {e}") # Log the actual error on the server
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_browser())
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)), debug=False)
