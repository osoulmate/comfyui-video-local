#!/usr/bin/env bash
# 安装 ComfyUI + 自定义节点（GGUF 加载器、视频导出）到 conda 环境。
# 可复现/给他人使用：所有路径与版本均可通过环境变量覆盖（见 scripts/common.sh 头部说明）。
#   PYTHON_VER   python 版本     （默认 3.12）
#   TORCH_SPEC   torch 安装规格  （默认 cu130 三件套；其他显卡自行指定）
#   PYTORCH_INDEX pytorch 源     （默认 https://download.pytorch.org/whl/cu130）
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

PYTHON_VER="${PYTHON_VER:-3.12}"
PYTORCH_INDEX="${PYTORCH_INDEX:-https://download.pytorch.org/whl/cu130}"
TORCH_SPEC="${TORCH_SPEC:-torch==2.11.0+cu130 torchvision==0.26.0+cu130 torchaudio==2.11.0+cu130}"

# conda 环境（不存在则创建）
if ! conda env list | awk '{print $1}' | grep -qx "$COMFYUI_ENV"; then
  conda create -y -n "$COMFYUI_ENV" python="$PYTHON_VER"
fi
conda activate "$COMFYUI_ENV"
pip install -U pip

# ComfyUI 主程序
[ -d "$COMFYUI_DIR" ] || git clone --depth 1 https://github.com/comfyanonymous/ComfyUI "$COMFYUI_DIR"

# PyTorch（pytorch 源国内一般可直连，临时去掉代理避免绕路）
( unset https_proxy http_proxy; pip install $TORCH_SPEC --index-url "$PYTORCH_INDEX" )

pip install -r "$COMFYUI_DIR/requirements.txt"

cd "$COMFYUI_DIR/custom_nodes"
[ -d ComfyUI-GGUF ] || git clone --depth 1 https://github.com/city96/ComfyUI-GGUF
[ -d ComfyUI-VideoHelperSuite ] || git clone --depth 1 https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite
pip install -r ComfyUI-GGUF/requirements.txt
pip install -r ComfyUI-VideoHelperSuite/requirements.txt

echo "== install done =="
python -c "import torch; print('torch', torch.__version__, 'cuda', torch.version.cuda, torch.cuda.device_count(), 'gpu(s)')"
