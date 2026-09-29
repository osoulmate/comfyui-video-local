#!/usr/bin/env bash
# 启动 ComfyUI：bash scripts/start_comfyui.sh [--listen 0.0.0.0] [--cuda-device N] ...
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
conda activate "$COMFYUI_ENV"
cd "$COMFYUI_DIR"
exec python main.py --port "${PORT:-8188}" "$@"
