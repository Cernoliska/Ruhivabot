import re
import time
from datetime import datetime, timedelta
import pywikibot

WIKI_FAMILY = "wikipedia"
WIKI_LANG = "id"
PAGES = [
    "Wikipedia:Intervensi_pengurus_terhadap_vandalisme", 
    "Wikipedia:Permintaan_perhatian_nama_pengguna",    
]
COMMENT_LIFETIME = timedelta(hours=1) 
UPDATE_INTERVAL = 60 * 60

PATTERN_IPTV = re.compile(r"\{\{\s*(?:[Vv]andal-m|[Pp]enggunavandal)\s*\|\s*(?P<user>[^\}|]+)")
PATTERN_UAA  = re.compile(r"\{\{\s*[Uu]ser-uaa\s*\|\s*(?P<user>[^\}|]+)")

FINISH_KEYWORDS = [
    "{{done", "{{selesai", "{{not done", "{{notdone",
    "{{tidak dilanjutkan", "{{tidak selesai",
    "{{iptv|block", "{{iptv|blocked", "{{iptv|d",
    "{{iptv|ditolak", "{{iptv|bukan", "{{iptv|bukanvandal", "{{iptv|ta",
    "{{iptv|tidakaktif", "{{iptv|ts", "{{iptv|tidakselesai"
]
site = pywikibot.Site(WIKI_LANG, WIKI_FAMILY)
site.login()

COMMENT_TRACKER = {}

def has_finish_comment(lines: list[str], start_index: int) -> bool:
    i = start_index + 1
    while i < len(lines):
        s = lines[i].strip().lower()
        if s.startswith("*:") or s.startswith("**") or s.startswith("*::"):
            if any(k in s for k in FINISH_KEYWORDS):
                return True
            i += 1
            continue
        break
    return False
  
def process_reports():
    for page_title in PAGES:
        page = pywikibot.Page(site, page_title)
        text = page.text
        lines = text.splitlines()
        new_lines = []
        changed = False
        i = 0
        while i < len(lines):
            line = lines[i]
            match_iptv = PATTERN_IPTV.search(line)
            match_uaa  = PATTERN_UAA.search(line)
            if match_iptv or match_uaa:
                user_to_check = (match_iptv or match_uaa).group("user").strip()
                if has_finish_comment(lines, i):
                    print(f"[INFO] Hapus '{user_to_check}' (tanda selesai/ditolak)")
                    changed = True
                    i += 1
                    while i < len(lines) and (lines[i].startswith("*:") or lines[i].startswith("**") or lines[i].startswith("*::")):
                        i += 1
                    continue
            new_lines.append(line)
            i += 1
        if changed:
            new_text = "\n".join(new_lines)
            if new_text != text:
                try:
                    page.text = new_text
                    page.save(
                        summary="[Bot Clerking]: membersihkan laporan yang selesai diproses",
                        minor=True,
                        bot=True
                    )
                    print(f"[SAVE] {page_title} diperbarui.")
                except Exception as e:
                    print(f"[ERROR] Gagal menyimpan {page_title}: {e}")
        else:
            print(f"[INFO] Tidak ada perubahan di {page_title}.")
def main():
    while True:
        print("[LOOP] Mulai siklus…")
        process_reports()
        print(f"[SLEEP] Tidur {UPDATE_INTERVAL} detik…")
        time.sleep(UPDATE_INTERVAL)
if __name__ == "__main__":
    main()
