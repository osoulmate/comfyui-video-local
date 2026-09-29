#!/usr/bin/env bash
# 公共配置：所有安装/下载/启动脚本先 source 本文件。
#
# 可用环境变量覆盖（均有合理默认值）：
#   COMFYUI_ENV   conda 环境名          （默认 comfyui）
#   CONDA_SH      conda.sh 路径         （默认自动探测 PATH / ~/miniconda3 等）
#   PROXY         下载代理              （默认 auto：本机 7890 可用则用；none=直连）
#   COMFYUI_DIR   ComfyUI 目录          （默认 <本文件上级目录>/ComfyUI）
#   HF_ENDPOINT   模型下载镜像          （无代理时可设 https://hf-mirror.com）

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMFYUI_DIR="${COMFYUI_DIR:-$PROJECT_ROOT/ComfyUI}"
COMFYUI_ENV="${COMFYUI_ENV:-comfyui}"

# --- conda 定位 ---
if [ -z "${CONDA_SH:-}" ]; then
  if command -v conda >/dev/null 2>&1; then
    CONDA_SH="$(conda info --base)/etc/profile.d/conda.sh"
  else
    for d in "$HOME/miniconda3" "$HOME/anaconda3" "$HOME/miniforge3" "$HOME/mambaforge"; do
      [ -f "$d/etc/profile.d/conda.sh" ] && CONDA_SH="$d/etc/profile.d/conda.sh" && break
    done
  fi
fi
if [ -z "${CONDA_SH:-}" ] || [ ! -f "$CONDA_SH" ]; then
  echo "ERROR: 未找到 conda。请先安装 Miniconda，或用 CONDA_SH=<conda安装目录>/etc/profile.d/conda.sh 指定。" >&2
  exit 1
fi
# shellcheck disable=SC1090
source "$CONDA_SH"

# --- 代理：PROXY > 本机 7890 探测 > 直连 ---
if [ "${PROXY:-auto}" = "none" ]; then
  :
elif [ -n "${PROXY:-}" ]; then
  export https_proxy="$PROXY" http_proxy="$PROXY" no_proxy="127.0.0.1,localhost"
elif curl -s -m 2 -x http://127.0.0.1:7890 -o /dev/null https://huggingface.co 2>/dev/null; then
  export https_proxy=http://127.0.0.1:7890 http_proxy=http://127.0.0.1:7890 no_proxy="127.0.0.1,localhost"
fi

# --- 激活 conda 环境（不存在则报错提示先跑 01）---
activate_env() {
  if ! conda env list | awk '{print $1}' | grep -qx "$COMFYUI_ENV"; then
    echo "ERROR: conda 环境 '$COMFYUI_ENV' 不存在，请先运行 scripts/01_install_comfyui.sh" >&2
    exit 1
  fi
  conda activate "$COMFYUI_ENV"
}
