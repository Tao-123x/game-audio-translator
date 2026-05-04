# Game Audio Translator

实时游戏语音翻译工具。PC 抓取游戏音频，通过局域网推送到手机，手机显示英文→中文实时字幕。

## 项目结构

```
server/          # PC 端 Python 服务
  main.py        # 入口，串联所有模块
  audio_capture.py  # 音频抓取 (sounddevice)
  stt.py         # 语音识别 (Google Cloud STT)
  translator.py  # 翻译 (Google Cloud Translation)
  ws_server.py   # WebSocket + HTTP 服务
phone/
  index.html     # 手机端单文件 web 应用
test/
  *.py           # 各模块独立测试脚本
```

## 开发规则

1. 每个模块独立可测试，通过 queue/async 传递数据
2. 音频格式：PCM16 mono 16kHz
3. WebSocket 协议：JSON，type 字段区分 partial/final
4. 不使用前端框架，phone/index.html 是纯 HTML+CSS+JS 单文件
5. 不 hook 游戏进程，只在 OS 音频驱动层抓取
6. 所有配置走 .env，不硬编码
7. Python 代码用英文注释，仅在需要解释业务逻辑时加注释

## 运行方式

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 GCP 凭证路径

# 启动
python server/main.py

# 手机浏览器打开 http://<PC_IP>:8080
```

## GCP 配置要求

1. 创建 GCP 项目
2. 启用 Cloud Speech-to-Text API 和 Cloud Translation API
3. 创建服务账号，下载 JSON 密钥
4. 设置 GOOGLE_APPLICATION_CREDENTIALS 指向密钥文件
