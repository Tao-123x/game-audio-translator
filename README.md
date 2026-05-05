# Game Audio Translator

实时游戏语音翻译工具。PC 抓取游戏音频，通过局域网推送到手机，手机显示英文 → 中文实时字幕。

## 功能

- 系统音频抓取（Windows WASAPI loopback / macOS 麦克风）
- Google Cloud 流式语音识别（支持 partial/final）
- Google Cloud 翻译（英 → 中）
- WebSocket 实时推送到手机浏览器
- 自动重连（STT 断连后指数退避重试）

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 GCP 服务账号 JSON 密钥路径

# 3. 启动
python server/main.py

# 4. 手机浏览器打开
# http://<你的电脑IP>:8080
```

## 环境要求

- Python 3.10+
- Google Cloud 项目，启用以下 API：
  - Cloud Speech-to-Text API
  - Cloud Translation API
- GCP 服务账号 JSON 密钥

## 配置

在 `.env` 中设置（参考 `.env.example`）：

| 变量 | 必填 | 说明 |
|------|------|------|
| `GOOGLE_APPLICATION_CREDENTIALS` | 是 | GCP 服务账号 JSON 密钥路径 |
| `AUDIO_DEVICE_INDEX` | 否 | 音频设备索引，留空自动检测 |
| `WS_PORT` | 否 | WebSocket 端口，默认 8765 |
| `HTTP_PORT` | 否 | HTTP 端口，默认 8080 |

## 项目结构

```
server/
  main.py           # 入口，串联所有模块
  audio_capture.py  # 音频抓取（WASAPI loopback / mic）
  stt.py            # 流式语音识别 + 自动重连
  translator.py     # 翻译
  ws_server.py      # WebSocket + HTTP 服务
phone/
  index.html        # 手机端字幕 UI
test/
  test_audio_capture.py   # 音频抓取测试
  test_transcription.py   # STT + 翻译测试
```

## 测试

```bash
# 测试音频抓取（录 5 秒保存为 WAV）
python test/test_audio_capture.py

# 测试语音识别 + 翻译
python test/test_transcription.py
```
