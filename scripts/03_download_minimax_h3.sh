#!/usr/bin/env bash
# 下载 MiniMax H3 模型（Comfy-Org 重打包版，int8_convrot 扩散模型 + nvfp4_awq 文本编码器），约 42GB。
# 无代理时：HF_ENDPOINT=https://hf-mirror.com bash scripts/03_download_minimax_h3.sh
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
activate_env

M="$COMFYUI_DIR/models"
mkdir -p "$M/diffusion_models" "$M/text_encoders" "$M/vae" "$M/loras"

dl() {  # dl <repo> <file-in-repo> <out_dir>
  python - "$1" "$2" "$3" <<'EOF'
import sys, shutil, os
from huggingface_hub import hf_hub_download
repo, fname, out = sys.argv[1:4]
p = hf_hub_download(repo, fname)
dst = os.path.join(out, os.path.basename(fname))
if not os.path.exists(dst):
    shutil.copy(p, dst)
print("saved:", dst, flush=True)
EOF
}

R=Comfy-Org/MiniMax-H3
dl $R "diffusion_models/minimax_h3_fl2va_pruned_int8_convrot.safetensors" "$M/diffusion_models"
dl $R "text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"         "$M/text_encoders"
dl $R "vae/minimax_h3_video_vae_fp16.safetensors"                          "$M/vae"
dl $R "vae/minimax_h3_audio_vae_fp32.safetensors"                          "$M/vae"
dl $R "loras/minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors"    "$M/loras"
echo "== h3 models done =="
ls -lh "$M/diffusion_models" "$M/text_encoders" "$M/vae" "$M/loras" | grep -i h3
