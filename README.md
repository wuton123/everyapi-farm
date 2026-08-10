# EveryAPI Farm 🚜

批量注册 EveryAPI 小号 → 自动建 API Key → 灌入中转站渠道 → 实时额度同步，**全自动流水线**（无需打开网页）。

## 为什么存在
EveryAPI (app.everyapi.ai) 是新 API 中转平台：新号注册送 250 万 quota（约 ¥36）+ 成就任务 + 每日签到（约 ¥5.5/天）。本工具把整套流程**逆向并固化**成命令行工具，配合中转站（new-api）镜像上游四分组，实现额度池无限扩容。

## 架构
```
farm_register.py ──> batch_results.json ──> import_channels.py ──> 凤兮(new-api) 渠道
      │                                        │
      └─ (注册+成就+签到, 每号≈300万quota)      └─ 4分组镜像: basic/stable/dedicated/gptpromo
sync_quota.py ──> 每1分钟: 上游总额 ──> 所有用户 quota (共享池)
```

## 快速开始
```bash
# 1. 配置 config（打码key/服务器信息）
cp config.example.json config.json && vi config.json

# 2. 批量注册 N 个号（每号≈1分钟）
python scripts/farm_register.py 5

# 3. 补建key（若上一步keys为空）
python scripts/fix_keys.py

# 4. 灌渠道
python scripts/import_channels.py

# 5. 更新 sync_quota.py 的 ACCOUNTS（加新号）→ 建cookie缓存
python scripts/build_sessions.py

# 6. 每1分钟自动同步（计划任务）
schtasks /create /tn sync_quota /sc minute /mo 1 /tr "python C:\logo\sync_quota.py"
```

## 核心逆向结论（勿随意改动）
| 步骤 | 端点 | 细节 |
|---|---|---|
| 发验证码 | `POST /api/verification?email=&turnstile=` | **query参数，body空** |
| 注册 | `POST /api/user/register?turnstile=` | body含 `turnstile` 字段 |
| 建 key | `POST /api/token/` | `unlimited_quota:true`（`remain_quota:-1` 被新版禁止） |
| 取 key | **`POST`** `/api/token/{id}/key` | 不是 GET！建key响应无id，需查列表按 name 匹配 |
| 查余额 | `GET /api/user/self` | Cookie + `EveryAPI-User-Id` 头（非 Bearer） |

分组映射（镜像上游）：
```
grp_M3K-NEhOUc → basic        grp_VOEupd841K → stable
grp_ZLgC-rOo2v → dedicated    grp_vNuaE45CEx → gptpromo
```

## 依赖
- Python 3.8+（服务器 Windows）
- YesCaptcha 打码 key（`YC_KEY`，也可换本地 Turnstile-Solver）
- mail.tm 临时邮箱（免费，自动）
- 目标中转站 new-api（DB 直插渠道）

## 踩坑速查
- Cloudflare 1010 拦截 python-urllib 调模型 → 测试用 curl / 或走中转站 Go 客户端
- CookieJar 不能 pickle（RLock）→ 缓存转 cookie 列表格式
- 打码限流（rate_limited）→ 用 cookie 缓存，只在失效时打码（≈¥0.01/天）
- 验证码 10 分钟有效、绑定发送时表单，报错需重新发码
- 注册间歇失败 → 脚本已自动重试（重新发码，最多3次）

## 相关开源
- [everyapi-ai/everyapi-ai](https://github.com/everyapi-ai/everyapi-ai) — EveryAPI 官方 CLI（查余额/登录）
- [Theyka/Turnstile-Solver](https://github.com/Theyka/Turnstile-Solver) — 本地免费 Turnstile 打码（可替代 YesCaptcha）

## ⚠️ 声明
本工具仅用于学习与自用额度管理。批量注册可能违反平台 ToS，风险自负；请控制注册节奏，避免对平台造成压力。