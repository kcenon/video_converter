# macOS App Icons

This directory contains the icon assets for the Video Converter macOS application.

## Directory Structure

```
icons/
├── README.md           # This file
├── app.icns            # Compiled app icon (generated from iconset)
├── app.iconset/        # Source PNG images for app icon
│   ├── icon_16x16.png
│   ├── icon_16x16@2x.png
│   ├── icon_32x32.png
│   ├── icon_32x32@2x.png
│   ├── icon_128x128.png
│   ├── icon_128x128@2x.png
│   ├── icon_256x256.png
│   ├── icon_256x256@2x.png
│   ├── icon_512x512.png
│   └── icon_512x512@2x.png
└── document.icns       # Document type icon (optional)
```

## Creating Icons

### Required Sizes

For a complete macOS icon, you need the following PNG files:

| File Name | Size (pixels) | Description |
|-----------|---------------|-------------|
| icon_16x16.png | 16x16 | Small icon |
| icon_16x16@2x.png | 32x32 | Retina small |
| icon_32x32.png | 32x32 | Medium icon |
| icon_32x32@2x.png | 64x64 | Retina medium |
| icon_128x128.png | 128x128 | Large icon |
| icon_128x128@2x.png | 256x256 | Retina large |
| icon_256x256.png | 256x256 | Extra large |
| icon_256x256@2x.png | 512x512 | Retina extra large |
| icon_512x512.png | 512x512 | Huge icon |
| icon_512x512@2x.png | 1024x1024 | Retina huge |

### Converting to .icns

Once you have all the PNG files in `app.iconset/`, run:

```bash
iconutil -c icns app.iconset -o app.icns
```

### Design Guidelines

1. **Keep it simple**: The icon should be recognizable at 16x16 pixels
2. **Use a square canvas**: macOS will apply rounded corners automatically
3. **Avoid text**: Text becomes unreadable at small sizes
4. **Consider the Dock**: Icons should look good against various wallpapers

### Placeholder Generation

If you don't have custom icons, the build script will generate a simple placeholder.
For production releases, please provide proper icon assets.

## Current Status

- [ ] App icon designed
- [ ] All sizes exported
- [ ] .icns file generated
- [ ] Document icon designed (optional)

## Resources

- [Apple Human Interface Guidelines - App Icons](https://developer.apple.com/design/human-interface-guidelines/app-icons)
- [iconutil man page](x-man-page://1/iconutil)
