# Homebrew Cask Formula for Video Converter
#
# This formula allows installation of Video Converter via Homebrew Cask.
#
# To install from local tap:
#   brew tap kcenon/video-converter https://github.com/kcenon/video_converter
#   brew install --cask video-converter
#
# Or install directly from GitHub releases:
#   brew install --cask https://raw.githubusercontent.com/kcenon/video_converter/main/packaging/macos/homebrew/video-converter.rb

cask "video-converter" do
  version "0.3.0"
  sha256 :no_check # Replace with actual SHA256 when releasing

  url "https://github.com/kcenon/video_converter/releases/download/v#{version}/VideoConverter-#{version}.dmg"
  name "Video Converter"
  desc "Automated H.264 to H.265 video conversion for macOS with Photos library integration"
  homepage "https://github.com/kcenon/video_converter"

  # Minimum macOS version
  depends_on macos: ">= :monterey"

  # External dependencies
  depends_on formula: "ffmpeg"

  app "Video Converter.app"

  # CLI tool installation (symlink to the Python CLI)
  # Note: CLI is separate from GUI and requires Python installation
  # binary "#{appdir}/Video Converter.app/Contents/MacOS/video-converter-cli",
  #        target: "video-converter"

  # Zap removes all application data on uninstall with --zap
  zap trash: [
    "~/Library/Application Support/VideoConverter",
    "~/Library/Caches/com.github.kcenon.videoconverter",
    "~/Library/Preferences/com.github.kcenon.videoconverter.plist",
    "~/Library/Saved Application State/com.github.kcenon.videoconverter.savedState",
    "~/.config/video_converter",
  ]

  caveats <<~EOS
    Video Converter requires Full Disk Access for Photos library integration:
      1. Open System Preferences > Privacy & Security > Full Disk Access
      2. Add "Video Converter" to the list

    For CLI usage, install via pip:
      pip install video-converter

    For hardware-accelerated encoding, ensure you have a compatible Mac:
      - Apple Silicon (M1/M2/M3) with VideoToolbox
      - Intel Mac with VideoToolbox support

    Documentation: https://github.com/kcenon/video_converter#readme
  EOS
end
