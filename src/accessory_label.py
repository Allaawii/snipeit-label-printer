"""Builds an accessory label that visually matches Snipe-IT's hardware label.

Snipe-IT only renders label pages for hardware assets; accessories have no
`/accessories/{id}/label`, `/qr_code`, or `/barcode` endpoints (all 404). So for
accessories we reproduce the exact hardware-label markup/CSS and supply our own
QR code (linking to the accessory page), a cosmetic barcode, and the IE logo.

The CSS below is copied verbatim from a real Snipe-IT hardware label so the
output is pixel-identical in layout; only the image sources and text differ.
"""

import base64
from io import BytesIO

import barcode
from barcode.writer import ImageWriter
import qrcode


# Copied verbatim from Snipe-IT's rendered hardware label so the accessory
# label matches exactly. The only change is for `img.qr_img`: the original used
# negative margins to crop the white quiet-zone baked into Snipe-IT's QR image.
# We generate our own QR with a controlled border, so we fit it cleanly instead.
_LABEL_STYLE = """
    body {
        font-family: arial, helvetica, sans-serif;
        width: 8.50000in;
        height: 11.00000in;
        margin: 0.50000in 0.21975in 0.50000in 0.21975in;
        font-size: 9pt;
    }
    .label {
        width: 2.575in;
        height: 0.93in;
        padding: 0in;
        margin-right: 0.05000in; /* the gutter */
        margin-bottom: 0.07000in;
        display: inline-block;
        overflow: hidden;
    }
    div.qr_img {
        width: 0.63in;
        height: 0.63in;
        float: left;
        display: inline-flex;
        padding-right: .15in;
    }
    img.qr_img {
        width: 100%;
        height: 100%;
        padding-bottom: .04in;
    }
    img.barcode {
        display:block;
        margin-top:-15px;
        width: 100%;
    }
    div.label-logo {
        float: right;
        display: inline-block;
    }
    img.label-logo {
        height: 0.5in;
    }
    .qr_text {
        width: 2.575in;
        height: 0.93in;
        padding-top: 0.07000in;
        font-family: arial, helvetica, sans-serif;
        font-size: 9pt;
        padding-right: .0001in;
        overflow: hidden !important;
        display: inline;
        word-wrap: break-word;
        word-break: break-all;
    }
    div.barcode_container {
        width: 100%;
        display: inline;
        overflow: hidden;
    }
"""


def _png_data_uri(png_bytes: bytes) -> str:
    encoded = base64.b64encode(png_bytes).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _make_qr_data_uri(target_url: str) -> str:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=1,
    )
    qr.add_data(target_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return _png_data_uri(buffer.getvalue())


def _make_barcode_data_uri(value: str) -> str:
    # Cosmetic Code128 so the label looks like a hardware label. The encoded
    # value carries no meaning by design (the QR is the functional code).
    code128 = barcode.get(
        "code128",
        value,
        writer=ImageWriter(),
    )
    buffer = BytesIO()
    code128.write(
        buffer,
        options={
            "module_height": 12.0,
            "module_width": 0.22,
            "quiet_zone": 1.0,
            "font_size": 0,  # hide the human-readable text under the bars
            "text": "",
            "write_text": False,
        },
    )
    return _png_data_uri(buffer.getvalue())


def _escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def build_accessory_label_html(
    accessory_id: str,
    accessory_name: str,
    accessory_url: str,
    logo_data_uri: str | None,
) -> str:
    """Return a full HTML document for the accessory label.

    The QR code encodes ``accessory_url`` (scanning opens the accessory page).
    ``logo_data_uri`` is the IE logo as a data URI; if None the logo is omitted.
    """
    qr_uri = _make_qr_data_uri(accessory_url)
    barcode_uri = _make_barcode_data_uri(f"ACC-{accessory_id}")

    logo_html = ""
    if logo_data_uri:
        logo_html = (
            '<div class="label-logo">'
            f'<img class="label-logo" src="{logo_data_uri}">'
            "</div>"
        )

    name_line = _escape_html(accessory_name) if accessory_name else "Accessory"

    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<title>Labels</title>
<style>{_LABEL_STYLE}</style>
</head>
<body>
    <div class="label">
        <div class="qr_img">
            <img src="{qr_uri}" class="qr_img">
        </div>
        <div class="qr_text">
            {logo_html}
            <div class="pull-left">
                N: {name_line}
            </div>
            <div class="pull-left">
                ID: {_escape_html(accessory_id)}
            </div>
        </div>
        <div class="barcode_container">
            <img src="{barcode_uri}" class="barcode">
        </div>
    </div>
</body></html>"""
