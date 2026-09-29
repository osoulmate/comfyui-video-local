# MiniMax H3 部署文档（"桌面女友" / 带语音视频）

MiniMax 于 2026-08-03 开源的 33B 全模态视频模型：文/图/视频/音频均可作参考输入，原生生成 32kHz 立体声，最高 2K/24fps。ComfyUI 0.30+ 原生节点支持，无需插件。

- 许可：MiniMax H3 社区许可，**排除美国/欧盟/英国/韩国**，国内使用无碍。
- 硬件：int8_convrot 版单卡 20GB 可跑（自动按层 offload 到内存）；8GB 卡需更低量化。

## 安装

前置：torch 必须 cu130（int8_convrot 的硬性要求）。先激活 conda 环境：

```bash
conda activate comfyui
pip install torch==2.11.0+cu130 torchvision==0.26.0+cu130 torchaudio==2.11.0+cu130 \
    --index-url https://download.pytorch.org/whl/cu130
```

```bash
bash scripts/03_download_minimax_h3.sh    # 下载约 42GB
```

模型清单（来源 Comfy-Org/MiniMax-H3，官方重打包）：

| 文件 | 大小 | 放置位置 |
|---|---|---|
| minimax_h3_fl2va_pruned_int8_convrot.safetensors | 20G | models/diffusion_models/ |
| qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors（文本编码器，无需 Blackwell） | 15G | models/text_encoders/ |
| minimax_h3_video_vae_fp16.safetensors | 4.9G | models/vae/ |
| minimax_h3_audio_vae_fp32.safetensors | 0.6G | models/vae/ |
| minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors（加速 LoRA） | 1.9G | models/loras/ |

工作流（改 `prompt` 即可定制）：

- `workflows/minimax_h3_t2v_api.json` — 文生视频，20 步质量优先
- `workflows/minimax_h3_t2v_turbo_api.json` — 文生视频 turbo LoRA 加速版，6 步约 3 倍速
- `workflows/minimax_h3_i2v_api.json` — **图生视频**：把角色图放进 `ComfyUI/input/girlfriend.jpg`（LoadImage 节点可改文件名），输出尺寸自动跟随图片比例（0.9MP、32 对齐），124 帧≈5 秒
- `workflows/minimax_h3_i2v_turbo_api.json` — 图生视频 turbo 加速版

图生视频玩法：给 AI 生成的角色定装图（或任意照片/画作），模型让她动起来——每次生成同一角色，是"桌面女友"固定形象的正确打开方式。

## 推荐参数

| 项目 | 默认 | 说明 |
|---|---|---|
| 分辨率 | 1344×768 | 2K 需更大显存/更久 |
| 帧数 | 73 | 约束 17n+5（73/24fps≈3 秒） |
| 步数 | 20 | 质量优先的默认配置 |
| 采样器 | res_multistep | 官方指定 |
| CFG | 无 | H3 不用负提示词（BasicGuider 只吃正提示词） |

**加速变体：turbo LoRA**（`workflows/minimax_h3_t2v_turbo_api.json`）

与默认工作流的唯一区别：UNETLoader 后串联 `LoraLoaderModelOnly`（`minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors`，强度 1.0），步数降到 6，速度约 3 倍，质量略有下降，适合打样。要最高画质就用默认的 20 步版本。

加速：UNETLoader → LoraLoaderModelOnly（turbo 8 步 LoRA）→ BasicScheduler steps=6~8，约 4 倍提速。

## 实测记录（2026-09-17，单卡 3080 满载）

| 工作流 | 步数 | 耗时 |
|---|---|---|
| `minimax_h3_t2v_api.json`（默认） | 20 | 约 7.5 分钟（~20s/步），同步生成语音（AAC 32kHz 立体声，音量正常） |
| `minimax_h3_t2v_turbo_api.json`（turbo LoRA） | 6 | 约 2.8 分钟（170 秒，2.6 倍速） |
| `minimax_h3_i2v_turbo_api.json`（图生视频，124 帧≈5 秒） | 6 | 约 5.8 分钟（346 秒），角色一致性验证通过 |

## 玩法路线

1. **动态壁纸**（爆火同款）：视频设为桌面壁纸（Wallpaper Engine 或国产免费壁纸软件）；
2. **角色一致性**：用官方模板 `video_minimax_h3_i2v.json`（图生视频）或 `video_minimax_h3_multiframe_reference.json`（多参考），喂固定定装图，每次生成同一张脸；
3. **真交互**（进阶）：ASR（SenseVoice/FunASR）→ 本地 Qwen3 → TTS（GPT-SoVITS / Fish Speech），参考开源框架 Open-LLM-VTuber / OpenClaw。
4. **完整短片**（已实践）：分镜拆成多条 clip 链式生成（首帧=上条尾帧保连续性，换装用 Ref2VA 参考模式），男声画外音用 edge-tts 后期混入，字幕/波形 UI 用 `post/assemble.py`（ffmpeg 拼接 + ASS 逐字字幕 + showwaves 波形条）合成。成片示例见 `post/final.mp4`。

## 常见问题

- **音频听起来不像任何语言（"模拟人生语"）**：提示词只写了"在说话"但没给台词，音频模块只能脑补出有语调无词汇的伪语音。解决：在 prompt 里写明语言和原话，如 `speaking in Mandarin Chinese, saying: "你好呀，今天工作辛苦了"`——验证可行（模型还会自动烧录对应字幕）。要精确控制每句话/固定音色，用音频参考模式或后期 GPT-SoVITS 配音。
- **"Detected that PyTorch and torchvision were compiled with different CUDA major versions"**：torch/torchvision 大版本没对齐，按上面 cu130 三件套重装。
- **int8_convrot 加载失败/极慢**：确认 torch 为 cu130 且 ComfyUI ≥0.30；不行则退回 `minimax_h3_fl2va_pruned_fp8_scaled.safetensors`（README 注明 fp8_scaled 是 int8 不可用时的备选）。
- **节点输出类型校验错误**：`MiniMaxH3ImageToVideo` 的 slot 0 是 positive（CONDITIONING）、slot 1 才是 LATENT，连线时注意。
- **采样时报 Broken pipe 且重试无效**：服务进程的后台流状态损坏（多见于异常退出后），`scripts/stop_comfyui.sh` 重启服务即可。
