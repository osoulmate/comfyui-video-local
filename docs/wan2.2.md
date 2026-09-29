# Wan 2.2 部署文档

高质量文生视频 / 图生视频：**Wan 2.2 T2V 14B（GGUF Q5_K_M，双专家）+ TI2V 5B（GGUF Q5_K_M）**。

- 硬件约束：Ampere 无 FP8 加速，用 GGUF 量化（Q5_K_M 是 20GB 卡上质量/显存平衡点；Q6_K/Q8_0 会顶到上限，Q4_K_M 更稳）。
- 许可：Apache 2.0，可商用；QuantStack GGUF 为社区量化分发。

## 安装

```bash
bash scripts/01_install_comfyui.sh    # conda 环境 + torch + ComfyUI + GGUF/视频插件
bash scripts/02_download_models.sh    # 下载约 31GB 权重
```

模型清单：

| 文件 | 大小 | 来源 | 放置位置（相对 ComfyUI/） |
|---|---|---|---|
| Wan2.2-T2V-A14B-HighNoise-Q5_K_M.gguf | 10.5G | QuantStack/Wan2.2-T2V-A14B-GGUF | models/diffusion_models/ |
| Wan2.2-T2V-A14B-LowNoise-Q5_K_M.gguf  | 10.5G | 同上 | models/diffusion_models/ |
| Wan2.2-TI2V-5B-Q5_K_M.gguf            | 3.8G | QuantStack/Wan2.2-TI2V-5B-GGUF | models/diffusion_models/ |
| umt5_xxl_fp8_e4m3fn_scaled.safetensors | 5.7G | Comfy-Org/Wan_2.2_ComfyUI_Repackaged | models/text_encoders/ |
| wan_2.1_vae.safetensors（14B 用） | 0.25G | QuantStack 仓库 VAE/ 目录 | models/vae/ |
| wan2.2_vae.safetensors（5B 用）   | 0.25G | 同上 | models/vae/ |

工作流（拖入 ComfyUI 界面即用）：

- `workflows/wan22_t2v_api.json` — 14B T2V，双专家串联
- `workflows/wan22_5b_ti2v_api.json` — 5B TI2V，单模型

## 推荐参数

**14B T2V**（GGUF Q5_K_M）：

| 项目 | 480p（推荐起步） | 720p |
|---|---|---|
| 分辨率 | 832×480 | 1280×720 |
| 帧数 | 81（约 5 秒 @16fps） | 81 |
| 总步数（高噪+低噪） | 20（10+10） | 20 |
| CFG | 3.5 | 3.5 |
| shift | 5.0 | 5.0 |

- **双专家**：前一半步数用 HighNoise 模型建立构图和运动，后一半用 LowNoise 细化纹理；工作流已按步数拆分（参数取自 ComfyUI 官方模板）。
- 改总步数时**两个 KSamplerAdvanced 的拆分点要同步改**：阶段1 end_at_step = 阶段2 start_at_step = 总步数一半（`test_gen.py` 已自动处理）。
- 单卡 20GB 跑 480p 无压力；720p OOM 时降帧数到 49 或换 Q4_K_M。
- 加速：给双专家各挂 lightx2v 4 步蒸馏 LoRA（总步数 4：2+2），提速 4~5 倍，质量略降。

**5B TI2V**：步数 20、CFG 5.0、sampler `uni_pc`、shift 8.0，显存约 14B 的一半，快速迭代用它。

## 实测记录（2026-09-17，单卡 3080）

| 模型 | 分辨率×帧数 | 步数 | 耗时 | 峰值显存 | 画质 |
|---|---|---|---|---|---|
| 14B T2V | 832×480×81 | 20（10+10） | 约 23 分钟（~65s/步） | ~14.5GB | 优秀 |
| 5B TI2V | 832×480×81 | 20 | 约 110 秒（~4.2s/步） | ~6GB | 良好 |

首次加载 GGUF 反量化 1–3 分钟属正常；模型进缓存后再次生成更快。

## 常见问题

- **OOM**：降分辨率/帧数；换 Q4_K_M；确认无其他占显存进程。
- **下载失败**：确认代理 `curl -x http://127.0.0.1:7890 -I https://huggingface.co`；或 `HF_ENDPOINT=https://hf-mirror.com` 直连镜像。
- **双卡**：默认只用 GPU 0；第二张卡跑第二个实例加 `--cuda-device 1`；单任务跨卡受 PCIe 3.0 限制不建议。
- **排查记录**：14B 曾出现"满屏噪点"，根因是双阶段采样中第二阶段步数为 0（输出停在残噪状态）；权重/检测/精度均验证无恙，遇同类花屏先查采样器拆分点。

## 选型备注

Wan 2.2 是 2025 年开源标杆；更新的 Wan 2.5/2.7 为闭源托管 API 不可本机部署。要更快的带语音生成/角色一致性，见 [MiniMax H3 文档](minimax-h3.md)。
