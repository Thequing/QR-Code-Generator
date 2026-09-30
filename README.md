# QR Code Generator

Makes QR codes in the style of `Reference Images/` — rounded modules, rounded
finder eyes, black on white, with your logo on a rounded-square plate in the middle.

## Use it

Double-click **`QR Generator.bat`**.

1. Paste the URL (or any text) — Enter also works.
2. **Browse...** and pick a logo. Optional; skip it for a plain QR code.
3. **Make QR Code** → preview appears.
4. **Retry** to go back and change something, or **Save PNG** to write the file.

The filename is pre-filled from the URL, the same way the reference image is named.

## Details

- Error correction is set to **H** (30% recoverable), so the centre logo never
  costs you a scan. The logo plate covers ~22% of the width.
- Output is ~3000 × 3000 px PNG — fine for print, not just screen.
- Logos can be PNG / JPG / WEBP / BMP / GIF. Transparent PNGs are composited
  onto the white plate, so they stay readable.

## If it does not start

Needs Python 3 with `qrcode` and `pillow`:

```
pip install -r requirements.txt
```

Then run `python qr_generator.py` from this folder to see any error message.
