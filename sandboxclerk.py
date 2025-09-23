import time
import pywikibot

WIKI_FAMILY = "wikipedia"
WIKI_LANG = "id"
SANDBOX_PAGE = "Wikipedia:Bak pasir"
SANDBOX_TEXT = "<!-- Halaman ini hanya untuk uji coba menyunting dan dikosongkan secara berkala -->"

SANDBOX_INTERVAL = 10 * 60 
site = pywikibot.Site(WIKI_LANG, WIKI_FAMILY)
site.login()
def clean_sandbox():
    page = pywikibot.Page(site, SANDBOX_PAGE)
    try:
        if page.text.strip() != SANDBOX_TEXT.strip():
            page.text = SANDBOX_TEXT
            page.save(
                summary="[Bot Clerking]: membersihkan bak pasir secara berkala",
                minor=True,
                bot=True,
            )
            print(f"[SAVE] {SANDBOX_PAGE} berhasil dibersihkan.")
        else:
            print(f"[INFO] {SANDBOX_PAGE} sudah bersih, tidak ada perubahan.")
    except Exception as e:
        print(f"[ERROR] Gagal membersihkan {SANDBOX_PAGE}: {e}")
def main():
    while True:
        clean_sandbox()
        time.sleep(SANDBOX_INTERVAL)
if __name__ == "__main__":
    main()
