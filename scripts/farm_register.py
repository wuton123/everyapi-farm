#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# EveryAPI 批量注册 v4: 前端逆向正确流程
# ①verification: POST /api/verification?email=&turnstile= (body空)
# ②register: POST /api/user/register?turnstile= body含turnstile
import json, time, random, urllib.request, urllib.error, urllib.parse, string, http.cookiejar, sys, re

YC_KEY = '51db11dd89be4db71f1094be2cc20d647d14913a134978'
TS_KEY = '0x4AAAAAADuU517TuIA9w9sb'
API = 'https://app.everyapi.ai'
MAIL_API = 'https://api.mail.tm'
PASS = 'EveryTest2026!x'
GROUPS = ['grp_M3K-NEhOUc', 'grp_VOEupd841K', 'grp_ZLgC-rOo2v', 'grp_vNuaE45CEx']
OUT = r'C:\logo\batch_results.json'

def log(msg):
    print('[%s] %s' % (time.strftime('%H:%M:%S'), msg), flush=True)

def make_opener(cj=None):
    if cj is None:
        cj = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

def http_json(op, url, data=None, method=None, headers=None, timeout=30):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None, method=method)
    req.add_header('Content-Type', 'application/json')
    req.add_header('User-Agent', 'Mozilla/5.0')
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with op.open(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode('utf-8', 'replace'))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode('utf-8', 'replace'))
        except Exception:
            return e.code, {}
    except Exception as e:
        return 0, {'error': str(e)}

def get_turnstile(action='signup'):
    body = {'clientKey': YC_KEY, 'task': {'type': 'TurnstileTaskProxyless',
        'websiteURL': API + '/signup', 'websiteKey': TS_KEY,
        'metadata': {'action': action}}}
    st, r = http_json(make_opener(), 'https://api.yescaptcha.com/createTask', body, 'POST')
    tid = r.get('taskId')
    if not tid:
        return None
    for _ in range(40):
        time.sleep(3)
        st, r = http_json(make_opener(), 'https://api.yescaptcha.com/getTaskResult',
                          {'clientKey': YC_KEY, 'taskId': tid}, 'POST')
        if r.get('status') == 'ready' or r.get('solution'):
            return (r.get('solution') or {}).get('token')
    return None

def mail_reg():
    st, r = http_json(make_opener(), MAIL_API + '/domains', None, 'GET')
    domain = (r.get('hydra:member') or [{}])[0].get('domain')
    if not domain:
        return None, None
    addr = ''.join(random.choices(string.digits, k=11)) + '@' + domain
    pw = 'TmpMail2026!x'
    st, r = http_json(make_opener(), MAIL_API + '/accounts', {'address': addr, 'password': pw}, 'POST')
    if st != 201:
        return None, None
    st, r = http_json(make_opener(), MAIL_API + '/token', {'address': addr, 'password': pw}, 'POST')
    tok = r.get('token') or (r.get('data') or {}).get('token')
    return addr, tok

def mail_wait_code(addr, tok, timeout=120):
    hdrs = {'Authorization': 'Bearer ' + tok}
    start = time.time()
    while time.time() - start < timeout:
        st, r = http_json(make_opener(), MAIL_API + '/messages?page=1', None, 'GET', headers=hdrs)
        msgs = r.get('hydra:member') or []
        if msgs:
            msg = msgs[0]
            mst, mr = http_json(make_opener(), MAIL_API + '/messages/' + msg['id'], None, 'GET', headers=hdrs)
            t = mr.get('text') or ''
            if isinstance(t, list):
                t = '\n'.join(str(x) for x in t)
            h = mr.get('html') or ''
            if isinstance(h, list):
                h = '\n'.join(str(x) for x in h)
            body = t + h
            m = re.search(r'(\d{4,8})', body)
            if m:
                return m.group(1)
        time.sleep(6)
    return None

def register_one(idx):
    log('=== 注册第%d个 ===' % idx)
    addr, mtok = mail_reg()
    if not addr:
        log(' 邮箱失败'); return None
    log(' 邮箱: %s' % addr)
    username = 'user' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    # ① 打码 + 发验证码(query参数)
    ts = get_turnstile('signup')
    if not ts:
        log(' 打码失败'); return None
    url = API + '/api/verification?email=%s&turnstile=%s' % (urllib.parse.quote(addr), urllib.parse.quote(ts))
    st, r = http_json(make_opener(), url, None, 'POST',
                      headers={'Origin': API, 'Referer': API + '/signup'})
    log(' 发验证码: %s' % str(r)[:80])
    # ② 收码
    code = mail_wait_code(addr, mtok)
    if not code:
        log(' 验证码超时'); return None
    log(' 验证码: %s' % code)
    # ③ 注册（新打码，body含turnstile）——失败自动重试（最多3次）
    ok = False
    for attempt in range(3):
        ts2 = get_turnstile('signup')
        if not ts2:
            continue
        st, r = http_json(make_opener(), API + '/api/user/register?turnstile=' + urllib.parse.quote(ts2),
                          {'username': username, 'password': PASS, 'email': addr,
                           'verification_code': code, 'turnstile': ts2, 'aff_code': ''}, 'POST',
                          headers={'Origin': API, 'Referer': API + '/signup'})
        if r.get('success'):
            ok = True
            break
        log(' 注册尝试%d失败: %s' % (attempt + 1, json.dumps(r, ensure_ascii=False)[:100]))
        # 验证码失效则重新发码
        if 'verification' in json.dumps(r).lower() or 'incorrect' in json.dumps(r).lower():
            tsx = get_turnstile('signup')
            urlx = API + '/api/verification?email=%s&turnstile=%s' % (urllib.parse.quote(addr), urllib.parse.quote(tsx))
            http_json(make_opener(), urlx, None, 'POST', headers={'Origin': API, 'Referer': API + '/signup'})
            code = mail_wait_code(addr, mtok, timeout=60)
            if not code:
                break
            log(' 重新收码: %s' % code)
        time.sleep(2)
    if not ok:
        log(' 注册最终失败')
        return None
    log(' 注册成功: %s' % username)
    # ④ 登录
    ts3 = get_turnstile('signin')
    if not ts3:
        return None
    cj = http.cookiejar.CookieJar()
    op = make_opener(cj)
    st, r = http_json(op, API + '/api/user/login?turnstile=' + urllib.parse.quote(ts3),
                      {'username': username, 'password': PASS}, 'POST',
                      headers={'Origin': API, 'Referer': API + '/signin'})
    uid = (r.get('data') or {}).get('id')
    if not uid:
        log(' 登录失败'); return None
    log(' 登录 uid=%d' % uid)
    H = {'EveryAPI-User-Id': str(uid), 'Origin': API}
    # ⑤ 建key
    keys = {}
    for g in GROUPS:
        st, r = http_json(op, API + '/api/token/', {'name': 'auto-%d' % random.randint(1000, 9999),
                          'unlimited_quota': True, 'expired_time': -1, 'model_limits_enabled': False,
                          'group': g}, 'POST', headers=H)
        tid = (r.get('data') or {}).get('id')
        if tid:
            st, r2 = http_json(op, API + '/api/token/%d/key' % tid, None, 'GET', headers=H)
            k = (r2.get('data') or {}).get('key')
            if k:
                keys[g] = k
    log(' 建key: %d个' % len(keys))
    # ⑥ 成就+签到
    st, r = http_json(op, API + '/api/achievements/sync', None, 'POST', headers=H)
    ts4 = get_turnstile('checkin')
    if ts4:
        st, r = http_json(op, API + '/api/user/checkin?turnstile=' + urllib.parse.quote(ts4),
                          None, 'POST', headers=H)
    # ⑦ 最终quota
    st, r = http_json(op, API + '/api/user/self', None, 'GET', headers=H)
    q = (r.get('data') or {}).get('quota')
    log(' 最终quota: %s' % q)
    return {'username': username, 'password': PASS, 'uid': uid, 'quota': q, 'keys': keys}

def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    results = []
    try:
        with open(OUT, 'r') as f:
            results = json.load(f)
    except Exception:
        pass
    for i in range(n):
        try:
            r = register_one(i + 1)
            if r:
                results.append(r)
                with open(OUT, 'w') as f:
                    json.dump(results, f, ensure_ascii=False, indent=1)
        except Exception as e:
            log(' 异常: %s' % e)
        time.sleep(2)
    log('=== 完成，共 %d 个成功 ===' % len(results))

if __name__ == '__main__':
    main()