"""LightTable Studio - Flask backend.

This module serves the "Image -> PDF Converter" web app: a single
upload page (templates/index.html) backed by one conversion endpoint
that stacks the uploaded images into a multi-page PDF and sends it
back to the browser as a download.

Run this file directly to start a local development server::

    python app.py

Then open http://127.0.0.1:5000 in a browser.
"""

from __future__ import annotations

import io
from typing import List

from flask import Flask, abort, render_template, request, send_file
from PIL import Image, UnidentifiedImageError
from werkzeug.datastructures import FileStorage

app = Flask(__name__)

#: Largest request body Flask will accept before rejecting it outright
#: (50 MB total, across all uploaded files combined). Raise this if
#: your users need to upload larger batches of high-resolution photos.
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

#: File extensions treated as images. Anything uploaded under the
#: "images" field with a different extension is rejected up front
#: instead of being silently skipped or crashing the conversion step.
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif", "tiff", "bmp"}


def is_allowed_file(filename: str) -> bool:
    """Check whether a filename has an extension we accept.

    Args:
        filename: The original filename as uploaded by the browser,
            e.g. ``"vacation-photo.JPG"``.

    Returns:
        ``True`` if the extension (matched case-insensitively) is in
        :data:`ALLOWED_EXTENSIONS`. ``False`` for a filename with no
        extension at all, or an unsupported one.
    """
    if "." not in filename:
        return False
    extension = filename.rsplit(".", 1)[1].lower()
    return extension in ALLOWED_EXTENSIONS


def load_images_as_rgb(files: List[FileStorage]) -> List[Image.Image]:
    """Open each uploaded file with Pillow and normalize it to RGB.

    A PDF page written by Pillow must be in RGB (or L / CMYK) mode, so
    anything that arrives as RGBA (transparent PNGs) or palette mode
    (GIFs) is flattened onto a white background first. Without this
    step, transparent areas would turn solid black in the exported
    PDF instead of staying white.

    Args:
        files: Uploaded file objects that have already passed
            :func:`is_allowed_file`.

    Returns:
        A list of Pillow ``Image`` objects, in the same order as
        ``files``, each guaranteed to be in RGB mode.

    Raises:
        ValueError: If any file cannot be decoded as an image - for
            example a corrupted upload, a truncated file, or a file
            whose extension doesn't match its actual contents.
    """
    images: List[Image.Image] = []

    for file in files:
        try:
            image = Image.open(file.stream)
            # .load() forces Pillow to fully decode the pixel data now,
            # so a corrupt file raises here with a clear error instead
            # of failing later, mid-way through writing the PDF.
            image.load()
        except UnidentifiedImageError as exc:
            raise ValueError(f'"{file.filename}" is not a readable image file.') from exc

        if image.mode != "RGB":
            background = Image.new("RGB", image.size, (255, 255, 255))
            if image.mode in ("RGBA", "LA"):
                background.paste(image, mask=image.split()[-1])
            else:
                background.paste(image.convert("RGB"))
            image = background

        images.append(image)

    return images


@app.route("/")
def index():
    """Render the upload page.

    This is the entire front end: a drag-and-drop zone, a live
    thumbnail preview, and a "Generate PDF" button whose form POSTs to
    :func:`convert`. All interactive behaviour lives in
    ``static/script.js``; this view just renders the HTML shell.
    """
    return render_template("index.html")


@app.route("/convert", methods=["POST"])
def convert():
    """Combine the uploaded images into one PDF and return it.

    Expects a ``multipart/form-data`` POST with one or more files
    under the ``images`` field - this matches the
    ``name="images"`` attribute on the file input in
    ``templates/index.html``. Images are stacked into a multi-page PDF
    in the order they were uploaded, then streamed back to the browser
    as a file download.

    Returns:
        flask.Response: The generated PDF, with headers set so the
        browser downloads it as ``converted.pdf``.

    Raises:
        werkzeug.exceptions.HTTPException: A 400 response (via
            :func:`flask.abort`) when no files were uploaded, none of
            the uploaded files are supported image types, or Pillow
            could not decode one of them.
    """
    uploaded_files = request.files.getlist("images")

    if not uploaded_files or all(f.filename == "" for f in uploaded_files):
        abort(400, description="No images were uploaded.")

    valid_files = [f for f in uploaded_files if f.filename and is_allowed_file(f.filename)]

    if not valid_files:
        abort(400, description="None of the uploaded files are supported image types.")

    try:
        images = load_images_as_rgb(valid_files)
    except ValueError as exc:
        abort(400, description=str(exc))

    # Pillow writes a multi-page PDF through the first image's save()
    # call, passing every other page in via append_images.
    pdf_buffer = io.BytesIO()
    first_image, remaining_images = images[0], images[1:]
    first_image.save(
        pdf_buffer,
        format="PDF",
        save_all=True,
        append_images=remaining_images,
    )
    pdf_buffer.seek(0)

    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="converted.pdf",
    )


@app.errorhandler(400)
def handle_bad_request(error):
    """Return a short JSON body for 400 errors instead of an HTML page.

    Args:
        error: The ``werkzeug.exceptions.BadRequest`` instance Flask
            passes to error handlers, carrying the ``description`` set
            by whichever :func:`flask.abort` call triggered it.

    Returns:
        tuple: A ``(body, status_code)`` pair, which Flask converts
        into a JSON response with a 400 status.
    """
    return {"error": error.description}, 400


if __name__ == "__main__":
    # This block only runs when you start the app directly with
    # "python app.py" - it's for local development. On Render (or any
    # other host), gunicorn imports the `app` object above and serves
    # it itself, so this block never executes there; see Procfile.
    #
    # debug=True auto-reloads the server on code changes and shows
    # detailed in-browser tracebacks - handy locally, but it leaks
    # internals if left on in production, which is why it's off here
    # and Procfile never passes it to gunicorn either.
    import os

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
