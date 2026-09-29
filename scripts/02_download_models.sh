#!/usr/bin/env bash
# 下载 Wan 2.2 模型权重（约 31GB）。
# 无代理时：HF_ENDPOINT=https://hf-mirror.com bash scripts/02_download_models.sh
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
activate_env

M="$COMFYUI_DIR/models"
mkdir -p "$M/diffusion_models" "$M/text_encoders" "$M/vae"

dl() {  # dl <repo> <file-in-repo> <out_dir>
  python - "$1" "$2" "$3" <<'EOF'
import sys, shutil, os
from huggingface_hub import hf_hub_download
repo, fname, out = sys.argv[1:4]
p = hf_hub_download(repo, fname)  # 走 Xet 加速，缓存于 ~/.cache/huggingface
shutil.copy(p, os.path.join(out, os.path.basename(fname)))
print("saved:", os.path.join(out, os.path.basename(fname)))
EOF
}

dl "QuantStack/Wan2.2-T2V-A14B-GGUF" "HighNoise/Wan2.2-T2V-A14B-HighNoise-Q5_K_M.gguf" "$M/diffusion_models"
dl "QuantStack/Wan2.2-T2V-A14B-GGUF" "LowNoise/Wan2.2-T2V-A14B-LowNoise-Q5_K_M.gguf"  "$M/diffusion_models"
dl "QuantStack/Wan2.2-T2V-A14B-GGUF" "VAE/Wan2.1_VAE.safetensors"                    "$M/vae"
dl "QuantStack/Wan2.2-TI2V-5B-GGUF"  "Wan2.2-TI2V-5B-Q5_K_M.gguf"                     "$M/diffusion_models"
dl "QuantStack/Wan2.2-TI2V-5B-GGUF"  "VAE/Wan2.2_VAE.safetensors"                     "$M/vae"
dl "Comfy-Org/Wan_2.2_ComfyUI_Repackaged" "split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors" "$M/text_encoders"

echo "== models =="
ls -lh "$M/diffusion_models" "$M/vae" "$M/text_encoders"
echo "done. 下载缓存可清理: rm -rf ~/.cache/huggingface"
