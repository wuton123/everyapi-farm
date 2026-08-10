#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 给全部账号（含3个新号）建session缓存：登录→存pickle
import json, urllib.request, urllib.error, urllib.parse, time, ssl, http.cookiejar, pickle

EVERY_API = 'https://app.everyapi.ai'
SESSION = r'C:\logo\every_session.pkl'
YC_KEY = '51db11dd89be4db71f1094be2cc20d647d14913a134978'
ACCOUNTS = [
    ('userbmpbu60x', 'EveryTest2026!x', '926号'),
    ('userqaj23y1v', 'EveryTest2026!x', '923号'),
    ('user53dq792u', 'EveryTest2026!x', '新号1'),
    ('user9l4jf7ak', 'EveryTest2026!x', '新号2'),
    ('userie4qo6ac', 'EveryTest2026!x', '新号3'),
]

def http_json(op, url, data=None, method=None, headers=None, timeout=25):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None, method=method)
    req.add_header('Content-Type', 'application/json')
    req.add_header('User-Agent', 'Mozilla/5.0')
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    ctx = ssl.create_default_context()
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

def make_opener():
    cj = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

def get_turnstile():
    body = {'clientKey': YC_KEY, 'task': {'type': 'TurnstileTaskProxyless',
        'websiteURL': 'https://app.everyapi.ai/signin', 'websiteKey': '0x4AAAAAADuU517TuIA9w9sb',
        'metadata': {'action': 'signin'}}}
    st, r = http_json(make_opener(), 'https://api.yescaptcha.com/createTask', body, 'POST')
    tid = r.get('taskId')
    if not tid:
        print('  createTask失败:', str(r)[:100], flush=True)
        return None
    for _ in range(40):
        time.sleep(3)
        st, r = http_json(make_opener(), 'https://api.yescaptcha.com/getTaskResult',
                          {'clientKey': YC_KEY, 'taskId': tid}, 'POST')
        if r.get('status') == 'ready' or r.get('solution'):
            return (r.get('solution') or {}).get('token')
    print('  getTaskResult超时', flush=True)
    return None

def cj_save(cj):
    return [[c.name, c.value, c.domain, c.path, c.secure, c.expires] for c in cj]

def cj_load(lst):
    cj = http.cookiejar.CookieJar()
    for name, value, domain, path, secure, expires in lst:
        try:
            ck = http.cookiejar.Cookie(0, name, value, None, False, domain, domain.startswith('.'), domain.startswith('.'), path, True, secure, expires, False, None, None, {})
            cj.set_cookie(ck)
        except Exception:
            pass
    return cj

# 加载已有缓存
try:
    with open(SESSION, 'rb') as f:
        raw = pickle.load(f)
    sessions = {}
    for u, v in raw.items():
        sessions[u] = {'cj': cj_load(v.get('cookies', [])), 'uid': v.get('uid')}
except Exception:
    sessions = {}

for username, password, tag in ACCOUNTS:
    if username in sessions and sessions[username].get('cj'):
        # 测试缓存是否有效
        s = sessions[username]
        op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(s['cj']))
        st, r = http_json(op, EVERY_API + '/api/user/self', None, 'GET',
                          headers={'EveryAPI-User-Id': str(s['uid']), 'Origin': EVERY_API})
        q = (r.get('data') or {}).get('quota')
        if q is not None:
            print(tag, '缓存有效 quota=', q, flush=True)
            continue
        print(tag, '缓存失效，重新登录', flush=True)
    print(tag, '登录中...', flush=True)
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    ts = get_turnstile()
    if not ts:
        print(tag, '打码失败，跳过', flush=True)
        continue
    st, r = http_json(op, EVERY_API + '/api/user/login?turnstile=' + urllib.parse.quote(ts),
                      {'username': username, 'password': password}, 'POST',
                      headers={'Origin': EVERY_API, 'Referer': EVERY_API + '/signin'})
    uid = (r.get('data') or {}).get('id')
    if not uid:
        print(tag, '登录失败:', json.dumps(r, ensure_ascii=False)[:120], flush=True)
        continue
    sessions[username] = {'cj': cj, 'uid': uid}
    # 转可pickle格式保存
    with open(SESSION, 'wb') as f:
        pickle.dump({u: {'cookies': cj_save(v['cj']), 'uid': v['uid']} for u, v in sessions.items()}, f)
    print(tag, '登录成功 uid=', uid, flush=True)
    time.sleep(1)

print('DONE, 缓存账号数:', len(sessions))