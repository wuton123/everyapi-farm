#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 给已注册号补建key v2：建key→查列表拿id→取key
import json, time, random, urllib.request, urllib.error, urllib.parse, http.cookiejar

YC_KEY = '51db11dd89be4db71f1094be2cc20d647d14913a134978'
TS_KEY = '0x4AAAAAADuU517TuIA9w9sb'
API = 'https://app.everyapi.ai'
RESULT = r'C:\logo\batch_results.json'
GROUPS = ['grp_M3K-NEhOUc', 'grp_VOEupd841K', 'grp_ZLgC-rOo2v', 'grp_vNuaE45CEx']

def http_json(op, url, data=None, method=None, headers=None, timeout=25):
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

def get_ts():
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    body = {'clientKey': YC_KEY, 'task': {'type': 'TurnstileTaskProxyless',
        'websiteURL': API + '/signin', 'websiteKey': TS_KEY, 'metadata': {'action': 'signin'}}}
    st, r = http_json(op, 'https://api.yescaptcha.com/createTask', body, 'POST')
    tid = r.get('taskId')
    if not tid:
        return None
    for _ in range(30):
        time.sleep(3)
        st, r = http_json(op, 'https://api.yescaptcha.com/getTaskResult', {'clientKey': YC_KEY, 'taskId': tid}, 'POST')
        if r.get('status') == 'ready' or r.get('solution'):
            return (r.get('solution') or {}).get('token')
    return None

def fix_keys(acc):
    username = acc['username']
    ts = get_ts()
    if not ts:
        print(username, '打码失败', flush=True)
        return
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    st, r = http_json(op, API + '/api/user/login?turnstile=' + urllib.parse.quote(ts),
                      {'username': username, 'password': acc['password']}, 'POST',
                      headers={'Origin': API, 'Referer': API + '/signin'})
    uid = (r.get('data') or {}).get('id')
    if not uid:
        print(username, '登录失败:', json.dumps(r, ensure_ascii=False)[:150], flush=True)
        return
    H = {'EveryAPI-User-Id': str(uid), 'Origin': API}
    keys = acc.get('keys') or {}
    for g in GROUPS:
        if g in keys:
            continue
        name = 'auto-%d' % random.randint(1000, 9999)
        st, r = http_json(op, API + '/api/token/', {'name': name, 'unlimited_quota': True,
                          'expired_time': -1, 'model_limits_enabled': False, 'group': g}, 'POST', headers=H)
        if not r.get('success'):
            print(' ', username, g, '建key失败:', json.dumps(r, ensure_ascii=False)[:120], flush=True)
            continue
        # 查列表拿id（按name+group匹配）
        tid = None
        for page in range(1, 4):
            st, rl = http_json(op, API + '/api/token/?p=%d&size=20' % page, None, 'GET', headers=H)
            items = (rl.get('data') or {}).get('items') or []
            if not items:
                break
            for it in items:
                if it.get('name') == name and it.get('group') == g:
                    tid = it.get('id')
                    break
            if tid:
                break
        if not tid:
            print(' ', username, g, '列表找不到id', flush=True)
            continue
        st, r2 = http_json(op, API + '/api/token/%d/key' % tid, None, 'POST', headers=H)
        k = (r2.get('data') or {}).get('key')
        if k:
            keys[g] = k
            print(' ', username, g, 'OK', flush=True)
        else:
            print(' ', username, g, '取key失败:', json.dumps(r2, ensure_ascii=False)[:120], flush=True)
        time.sleep(0.5)
    acc['keys'] = keys
    print(username, 'keys:', len(keys), '个', flush=True)

with open(RESULT, 'r', encoding='utf-8') as f:
    results = json.load(f)
for acc in results:
    if not acc.get('keys'):
        try:
            fix_keys(acc)
            with open(RESULT, 'w') as f:
                json.dump(results, f, ensure_ascii=False, indent=1)
        except Exception as e:
            print(acc['username'], '异常:', e, flush=True)
print('DONE', flush=True)