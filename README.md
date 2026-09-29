# 本机 AI 视频生成 · 总入口

在 `2× RTX 3080 20GB`（无 NVLink）+ Ubuntu 24.04 上部署两套开源视频生成，共用同一个 ComfyUI 服务：

| | [Wan 2.2](docs/wan2.2.md) | [MiniMax H3](docs/minimax-h3.md) |
|---|---|---|
| 定位 | 高质量 T2V / I2V | 全模态（**带语音**）、角色一致性 |
| 模型 | 14B 双专家 / 5B TI2V（GGUF Q5_K_M） | 33B（int8_convrot）+ Qwen3-VL 32B 编码器 |
| 实测速度 | 14B：23 分钟/条；5B：110 秒/条 | **7.5 分钟/条**（1344×768×73，20 步） |
| 显存峰值 | 14.5GB / 6GB | 19.8GB（单卡满载） |
| 适合 | 精细创作 | 快速迭代、"桌面女友"玩法 |

进阶：[真交互方案设计](docs/interactive-girlfriend.md)（桌宠/真人口型/视频回信四路线 + LLM 端点）；短片成片管线见 `post/assemble.py`。

- 硬件约束：Ampere（sm_86）不支持 FP8/NVFP4 硬件加速；量化格式选择见各自文档。
- 环境：conda 环境 `comfyui`（Python 3.12）+ PyTorch cu130（torch 2.11.0 / torchvision 0.26.0 / torchaudio 2.11.0）。
- 依赖清单已导出到项目根目录：`environment.yml`（conda 全量，含 pip 段，`conda env create -f environment.yml` 可复现）、`requirements.txt`（纯 pip 108 项）。
- 许可：Wan 2.2 为 Apache 2.0；H3 社区许可排除美国/欧盟/英国/韩国。

## 公共环境

**目录结构**（以项目根目录为基准）

```text
├── README.md                    # 本文档
├── docs/                        # wan2.2.md / minimax-h3.md 两篇部署文档
├── environment.yml              # conda 环境全量导出（可复现）
├── requirements.txt             # pip 冻结清单
├── ComfyUI/                     # 主程序 + 全部模型 + 输出（第三方 git 仓库，不入库）
├── scripts/                     # 安装/下载/启动/测试脚本（编号对应各自文档）
└── workflows/                   # API 格式工作流（可拖入界面）
```

**网络**：pypi / pytorch 源直连；GitHub / HuggingFace 走代理。代理自动探测（本机 127.0.0.1:7890 可用则用之），也可用 `PROXY=<url>` 指定、`PROXY=none` 强制直连；无代理时用 `HF_ENDPOINT=https://hf-mirror.com` 走国内镜像下载模型。

**脚本可移植性**：`scripts/` 下的脚本不依赖绝对路径。公共逻辑（项目根定位、conda 探测、代理）在 `scripts/common.sh`，支持以下环境变量覆盖：

| 变量 | 默认 | 说明 |
|---|---|---|
| `COMFYUI_ENV` | `comfyui` | conda 环境名 |
| `CONDA_SH` | 自动探测 | conda.sh 路径（PATH 与 `~/miniconda3` 等常见位置） |
| `PROXY` | `auto` | 下载代理；`none` 直连 |
| `COMFYUI_DIR` | `<项目根>/ComfyUI` | ComfyUI 目录 |
| `HF_ENDPOINT` | 官方 | 模型下载镜像（如 `https://hf-mirror.com`） |
| `TORCH_SPEC` / `PYTORCH_INDEX` | cu130 三件套 | 其他显卡可换对应 torch 版本/源 |

复现的最小流程：`conda env create -f environment.yml`（或跑 `scripts/01_install_comfyui.sh`）→ `02`/`03` 下模型 → `start_comfyui.sh` 启动。

**服务启停**

```bash
bash scripts/start_comfyui.sh                 # 启动，127.0.0.1:8188
bash scripts/start_comfyui.sh --listen 0.0.0.0  # 局域网开放
bash scripts/start_comfyui.sh --cuda-device 1   # 用第二张卡
bash scripts/stop_comfyui.sh                  # 停止（先优雅退出，超时才强杀）
```

浏览器打开 `http://127.0.0.1:8188`，把 `workflows/*.json` 拖进画布载入；视频输出在 `ComfyUI/output/video/`。

**冒烟测试 / API 调用**（先 `conda activate comfyui`）

```bash
python scripts/test_gen.py --workflow workflows/<工作流>.json \
    --prompt "..." --w 832 --h 480 --frames 81 --steps 20
```

（节点级覆写规则见各文档；双卡、OOM 等通用问题见 [docs/wan2.2.md](docs/wan2.2.md) 的常见问题。）
