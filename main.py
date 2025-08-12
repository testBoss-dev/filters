import os
import asyncio
import uuid
import base64
from flask import Flask, request, send_file
from pyppeteer import launch

app = Flask(__name__)

# ================== Function to Save Image ==================
def save_image(data_url, output_path):
    header, encoded = data_url.split(",", 1)
    data = base64.b64decode(encoded)
    with open(output_path, "wb") as f:
        f.write(data)

# ================== DeepAR Processing ==================
async def run_deepar(input_path, output_path, filter_name):
    browser = await launch(
        headless=True,
        args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
    )
    page = await browser.newPage()

    # Expose Python save function to JS
    await page.exposeFunction("nodeSaveImage", lambda data_url: save_image(data_url, output_path))

    # Load DeepAR HTML template
    await page.goto(f"file://{os.getcwd()}/deepar_filter.html")

    # Run JS function inside HTML to apply filter
    await page.evaluate(f"""
        applyDeepARFilter("{input_path}", "{filter_name}")
            .then(dataUrl => nodeSaveImage(dataUrl));
    """)

    await browser.close()

# ================== API Endpoint ==================
@app.route("/apply-filter", methods=["POST"])
def apply_filter():
    if "image" not in request.files:
        return {"error": "No image uploaded"}, 400

    image_file = request.files["image"]
    filter_name = request.form.get("filter", "hair")  # default filter

    # Ensure directories exist
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("outputs", exist_ok=True)

    # Save uploaded file
    filename = f"{uuid.uuid4()}.png"
    input_path = os.path.abspath(os.path.join("uploads", filename))
    output_path = os.path.abspath(os.path.join("outputs", filename))
    image_file.save(input_path)

    # Process with DeepAR
    asyncio.get_event_loop().run_until_complete(
        run_deepar(input_path, output_path, filter_name)
    )

    return send_file(output_path, mimetype="image/png")

# ================== Run Server ==================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
