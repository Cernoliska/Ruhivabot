import time
import pywikibot
from datetime import datetime, timedelta

WIKI_FAMILY = "wikipedia"
WIKI_LANG = "id"
TARGET_PAGE = "User:Ruhivabot/Switch"
UPDATE_INTERVAL_MINUTES = 30

VANDALISM_KEYWORDS = [
    "revert", "rv ", "long-term abuse", "long term abuse",
    "lta", "abuse", "rvv ", "undid",
    "membalikkan", "membatalkan", "mengembalikan"
]
NOT_VANDALISM_KEYWORDS = [
    "uaa", "good faith", "agf", "unsourced", "unreferenced",
    "self", "speculat", "original research", "rv tag",
    "typo", "incorrect", "format", "baik"
]

DEFCON_TEMPLATE = """{{#switch: __INDEX__
 |level=__LEVEL__
 |rpm=__RPM__
 |ttd=~~~
}}"""

site = pywikibot.Site(WIKI_LANG, WIKI_FAMILY)
site.login()

def is_revert_of_vandalism(comment):
    comment_lower = comment.lower()
    if any(kw in comment_lower for kw in NOT_VANDALISM_KEYWORDS):
        return False
    return any(kw in comment_lower for kw in VANDALISM_KEYWORDS)

def count_reverts_last(minutes=30):
    now = datetime.utcnow()
    start_time = now - timedelta(minutes=minutes)
    count = 0
    for change in site.recentchanges(
        reverse=True,
        start=start_time,
        end=now,
        changetype="edit"
    ):
        comment = change.get("comment", "")
        if is_revert_of_vandalism(comment):
            count += 1
    return count

def get_level_from_rpm(rpm):
    if rpm <= 0.19:
        return 5
    elif rpm <= 0.49:
        return 4
    elif rpm <= 0.99:
        return 3
    elif rpm <= 2.99:
        return 2
    else:
        return 1

def update_defcon_template(level, rpm, last_value):
    page = pywikibot.Page(site, TARGET_PAGE)
    template_text = (DEFCON_TEMPLATE
                     .replace("__INDEX__", "{{{1}}}")
                     .replace("__LEVEL__", str(level))
                     .replace("__RPM__", f"{rpm:.2f}"))
    try:
        text = page.text
    except pywikibot.exceptions.NoPage:
        print("[ERROR] Halaman target tidak ditemukan, membuat baru.")
        text = ""
    if text.strip() == template_text.strip():
        print("[INFO] Tidak ada perubahan, skip save.")
        return last_value
    try:
        page.text = template_text
        page.save(
            summary=f"[Bot Clerking]: memperbarui DEFCON: {rpm:.2f} RPM – DEFCON {level}",
            minor=True,
            bot=True
        )
        print(f"[INFO] Halaman DEFCON berhasil diperbarui → Level {level} ({rpm:.2f} RPM)")
    except pywikibot.exceptions.Error as e:
        print(f"[ERROR] Gagal menyimpan halaman: {e}")
    return (level, rpm)

def main():
    last_update_value = None
    while True:
        reverts = count_reverts_last(UPDATE_INTERVAL_MINUTES)
        avg_rpm = reverts / UPDATE_INTERVAL_MINUTES
        level = get_level_from_rpm(avg_rpm)
        timestamp = datetime.utcnow().strftime("[%Y-%m-%dT%H:%M:%SZ]")
        print(f"{timestamp} Jumlah revert {UPDATE_INTERVAL_MINUTES} menit terakhir: "
              f"{reverts} → Rata-rata {avg_rpm:.2f} RPM → Level {level}")
        last_update_value = update_defcon_template(level, avg_rpm, last_update_value)
        time.sleep(UPDATE_INTERVAL_MINUTES * 60)
if __name__ == "__main__":
    main()
