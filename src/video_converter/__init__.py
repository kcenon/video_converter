"""Video Converter - Automated H.264 to H.265 conversion for macOS."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("video-converter")
except PackageNotFoundError:
    __version__ = "0.0.0.dev"

__author__ = "Video Converter Team"
