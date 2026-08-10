# EveryAPI Farm — 批量注册 + 凤兮中转站灌渠道全自动流水线

You are an expert in the EveryAPI (app.everyapi.ai) platform automation. This skill contains the complete, reverse-engineered workflow for: bulk account registration (temp email + Turnstile solving), API key creation, channel import into a Fengxi (new-api) relay, and real-time quota sync. **Always consult this skill before touching EveryAPI scripts** — every endpoint detail here was hard-won through source-code analysis.

## Trigger
- 批量注册 EveryAPI 小号 / 灌渠道 / 同步额度 / 凤兮池子扩容 / everyapi farm

## 服务器环境（腾讯云 Windows）
- SSH: `sshpass -p '4EVc5/f8H2T(yC' ssh -o StrictHostKeyChecking=no Administrator@124.222.129.4 "chcp 65001 >nul & ..."`
- 凤兮(new-api): C:\newapi\ (DB: C:\newapi\one-api.db, 端口3000, 计划任务 newapi_run)
- 脚本目录: C:\logo\ (batch_results.json / sync_quota.py / every_session.pkl / sync.log)
- 隧道: cloudflared (C:\cloudflared, 计划任务 cf_tunnel), 公网: https://api.fengxi.ltd

## 核心 API（逆向结论，勿改！）
| 步骤 | 端点 | 关键细节 |
|---|---|---|
| 打码 | POST https://api.yescaptcha.com/createTask | TurnstileTaskProxyless; websiteKey=`0x4AAAAAADuU517TuIA9w9sb`; metadata.action=signup/signin/checkin |
| 临时邮箱 | https://api.mail.tm | /domains→/accounts→/token→/messages?page=1→/messages/{id}(text+html找6位数字) |
| 发验证码 | POST /api/verification?email=xxx&turnstile=xxx | **query参数，body空！** (body传参报Invalid parameters) |
| 注册 | POST /api/user/register?turnstile=xxx | body={username,password,email,verification_code,**turnstile**,aff_code:''}; 用户名≤20字符 |
| 登录 | POST /api/user/login?turnstile=xxx | body={username,password}; 返回data.id=uid |
| 建key | POST /api/token/ | body={name, **unlimited_quota:true**(remain_quota:-1被拒!), expired_time:-1, model_limits_enabled:false, group} |
| 取key | **POST** /api/token/{id}/key | **POST不是GET!** 响应data.key=完整key |
| 找key id | GET /api/token/?p=1&size=20 | 建key响应无id→按name+group匹配列表items |
| 成就 | POST /api/achievements/sync | 领注册任务额度 |
| 签到 | POST /api/user/checkin?turnstile=xxx | 每天约+37万quota |
| 查余额 | GET /api/user/self | 需 **Cookie + EveryAPI-User-Id头** (非Bearer) |

## 分组映射（镜像上游四组）
```
grp_M3K-NEhOUc → everyapi-basic   (deepseek-v4-flash,MiniMax-M3,ark-code-latest)
grp_VOEupd841K → everyapi-stable  (同上)
grp_ZLgC-rOo2v → everyapi-dedicated (同上)
grp_vNuaE45CEx → everyapi-gptpromo (gpt-4o..gpt-5.6-luna, test_model=gpt-5.6-sol)
```
渠道名: `everyapi-{组}-{用户名}`, type=1, base_url=https://app.everyapi.ai

## 凤兮灌渠道（DB直接INSERT）
```sql
INSERT INTO channels (name,type,key,base_url,test_model,models,"group",status,created_time,weight)
VALUES (?,1,?, 'https://app.everyapi.ai', test_model, models, group_name, 1, now, 0);
```

## 额度同步（sync_quota.py v5）
- 每1分钟计划任务 sync_quota
- **Cookie 缓存**: C:\logo\every_session.pkl 存 {user:{cookies:[[name,value,domain,path,secure,expires]...],uid}}
- **CookieJar 不能 pickle**(RLock) → 必须转列表格式！(cj_save/cj_load)
- 所有用户 quota 统一 UPDATE = 上游总额 (全站共享池)
- 打码只在cookie失效时(≈¥0.01/天)

## 踩坑记录（血泪）
1. **Cloudflare 1010** 拦截 python-urllib 调 /v1/chat/completions (TLS指纹) → 测试用 **curl**；凤兮Go客户端不受影响
2. **打码限流** (rate_limited) → 连续注册间隔拉长；建缓存后零打码
3. **验证码10分钟有效**、绑定发送时表单(中途改字段即失效)、错误后需重新发码
4. 注册间歇性失败 "Verification code is incorrect" → 自动重试(重新发码,最多3次)
5. **taskkill /IM python.exe /F 会杀 status_server/stat服务** → 重启 schtasks /run /tn stat_server
6. token 软删除(deleted_at非空)后调用401 → 用 tokens WHERE deleted_at IS NULL
7. new-api token校验: DB存不带sk-的secret, 调用时Bearer sk-{secret}; id4旧格式(sk-前缀)不匹配
8. 渠道test_model: basic/stable/dedicated=deepseek-v4-flash, gptpromo=gpt-5.6-sol
9. gpt-5.6系列必须 stream=true, 否则 "Stream must be set to true"
10. ark-code-latest 上游需Agent计划→用户调用报错→文档已标注"暂不可用"

## 脚本清单 (C:\logo\ 或本技能 scripts/)
- `every_batch2.py` = every_batch4.py 部署名: 批量注册(count参数) → batch_results.json
- `fix_keys2.py`: 给已有号补建key (unlimited_quota+POST取key)
- `import_channels.py`: 读batch_results.json→灌渠道(DB INSERT)
- `sync_quota.py` v5: 1分钟同步(ACCOUNTS含全部小号)
- `build_sessions.py`: 给账号建cookie缓存(打码登录一次)
- `status_server.py`: stat.fengxi.ltd仪表盘(8089, 计划任务stat_server)

## 执行流程
1. `python every_batch2.py N` → 注册N个号(每号≈300万quota≈¥42, 含注册+成就+签到)
2. 失败号自动重试; 完成后 `python fix_keys2.py` 补key(若keys空)
3. `python import_channels.py` → 新号key灌入凤兮四组渠道
4. 更新 sync_quota.py ACCOUNTS(加新号) → schtasks /run /tn sync_quota
5. 重启凤兮: schtasks /end /tn newapi_run & schtasks /run /tn newapi_run
6. 验证: curl -X POST https://api.fengxi.ltd/v1/chat/completions (Bearer sk-{secret}) model=deepseek-v4-flash
7. 检查: C:\logo\sync.log 每1分钟 quota=总池子

## 开源替代方案
- **everyapi CLI** (github.com/everyapi-ai/everyapi-ai): 官方命令行, auth status查余额/登录/use工具
- **Turnstile-Solver** (github.com/Theyka/Turnstile-Solver, 898星): patchright本地免费打码, 可替代yescaptcha降成本
- 本技能即开源项目 everyapi-farm (已推GitHub wuton123/everyapi-farm)
