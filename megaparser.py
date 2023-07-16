#!/usr/bin/env python3

import configparser
import urllib.request
import csv
import sys
import re
import os

db = []
db_fields = []
counter = 0
total = 0

def dump_db():
    w = csv.DictWriter(sys.stdout, fieldnames=db_fields, delimiter='\t')
    w.writeheader()
    for row in db:
        w.writerow(row)

def asciify(s):
    s = s.replace(u"\u2013", "-")
    s = re.sub("[^\x20-\x7F]"," ", s)
    s = re.sub(" +"," ", s)
    return s.strip()

def tagify(s):
    s = asciify(s)
    s = re.sub("[^a-zA-Z0-9-]","_", s)
    return s

def get_page(section, url, key, enc):
    global counter, total
    fname = "download/%s/%s.html" % (section, tagify(key))
    if os.path.exists(fname):
        buf = open(fname,'rb').read()
    else:
        sys.stderr.write("%s\nDownloading page %d of %d...\n" % (url, counter, total))
        buf = wget(url, fname)
    counter += 1
    return buf.decode(enc)

def wget(url, fname):
    req = urllib.request.Request(url, None, {'User-Agent':'megaparser'})
    response = urllib.request.urlopen(req)
    buf = response.read()
    d = os.path.dirname(fname)
    if not os.path.exists(d):
        os.makedirs(d)
    fp = open(fname, "wb")
    fp.write(buf)
    fp.close()
    return buf

def get_var(conf, sec, var):
    try:
        return conf.get(sec, var)
    except:
        return ""

def get_keys(reg, text):
    keys = []
    for m in re.finditer(reg, text, re.MULTILINE | re.DOTALL):
        if len(m.groups()):
            k = m.group(1)
            if k not in keys:
                keys.append(k)
    return keys

def get_values(conf, sec, text, url, param=''):
    global db_fields
    res = {}
    for var in db_fields:
        reg = get_var(conf, sec, var)
        vals = []
        if reg:
            for m in re.finditer(reg, text, re.MULTILINE | re.DOTALL):
                if m and len(m.groups()):
                    val = m.group(1)
                    val = val.replace('\n','\\n')
                    vals.append(val)
                res[var] = val
        if '$1' in reg:
            res[var] = param
    if res:
        for var in db_fields:
            if var not in res.keys():
                res[var] = ""
        if "url" in db_fields:
            res["url"] = url
        db.append(res)

def get_fields(conf, sec):
    res = []
    for i in conf.items(sec):
        if i[0] not in ["url", "param", "template", "alias", "encoding"]:
            res.append(i[0])
    return res

def process(conf, sec, text, parent, url, param=''):
    global db_fields
    global total
    get_values(conf, sec, text, url, param)
    reg = get_var(conf, sec, "param")
    if reg:
        keys = get_keys(reg, text)
        total += len(keys)
        sec = get_var(conf, sec, "template")
        if sec:
            dbf = get_fields(conf, sec)
            db_fields = dbf if len(dbf) else db_fields
            for key in keys:
                parse(conf, sec, key, parent)

def parse(conf, sec, key="index", parent=""):
    global db_fields
    if parent == "":
        parent = sec
    enc = get_var(conf, sec, 'encoding') or 'utf-8'
    url = get_var(conf, sec, "url").replace("$1", key)
    text = get_page(parent, url, sec+'_'+key, enc)
    alias = get_var(conf, sec, "alias")
    if alias:
        process(conf, alias, text, parent, url)
        dbf = get_fields(conf, alias)
        db_fields = dbf if len(dbf) else db_fields
        get_values(conf, sec, text, url)
    process(conf, sec, text, parent, url, key)

if __name__ == '__main__':
    conf =  configparser.ConfigParser()
    conf.read("megaparser.ini", encoding='utf-8')
    section = get_var(conf, "settings", "default")
    parse(conf, section)
    dump_db()
