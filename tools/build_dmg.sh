#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<USAGE
Build a macOS DMG from a .app bundle, optionally building the app first.

Usage:
  $(basename "$0") [options]

App Selection:
  -a, --app PATH          Path to the .app bundle
                         If omitted, auto-detects one .app in <project-root>/dist
      --app-glob GLOB     Glob for auto-detecting app (default: dist/*.app)

Build Pipeline (optional):
  -b, --build-cmd CMD     Build command to run before packaging (repeatable)
      --from-source       Use built-in source->.app build pipeline (PyInstaller)
      --python PATH       Python executable for --from-source (default: python3)
      --project-root DIR  Directory to run build commands in (default: repo root)
      --clean             Remove <project-root>/build and <project-root>/dist first

Optional:
  -o, --output PATH       Output DMG path (default: ./<AppName>.dmg)
  -v, --volume-name NAME  Mounted volume name (default: <AppName>)
  -s, --size SIZE         DMG size for hdiutil, e.g. 200m (default: auto)
      --keep-stage        Keep temporary staging directory
  -h, --help              Show this help

Examples:
  $(basename "$0")
  $(basename "$0") -a dist/Trelby.app
  $(basename "$0") --clean --from-source
  $(basename "$0") --clean -b "python3 -m pip install -r requirements.txt" -b "python3 -m PyInstaller --windowed --name Trelby trelby.py"
  $(basename "$0") -a dist/Trelby.app -o dist/Trelby-1.0.0.dmg -v "Trelby Installer"
USAGE
}

find_default_app() {
  local root="$1"
  local pattern="$2"
  local candidates=()
  local app

  # shellcheck disable=SC2086
  for app in $pattern; do
    if [[ -d "$root/$app" ]]; then
      candidates+=("$root/$app")
    fi
  done

  if [[ ${#candidates[@]} -eq 1 ]]; then
    printf '%s\n' "${candidates[0]}"
    return 0
  fi

  if [[ ${#candidates[@]} -eq 0 ]]; then
    return 1
  fi

  echo "Error: multiple .app bundles found. Use --app to choose one:" >&2
  printf '  %s\n' "${candidates[@]}" >&2
  return 2
}

APP_PATH=""
OUTPUT_DMG=""
VOLUME_NAME=""
DMG_SIZE=""
KEEP_STAGE="false"
APP_GLOB="dist/*.app"
PROJECT_ROOT=""
CLEAN_FIRST="false"
BUILD_CMDS=()
FROM_SOURCE="false"
PYTHON_BIN="python3"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -a|--app)
      APP_PATH="${2:-}"
      shift 2
      ;;
    -o|--output)
      OUTPUT_DMG="${2:-}"
      shift 2
      ;;
    -v|--volume-name)
      VOLUME_NAME="${2:-}"
      shift 2
      ;;
    -s|--size)
      DMG_SIZE="${2:-}"
      shift 2
      ;;
    --app-glob)
      APP_GLOB="${2:-}"
      shift 2
      ;;
    -b|--build-cmd)
      BUILD_CMDS+=("${2:-}")
      shift 2
      ;;
    --from-source)
      FROM_SOURCE="true"
      shift
      ;;
    --python)
      PYTHON_BIN="${2:-}"
      shift 2
      ;;
    --project-root)
      PROJECT_ROOT="${2:-}"
      shift 2
      ;;
    --clean)
      CLEAN_FIRST="true"
      shift
      ;;
    --keep-stage)
      KEEP_STAGE="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if ! command -v hdiutil >/dev/null 2>&1; then
  echo "Error: hdiutil is required and only available on macOS." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -z "$PROJECT_ROOT" ]]; then
  PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
else
  PROJECT_ROOT="$(cd "$PROJECT_ROOT" && pwd)"
fi

if [[ "$CLEAN_FIRST" == "true" ]]; then
  echo "Cleaning build artifacts in $PROJECT_ROOT ..."
  rm -rf "$PROJECT_ROOT/build" "$PROJECT_ROOT/dist"
fi

if [[ "$FROM_SOURCE" == "true" ]]; then
  BUILD_CMDS+=(
    "$PYTHON_BIN -m pip install -r requirements.txt"
    "$PYTHON_BIN -m pip install pyinstaller"
    "$PYTHON_BIN -m PyInstaller --noconfirm --clean --windowed --name Trelby --icon resources_mac/icon.icns --collect-data trelby trelby.py"
  )
fi

if [[ ${#BUILD_CMDS[@]} -gt 0 ]]; then
  echo "Running build pipeline in $PROJECT_ROOT ..."
  for cmd in "${BUILD_CMDS[@]}"; do
    if [[ -z "$cmd" ]]; then
      echo "Error: --build-cmd requires a non-empty command." >&2
      exit 1
    fi
    echo "+ $cmd"
    (cd "$PROJECT_ROOT" && bash -lc "$cmd")
  done
fi

if [[ -z "$APP_PATH" ]]; then
  if ! APP_PATH="$(find_default_app "$PROJECT_ROOT" "$APP_GLOB")"; then
    rc=$?
    if [[ $rc -eq 1 ]]; then
      echo "Error: no .app bundle found with '$APP_GLOB' under $PROJECT_ROOT." >&2
      echo "Use --app PATH, adjust --app-glob, or add --build-cmd." >&2
    fi
    usage >&2
    exit 1
  fi
  echo "Using detected app bundle: $APP_PATH"
fi

if [[ ! -d "$APP_PATH" || "${APP_PATH##*.}" != "app" ]]; then
  echo "Error: --app must point to an existing .app bundle." >&2
  exit 1
fi

APP_PATH="$(cd "$(dirname "$APP_PATH")" && pwd)/$(basename "$APP_PATH")"
APP_NAME="$(basename "$APP_PATH" .app)"

if [[ -z "$VOLUME_NAME" ]]; then
  VOLUME_NAME="$APP_NAME"
fi

if [[ -z "$OUTPUT_DMG" ]]; then
  OUTPUT_DMG="$PWD/${APP_NAME}.dmg"
fi

OUTPUT_DMG="$(cd "$(dirname "$OUTPUT_DMG")" && pwd)/$(basename "$OUTPUT_DMG")"

STAGE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/${APP_NAME}.dmg.stage.XXXXXX")"
cleanup() {
  if [[ "$KEEP_STAGE" == "true" ]]; then
    echo "Kept staging directory: $STAGE_DIR"
    return
  fi
  rm -rf "$STAGE_DIR"
}
trap cleanup EXIT

cp -R "$APP_PATH" "$STAGE_DIR/"
ln -s /Applications "$STAGE_DIR/Applications"

if [[ -f "$OUTPUT_DMG" ]]; then
  rm -f "$OUTPUT_DMG"
fi

CREATE_ARGS=(
  create
  -volname "$VOLUME_NAME"
  -srcfolder "$STAGE_DIR"
  -format UDZO
  "$OUTPUT_DMG"
)

if [[ -n "$DMG_SIZE" ]]; then
  CREATE_ARGS=(
    create
    -size "$DMG_SIZE"
    -volname "$VOLUME_NAME"
    -srcfolder "$STAGE_DIR"
    -format UDZO
    "$OUTPUT_DMG"
  )
fi

hdiutil "${CREATE_ARGS[@]}" >/dev/null

echo "DMG created: $OUTPUT_DMG"
