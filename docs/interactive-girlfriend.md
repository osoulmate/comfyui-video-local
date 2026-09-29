# AI 桌面女友 · 真交互方案设计

> 前置状态：视频生成链路已完成（见 [minimax-h3.md](minimax-h3.md)，短片成片在 `post/final.mp4`）；
> LLM 已有可用 OpenAI 兼容端点（见附录 A），**四个方案的"大脑"均直接使用该端点，无需本地部署 LLM**。

## 目标定义

"真交互" = 她**听得见**（ASR）、**想得明白**（LLM + 记忆）、**开口回答**（TTS + 口型）、可选**看得见**（视觉）。

## 环境基线

| 项目 | 现状 |
|---|---|
| GPU | 2× RTX 3080 20GB（无 NVLink，Ampere 无 FP8 硬件加速） |
| CPU / 内存 | 2× Xeon E5-2682 v4（32 核，性能弱）/ 125GB |
| 已部署 | ComfyUI 0.36 + Wan 2.2 + MiniMax H3（int8/ref2va）+ turbo LoRA |
| 可用组件 | edge-tts（实测通）、ffmpeg、CJK 字体、conda env `comfyui` |
| LLM | hintlab `qwen3.8-27b`（OpenAI 兼容，内/外网双地址，2026-09-18 实测通过） |

约束：老 Xeon 单核弱 → ASR/TTS 选轻量本地模型或云端；显存 40GB 总量要留给 H3 生成。

---

## 方案 A：Open-LLM-VTuber 桌宠全家桶（最快落地）

成熟开源框架，ASR→LLM→TTS→Live2D 口型全链路集成，自带桌面宠物壳。

```
麦克风 → SenseVoice(本地ASR) → hintlab qwen3.8-27b → edge-tts(TTS)
                                        ↓
                          Live2D 皮 + 口型/表情驱动 ← TTS 音频流
```

| 组件 | 选型 | 资源占用 |
|---|---|---|
| 桌宠壳 + 口型 | Open-LLM-VTuber（浏览器/Electron） | 近零 GPU |
| ASR | SenseVoice-Small（本地，~1GB） | CPU 实时 |
| LLM | hintlab `qwen3.8-27b` | 零本地资源 |
| TTS | edge-tts（zh 女声，已验证）→ 可换 GPT-SoVITS | 零 GPU / 联网 |
| 记忆 | 框架自带 persona + 历史管理 | 磁盘 |

- **部署量**：小（pip 依赖 + 配置 conf.yaml 指向 hintlab 端点）
- **单轮延迟**：≈1.5~3s（ASR 0.3 + LLM 1~2 + TTS 0.5，口型流式）
- ✅ 今天可玩、记忆/人设框架现成；❌ 形象是 Live2D 二次元人偶，非 girl.png 本人

## 方案 B：真人形象口型驱动（保真度最高）

LLM + 克隆音色 TTS + MuseTalk 对口型，让"girl.png 本人"开口。

```
你说话 → SenseVoice(本地) → hintlab qwen3.8-27b → GPT-SoVITS(克隆她的声音)
                                                              ↓
                    girl.png/视频底 + MuseTalk 口型生成(流式) → 她开口回答
```

| 组件 | 选型 | 显存 |
|---|---|---|
| 口型 | MuseTalk（腾讯开源，3080 接近实时） | ~8G（GPU 0） |
| TTS | GPT-SoVITS（几秒样本克隆，中文社区标准） | ~6G（GPU 0/1） |
| ASR / LLM | 同方案 A | ~0 |

- **部署量**：大（MuseTalk + SoVITS 两套环境，权重约 8~10GB 下载）
- **单轮延迟**：≈2~5s/轮；对话中 H3 不占卡，可并存
- ✅ 真人形象 + 专属音色，体验天花板；❌ 部署最重，口型精度弱于 H3 原生生成

## 方案 C：异步视频回信（零新增部署）

复用现有视频链路，对标米哈游《林离 Olivia》的"写信"模式：

```
你留言(文字/语音) → hintlab LLM 写回信 → TTS 配音
        → H3 turbo 生成"她读信"视频(单条约3分钟) → 桌面推送播放
```

- **部署量**：零（全部组件已就绪）
- **延迟**：分钟级（异步，非实时对话）
- ✅ 每条回复都是她本人的新视频，质感最高；❌ 不能实时聊天

## 方案 D：混合/兜底

任一方案中组件的可替换项：

- LLM 已在云端（hintlab），本地压力为零；
- TTS 云化（edge-tts）↔ 本地化（SoVITS）按隐私/效果权衡；
- ASR 云化（通义/讯飞 API）↔ 本地 SenseVoice 按老 CPU 负载权衡；
- 视觉能力（可选）：屏幕/摄像头理解用 Qwen3-VL（H3 的文本编码器已是 Qwen3-VL 32B，复用成本低）。

---

## 对比与路线

| | 实时性 | 形象保真 | 部署成本 | 新增下载 |
|---|---|---|---|---|
| A 桌宠 | ≈2s | ★★ Live2D | 低 | <1GB |
| B 真人口型 | 2~5s | ★★★★ 本人 | 高 | ~10GB |
| C 视频回信 | 分钟级 | ★★★★★ 本人+新视频 | 零 | 0 |
| D 混合 | 同基底 | 同基底 | — | — |

**建议路线**：A 先行跑通交互闭环（今晚可玩）→ 形象不满足再上 B → C 作为常驻玩法并行（它本来就是"写信"产品形态）。

---

## 附录 A：LLM 端点（已验证 2026-09-18）

- 内网：`http://192.168.3.6:38001/v1`　外网：`https://api.hintlab.cn/v1`
- 模型：`qwen3.8-27b`（`/v1/models` 与 chat 补全均实测通过，支持多模态）
- API Key：由用户保管，不入库；部署时写入运行环境的配置文件（加入 `.gitignore`）

## 附录 B：方案 A 部署记录（2026-09-18 已上线）

- 位置：`~/Open-LLM-VTuber`（conda env `vtuber`），启动：
  `conda activate vtuber && cd ~/Open-LLM-VTuber && python run_server.py`（edge-tts 需代理，先 `export https_proxy=http://127.0.0.1:7890`）
- **重要：代理必须配 no_proxy 排除内网 LLM**（2026-09-29 故障根因）：只设 `http_proxy` 时，访问 hintlab 内网地址 `192.168.3.6` 会被 clash 代理转发 → 网关 502 → 前端报 "Error calling the chat endpoint"。正确启动环境：
  `export https_proxy=http://127.0.0.1:7890 http_proxy=http://127.0.0.1:7890 no_proxy="192.168.3.6,127.0.0.1,localhost" NO_PROXY="192.168.3.6,127.0.0.1,localhost"`
- 访问：`http://<本机IP>:12393`，浏览器允许麦克风即可语音对话，也可文字输入
- 配置：`conf.yaml` —— LLM=hintlab `qwen3.8-27b`（temperature 0.8），ASR=SenseVoice(sherpa-onnx, CPU)，TTS=edge-tts 晓晓，人设"小离"
- 端到端已验证：文本/语音 → ASR → LLM（in-character 回复）→ TTS 音频流 ✓，正常一轮 8~20 秒
- **已知问题**：hintlab 为共享端点 + qwen3 思考型模型，偶发响应超 37 秒被网关 502（vtuber 会将错误文本念出）；缓解 = 人设已限制短回复、避开高峰。 pip 装依赖务必用清华镜像（官方源在本机极慢）：`uv pip install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple`

## 附录 C：部署后待验证项

- 麦克风采集在老机器上的延迟（ARECORD/PortAudio）
- edge-tts 在国内直连稳定性（失败时走本机代理 127.0.0.1:7890）
- Live2D 模型授权（框架自带示例皮，正式使用需自有素材）
