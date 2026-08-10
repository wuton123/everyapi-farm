#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 批量灌渠道：新号4个key → 凤兮4个镜像分组渠道（照抄926/923模式）
import json, sqlite3, time

DB = r'C:\newapi\one-api.db'
RESULT = r'C:\logo\batch_results.json'

# 上游分组顺序 → 凤兮镜像渠道group
GROUP_MAP = [
    ('grp_M3K-NEhOUc', 'everyapi-basic', 'deepseek-v4-flash,MiniMax-M3,ark-code-latest', 'deepseek-v4-flash'),
    ('grp_VOEupd841K', 'everyapi-stable', 'deepseek-v4-flash,MiniMax-M3,ark-code-latest', 'deepseek-v4-flash'),
    ('grp_ZLgC-rOo2v', 'everyapi-dedicated', 'deepseek-v4-flash,MiniMax-M3,ark-code-latest', 'deepseek-v4-flash'),
    ('grp_vNuaE45CEx', 'everyapi-gptpromo', 'gpt-4o,gpt-4o-mini,gpt-5,gpt-5-mini,gpt-5-nano,gpt-5.5,gpt-5.6-sol,gpt-5.6-terra,gpt-5.6-luna', 'gpt-5.6-sol'),
]

with open(RESULT, 'r', encoding='utf-8') as f:
    results = json.load(f)

db = sqlite3.connect(DB)
c = db.cursor()
now = int(time.time())
total = 0
for acc in results:
    username = acc['username']
    keys = acc.get('keys') or {}
    for grp, group_name, models, test_model in GROUP_MAP:
        k = keys.get(grp)
        if not k:
            print(username, grp, '无key，跳过')
            continue
        short = group_name.replace('everyapi-', '')
        ch_name = 'everyapi-%s-%s' % (short, username)
        c.execute("SELECT id FROM channels WHERE name=?", (ch_name,))
        if c.fetchone():
            print(username, group_name, '已存在，跳过')
            continue
        c.execute('INSERT INTO channels (name,type,key,base_url,test_model,models,"group",status,created_time,weight) VALUES (?,?,?,?,?,?,?,?,?,?)',
                  (ch_name, 1, k, 'https://app.everyapi.ai', test_model, models, group_name, 1, now, 0))
        total += c.rowcount
        print(username, '->', group_name, 'OK')
db.commit()
db.close()
print('DONE, 共插入', total, '个渠道')