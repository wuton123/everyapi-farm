#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 凤兮-上游额度同步 v5: 1分钟同步（cookie缓存复用，零打码）
# cookie以可pickle列表格式存储
import json, sqlite3, urllib.request, urllib.error, urllib.parse, time, ssl, http.cookiejar, pickle

DB = r'C:\newapi\one-api.db'
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
LOG = r'C:\logo\sync.log'

def log(msg):
    line = '[%s] %s\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), msg)
    try:
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write(line)
    except Exception:
        pass

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

def load_sessions():
    try:
        with open(SESSION, 'rb') as f:
            raw = pickle.load(f)
        sessions = {}
        for u, v in raw.items():
            sessions[u] = {'cj': cj_load(v.get('cookies', [])), 'uid': v.get('uid')}
        return sessions
    except Exception:
        return {}

def save_sessions(s):
    try:
        with open(SESSION, 'wb') as f:
            pickle.dump({u: {'cookies': cj_save(v['cj']), 'uid': v['uid']} for u, v in s.items()}, f)
    except Exception:
        pass

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
        return None
    for _ in range(40):
        time.sleep(3)
        st, r = http_json(make_opener(), 'https://api.yescaptcha.com/getTaskResult',
                          {'clientKey': YC_KEY, 'taskId': tid}, 'POST')
        if r.get('status') == 'ready' or r.get('solution'):
            return (r.get('solution') or {}).get('token')
    return None

def login_fresh(username, password):
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    ts = get_turnstile()
    if not ts:
        return None, None
    st, r = http_json(op, EVERY_API + '/api/user/login?turnstile=' + urllib.parse.quote(ts),
                      {'username': username, 'password': password}, 'POST',
                      headers={'Origin': EVERY_API, 'Referer': EVERY_API + '/signin'})
    uid = (r.get('data') or {}).get('id')
    if not uid:
        return None, None
    return cj, uid

def get_quota_cached(username, password, sessions):
    s = sessions.get(username)
    if s:
        cj = s.get('cj')
        uid = s.get('uid')
        if cj and uid:
            op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
            st, r = http_json(op, EVERY_API + '/api/user/self', None, 'GET',
                              headers={'EveryAPI-User-Id': str(uid), 'Origin': EVERY_API})
            q = (r.get('data') or {}).get('quota')
            if q is not None:
                return q
            log('%s cookie失效，重新登录' % username)
    cj, uid = login_fresh(username, password)
    if not cj or not uid:
        return None
    sessions[username] = {'cj': cj, 'uid': uid}
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    st, r = http_json(op, EVERY_API + '/api/user/self', None, 'GET',
                      headers={'EveryAPI-User-Id': str(uid), 'Origin': EVERY_API})
    return (r.get('data') or {}).get('quota')

def main():
    sessions = load_sessions()
    total = 0
    got = 0
    for username, password, tag in ACCOUNTS:
        q = get_quota_cached(username, password, sessions)
        if q is not None:
            total += q
            got += 1
            log('%s quota=%s' % (tag, q))
        time.sleep(0.5)
    save_sessions(sessions)
    if got == 0:
        log('FAIL: 上游额度获取失败')
        return
    db = sqlite3.connect(DB)
    c = db.cursor()
    c.execute('UPDATE users SET quota=?', (total,))
    n = c.rowcount
    db.commit()
    db.close()
    log('同步 quota=%d (got=%d) 用户数=%d' % (total, got, n))

if __name__ == '__main__':
    main()