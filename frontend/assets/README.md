# Ananta POS Assets

This folder should contain the following files for building the Windows installer:

## Required Files:

1. **icon.ico** - Main application icon (256x256 pixels)
2. **installer-icon.ico** - Installer icon (256x256 pixels)
3. **uninstaller-icon.ico** - Uninstaller icon (256x256 pixels)
4. **installer-header.bmp** - Installer header image (150x57 pixels)
5. **installer-sidebar.bmp** - Installer sidebar image (164x314 pixels)

## Creating Icons:

You can create .ico files from PNG images using online tools:
- https://convertio.co/png-ico/
- https://www.icoconverter.com/

Or use free tools:
- GIMP (Free, open-source)
- IcoFX (Free for non-commercial)

## Creating BMP Images:

For installer header and sidebar:
1. Create images in the specified dimensions
2. Use your brand colors and logo
3. Save as 24-bit BMP format

## Default Setup:

If these files don't exist, electron-builder will use default icons.
For a professional installer, it's recommended to create custom assets.

## Quick Setup:

For testing purposes, you can create simple solid-color placeholders:

```bash
# Using ImageMagick (if installed)
convert -size 256x256 xc:blue icon.ico
convert -size 256x256 xc:blue installer-icon.ico
convert -size 256x256 xc:blue uninstaller-icon.ico
convert -size 150x57 xc:white installer-header.bmp
convert -size 164x314 xc:white installer-sidebar.bmp
```

Or simply skip the custom assets for now, and electron-builder will use defaults.
