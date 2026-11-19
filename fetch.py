# -*- coding: utf-8 -*-
"""poe.ninja -> 靜態行情頁資料抓取器
純 HTTP，無瀏覽器依賴，可在 GitHub Actions / 任意伺服器執行。
輸出 data.json（給 index.html 讀取）+ index.html（自包含內嵌資料）
"""
import json, gzip, sys, os, statistics, time, re, unicodedata
import urllib.request
import urllib.parse

LEAGUE = os.environ.get("POE_LEAGUE", "Covens")
OUT_DIR = os.environ.get("OUT_DIR", ".")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
BASE = "https://poe.ninja/poe1/api/economy"

EX_TYPES = ["Currency", "Fragment", "Scarab", "Fossil", "Essence", "DivinationCard",
            "Oil", "DeliriumOrb", "Artifact", "Tattoo", "Omen", "Vial",
            "Incubator", "Runegraft", "AllflameEmber"]
ST_TYPES = ["UniqueWeapon", "UniqueArmour", "UniqueAccessory", "UniqueJewel",
            "UniqueFlask", "SkillGem", "BaseType", "ClusterJewel", "Map", "Invitation"]

CAT_ZH = {
    "Currency": "通貨", "Fragment": "碎片", "Scarab": "聖甲蟲", "Fossil": "化石",
    "Essence": "精華", "DivinationCard": "命運卡", "Oil": "油瓶", "DeliriumOrb": "譫妄玉",
    "Artifact": "聖物", "Tattoo": "紋身", "Omen": "預兆", "Vial": "藥瓶",
    "Incubator": "孵化器", "Runegraft": "符文嫁接", "AllflameEmber": "全焰餘燼",
    "UniqueWeapon": "傳奇武器", "UniqueArmour": "傳奇護甲", "UniqueAccessory": "傳奇飾品",
    "UniqueJewel": "傳奇珠寶", "UniqueFlask": "傳奇藥劑", "SkillGem": "技能寶石",
    "BaseType": "基底", "ClusterJewel": "星團珠寶", "Map": "地圖", "Invitation": "邀請函",
}

# ---------- 繁中譯名（zh_tw.json 與本檔同目錄；缺失時整頁回退英文，不影響抓取）----------
_ZH_MAP, _ZH_CJ = {}, {}
try:
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "zh_tw.json"), encoding="utf-8") as _f:
        _zd = json.load(_f)
        _ZH_MAP = _zd.get("map", {})
        _ZH_CJ = _zd.get("cjtpl", {})
    print(f"[zh] 譯名表載入 {len(_ZH_MAP)} 條 / 星團詞綴 {len(_ZH_CJ)} 條")
except Exception as _e:
    print(f"[zh] 譯名表未載入（將顯示英文）: {_e}")

_ZH_PFX = {"Foulborn": "穢生", "Replica": "贗品", "Legacy": "遺產",
           "Synthesised": "追憶", "Fractured": "破裂", "Relic": "聖物"}
_ZH_PRE = re.compile(r"^(Foulborn|Replica|Legacy|Synthesised|Fractured|Relic)\s+(.+)$")
_ZH_PAR = re.compile(r"^(.+?) \((.+)\)$")
_ZH_NUM = re.compile(r"[+-]?\d+(?:\.\d+)?")


def znorm(s):
    s = urllib.parse.unquote(str(s))
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s.lower())


def zh_name(n):
    """英文物品名 -> 繁中；詞綴式長句不在此處理。"""
    if not n:
        return None
    hit = _ZH_MAP.get(znorm(n))
    if hit:
        return hit
    m = _ZH_PRE.match(n)
    if m:
        inner = zh_name(m.group(2))
        if inner:
            return _ZH_PFX[m.group(1)] + "．" + inner
    m = _ZH_PAR.match(n)
    if m:
        a, b = zh_name(m.group(1)), zh_name(m.group(2))
        if a and b:
            return f"{a}（{b}）"
    return None


def zh_tpl(n):
    """星團珠寶詞綴長句：數值換成 # 後按模板查表。"""
    if not n:
        return None
    return _ZH_CJ.get(znorm(_ZH_NUM.sub("#", n)))


def get(url, retry=3):
    last = None
    for i in range(retry):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA, "Accept": "application/json",
                "Accept-Encoding": "gzip", "Referer": "https://poe.ninja/",
            })
            with urllib.request.urlopen(req, timeout=40) as r:
                raw = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                return json.loads(raw)
        except Exception as e:
            last = e
            time.sleep(2 + i * 3)
    raise last


def chg_of(spark):
    if not spark:
        return None
    v = spark.get("totalChange")
    return None if v is None else float(v)


def fetch_exchange(t):
    d = get(f"{BASE}/exchange/current/overview?league={LEAGUE}&type={t}")
    items = {i["id"]: i for i in d.get("items", [])}
    out = []
    for ln in d.get("lines", []):
        it = items.get(ln.get("id"))
        if not it:
            continue
        pv = ln.get("primaryValue")
        vpv = ln.get("volumePrimaryValue")
        vol = None
        if pv and vpv:
            try:
                vol = round(float(vpv) / float(pv), 2)   # 24h 估算成交量(件) = 成交額 / 單價
            except Exception:
                vol = None
        out.append({
            "n": it.get("name") or ln.get("id"),
            "b": it.get("detailsId") or "",
            "c": t,
            "p": None if pv is None else float(pv),
            "chg": chg_of(ln.get("sparkline")),
            "vol": vol,
            "vk": "t24",
            "icon": it.get("image") or "",
        })
    return out


def fetch_stash(t):
    d = get(f"{BASE}/stash/current/item/overview?league={LEAGUE}&type={t}")
    out = []
    for ln in d.get("lines", []):
        cv = ln.get("chaosValue")
        out.append({
            "n": ln.get("name") or "",
            "b": ln.get("baseType") or ln.get("variant") or "",
            "v": ln.get("variant") or "",
            "c": t,
            "p": None if cv is None else float(cv),
            "chg": chg_of(ln.get("sparkLine")),
            "vol": float(ln.get("count") or ln.get("listingCount") or 0),
            "icon": ln.get("icon") or "",
        })
    return out


def median(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 2) if xs else None


def main():
    rows, errors = [], []
    for t in EX_TYPES:
        try:
            r = fetch_exchange(t)
            rows += r
            print(f"[ex] {t}: {len(r)}")
        except Exception as e:
            errors.append(f"{t}: {e}")
            print(f"[ex] {t} FAIL {e}")
    for t in ST_TYPES:
        try:
            r = fetch_stash(t)
            rows += r
            print(f"[st] {t}: {len(r)}")
        except Exception as e:
            errors.append(f"{t}: {e}")
            print(f"[st] {t} FAIL {e}")

    # 繁中譯名：n/b 保留英文原文，z/bz 存中文（前端優先顯示中文，英文作副行）
    zh_hit = 0
    for r in rows:
        n = r.get("n") or ""
        z = zh_name(n) or (zh_tpl(n) if r.get("c") == "ClusterJewel" else None)
        if z and z != n:
            r["z"] = z
            zh_hit += 1
        b = r.get("b") or ""
        bz = zh_name(b)
        if bz and bz != b:
            r["bz"] = bz
    print(f"[zh] 名稱譯中 {zh_hit}/{len(rows)} = {zh_hit / max(len(rows), 1) * 100:.1f}%")

    # 神聖石錨點
    div = next((r for r in rows if r["c"] == "Currency" and r["b"] == "divine-orb"), None)
    if not div:
        div = next((r for r in rows if r["n"] == "Divine Orb"), None)
    dprice = div["p"] if div else None
    dchg = div["chg"] if div and div["chg"] is not None else 0.0
    anchor = 1 + dchg / 100.0

    # 真實漲跌（剔除神聖石通膨）
    for r in rows:
        r["real"] = None if r["chg"] is None else round(((1 + r["chg"] / 100.0) / anchor - 1) * 100, 2)

    # 類別統計
    cats = {}
    for r in rows:
        cats.setdefault(r["c"], []).append(r)
    stats = []
    for c, rs in cats.items():
        chg_all = [x["real"] for x in rs if x["real"] is not None]
        chg_mv = [x["real"] for x in rs if x["real"] is not None and abs(x["chg"] or 0) > 0.01]
        stats.append({
            "c": c, "zh": CAT_ZH.get(c, c), "n": len(rs),
            "n_mv": len(chg_mv),
            "med_all": median(chg_all),
            "med_mv": median(chg_mv),
            "up": sum(1 for x in chg_all if x > 0),
            "down": sum(1 for x in chg_all if x < 0),
        })
    stats.sort(key=lambda s: -s["n"])

    # 精簡明細：有價格且有成交量，按類別保留前 300（依 |real|*ln(vol) 影響力排序）
    import math
    for r in rows:
        r["_score"] = abs(r["real"] or 0) * math.log10(max(r["vol"], 1) + 10)
    keep = []
    for c, rs in cats.items():
        rs2 = [x for x in rs if x["p"] is not None and x["vol"] > 0]
        rs2.sort(key=lambda x: -x["_score"])
        keep += rs2[:300]
    for r in keep:
        r.pop("_score", None)

    payload = {
        "league": LEAGUE,
        "updated_at": time.strftime("%Y-%m-%d %H:%M", time.gmtime(time.time() + 8 * 3600)),
        "ts": int(time.time() * 1000),
        "divine_price": dprice,
        "divine_chg7d": dchg,
        "total_items": len(rows),
        "stats": stats,
        "rows": keep,
        "errors": errors,
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "data.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))

    # 產出自包含靜態頁
    tpl_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "template.html")
    if os.path.exists(tpl_path):
        with open(tpl_path, encoding="utf-8") as f:
            tpl = f.read()
        inline = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
        html = tpl.replace("__LEAGUE__", LEAGUE).replace("__DATA__", inline)
        with open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8") as f:
            f.write(html)
        print("index.html 已生成")
    print(f"\nrows={len(rows)} kept={len(keep)} divine={dprice} dchg={dchg} stats={len(stats)}")
    print("errors:", errors)


if __name__ == "__main__":
    main()
