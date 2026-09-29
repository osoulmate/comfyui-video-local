#!/usr/bin/env bash
# 停止 ComfyUI 服务：先 SIGINT（等价 Ctrl+C，触发优雅退出、尽量保留历史记录），
# 20 秒未退出再升级 SIGKILL。用法: bash scripts/stop_comfyui.sh [PORT]（默认 8188）
PORT="${1:-${PORT:-8188}}"
PID="$(ss -tlnp 2>/dev/null | grep -E ":${PORT}\b" | grep -oP 'pid=\K[0-9]+' | head -1)"

if [ -z "$PID" ]; then
  echo "端口 $PORT 没有正在运行的服务。"
  exit 0
fi

echo "停止 PID $PID (端口 $PORT) ..."
kill -INT "$PID"
for _ in $(seq 1 20); do
  kill -0 "$PID" 2>/dev/null || { echo "已停止。"; exit 0; }
  sleep 1
done
echo "20 秒未退出，发送 SIGKILL 强制结束。"
kill -KILL "$PID" 2>/dev/null
sleep 1
kill -0 "$PID" 2>/dev/null && { echo "仍未能停止，请手动检查: kill -9 $PID" >&2; exit 1; }
echo "已强制停止。"
