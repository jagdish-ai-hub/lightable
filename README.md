# LightTable Studio

A small Flask web app that turns a batch of images into a single PDF. Drag images into the page (or click to browse), preview and reorder-by-removing them, then hit **Generate PDF** to download the combined file.

## What's in this folder

```
lighttable-studio/
├── app.py              Flask app: serves the page, converts images to PDF
├── requirements.txt    Python packages this project needs
└── templates/
    └── index.html      The whole front end - HTML, CSS and JS in one file
```

The front end is intentionally a single file: `index.html` has its `<style>` and `<script>` inline instead of separate `style.css` / `script.js` files, so there's only one file to open when you want to change how the page looks or behaves.

## 1. Install Python

You need Python 3.9 or newer. Check what you have installed:

```
python3 --version
```

If that command isn't found, or shows a version older than 3.9, install Python from [python.org](https://www.python.org/downloads/) first.

## 2. Set up a virtual environment (recommended)

A virtual environment keeps this project's packages separate from everything else on your machine. From inside the `lighttable-studio` folder:

```
python3 -m venv venv
```

Activate it:

- **macOS / Linux:** `source venv/bin/activate`
- **Windows (PowerShell):** `venv\Scripts\Activate.ps1`

You'll know it worked because your terminal prompt will now start with `(venv)`. You'll need to run the activate command again each time you open a new terminal to work on this project.

## 3. Install the dependencies

With the virtual environment active:

```
pip install -r requirements.txt
```

This installs two packages:
- **Flask** — the web framework that serves the page and handles the upload
- **Pillow** — the image library that does the actual image-to-PDF conversion

## 4. Run the app

```
python app.py
```

You should see output ending in something like:

```
 * Running on http://127.0.0.1:5000
```

Open that address in your browser. You'll see the LightTable Studio upload page.

## 5. Use it

1. Drag images onto the dashed drop zone, or click it to open a file picker.
2. Thumbnails appear below as you add images — click the **×** on a thumbnail to remove it.
3. Click **Generate PDF**. Your browser downloads `converted.pdf`, with one page per image, in the order they were added.

Press **Ctrl+D** at any time to switch between light and dark themes.

## How the conversion works

When you click **Generate PDF**, the browser sends all the selected files to the `/convert` route in `app.py`. That route:

1. Checks that at least one file was uploaded, and that each one has an accepted image extension (`.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`, `.tiff`, `.bmp`).
2. Opens each file with Pillow and converts it to plain RGB — this matters for formats like PNG or GIF that can have transparency, which would otherwise turn solid black in a PDF.
3. Saves the first image as a PDF and appends the rest as additional pages, in upload order.
4. Sends the finished PDF back to the browser as a download.

If something's wrong with the upload (no files, an unsupported file type, or a corrupted image), the route responds with a short error message and a 400 status instead of crashing.

## Troubleshooting

**`ModuleNotFoundError: No module named 'flask'` (or `PIL`)**
Your virtual environment probably isn't active, or the install step was skipped. Re-run the activate command from step 2, then `pip install -r requirements.txt` again.

**Port 5000 is already in use**
Something else on your machine is using that port. Either stop that program, or run `python app.py` after editing the last line of `app.py` to `app.run(debug=True, port=5001)` (or any free port), then open that port in the browser instead.

**The page loads with no styling / no icons**
Make sure you're running the app through Flask (`python app.py` and opening `http://127.0.0.1:5000`) rather than double-clicking `templates/index.html` directly — the Google Fonts and Font Awesome links inside it still need an internet connection to load.

**Uploaded PDF is missing images that I dragged in**
This was a real bug in an earlier version of this project — dropped files were shown in the preview but never actually added to the upload. It's fixed here (the `syncFileInput()` function inside `index.html`'s `<script>` keeps the real upload list in sync with what's shown on screen), but worth knowing about if you're comparing against an older copy.

## Notes for going further

- `app.config["MAX_CONTENT_LENGTH"]` in `app.py` caps uploads at 50 MB total. Raise it if people need to upload many large photos at once.
- `debug=True` in the last line of `app.py` is for local development only — it exposes detailed error pages. Turn it off, and use a proper WSGI server such as `gunicorn`, before putting this anywhere public.
