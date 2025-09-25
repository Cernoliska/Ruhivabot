import sys  
import time  
import traceback  
from datetime import datetime, timedelta  
import pywikibot  
import re  

SPI_CENTRAL_PAGE = "Wikipedia:Investigasi pengguna siluman/Kasus/Sedang berjalan"  
SPI_CASE_CATEGORIES = [  
    "Kategori:Investigasi pengguna siluman yang masih didiskusikan",  
    "Kategori:Investigasi pengguna siluman yang selesai didiskusikan",  
    "Kategori:Investigasi pengguna siluman yang terbengkalai",  
]  
SKIP_KEYWORDS = ["IPS", "Kasus", "header", "Indikator", "Blank_report_template_header"]  
SUMMARY = "[Bot Clerking]: memperbarui kasus investigasi"  
RETENTION_DAYS = 7
  
BULAN = [  
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",  
    "Juli", "Agustus", "September", "Oktober", "November", "Desember"  
]  

site = pywikibot.Site("id", "wikipedia")  
site.login()  
   
def parse_date(text):  
    pattern = r"\b([0-3]?[0-9])\s+(" + "|".join(BULAN) + r")\s+([0-9]{4})\b"  
    m = re.search(pattern, text, flags=re.IGNORECASE)  
    if m:  
        day = int(m.group(1))  
        month = BULAN.index(m.group(2).capitalize()) + 1  
        year = int(m.group(3))  
        try:  
            return datetime(year, month, day)  
        except ValueError:  
            return None  
    return None  
  
def extract_latest_header_date(text):  
    headers = re.findall(r"^(={2,3})\s*(.*?)\s*\1", text, flags=re.M)  
    latest_date = None  
    latest_header = "–"  
    for eq, title in headers:  
        dt = parse_date(title)  
        if dt and (latest_date is None or dt > latest_date):  
            latest_date = dt  
            latest_header = title  
    return latest_header, latest_date  
  
def extract_last_admin_and_date(text):  
    lines = text.splitlines()  
    for line in reversed(lines):  
        match_user = re.search(r"\[\[(?:User|Pengguna):([^|]+)\|", line, flags=re.I)  
        if match_user:  
            admin = match_user.group(1).strip()  
            dt = parse_date(line)  
            return admin, dt  
    return "–", None  
  
def get_user_groups(username):  
    try:  
        user = pywikibot.User(site, username)  
        return user.groups()  
    except Exception:  
        return []  
  
def is_older_than_90_days(date_obj):  
    if not date_obj:  
        return False  
    return datetime.utcnow() - date_obj > timedelta(days=RETENTION_DAYS)  
  
def get_status_from_subpage(title):  
    try:  
        page = pywikibot.Page(site, title)  
        text = page.get()  
    except Exception as e:  
        print(f"[ERROR] gagal ambil {title}: {e}")  
        return None, None, None, None  
  
    matches = list(re.finditer(r"\{\{\s*SPI case status\s*(\|[^}]*)?\}\}", text, flags=re.I))
    if matches:
        m = matches[-1]  
        params = m.group(1)
        if params:
            parts = [p.strip() for p in params.split("|") if p.strip()]
            status = parts[0] if parts else "open"
        else:
            status = "open"
    else:
        status = None
  
    latest_header, header_date = extract_latest_header_date(text)  
  
    last_admin, last_date_obj = extract_last_admin_and_date(text)  
    if last_admin != "–":  
        groups = get_user_groups(last_admin)  
        relevant = [g for g in groups if g in ["sysop", "checkuser"]]  
        if relevant:  
            last_admin = f"{last_admin} ({', '.join(relevant)})"  
    last_date = last_date_obj.strftime("%Y-%m-%d") if last_date_obj else "–"  
   
    if not status or not header_date:  
        return None, None, None, None, None  
  
    return status, latest_header, last_admin, last_date, header_date  
  
def get_cases_from_categories():  
    cases = set()  
    for cat_name in SPI_CASE_CATEGORIES:  
        cat_page = pywikibot.Category(site, cat_name)  
        print(f"[DEBUG] cek kategori: {cat_name}")  
        for page in cat_page.articles():  
            subpage = page.title().replace("Wikipedia:Investigasi pengguna siluman/", "")  
            if any(key.lower() in subpage.lower() for key in SKIP_KEYWORDS):  
                print(f"[SKIP] {subpage} (keyword skip)")  
                continue  
            cases.add(subpage)  
    return cases  
  
def main():  
    central_page = pywikibot.Page(site, SPI_CENTRAL_PAGE)  
    text = central_page.get()  
    now = datetime.utcnow()  
    lines = text.splitlines()  
    new_lines = []  
    changed = False  
    processed = set()  
    last_index = None  
    print(f"[DEBUG] total baris di halaman pusat: {len(lines)}")  
      
    for idx, line in enumerate(lines):  
        stripped = line.strip()  
        if stripped.startswith("{{IPSstatusentry|"):  
            m = re.match(r"\{\{IPSstatusentry\|([^|]+)\|", stripped)  
            if not m:  
                new_lines.append(line)  
                continue  
            subpage = m.group(1).strip()  
            if any(key.lower() in subpage.lower() for key in SKIP_KEYWORDS):  
                new_lines.append(line)  
                processed.add(subpage)  
                last_index = len(new_lines) - 1  
                continue  
  
            status, latest_header, last_admin, last_date, header_date = get_status_from_subpage(  
                f"Wikipedia:Investigasi pengguna siluman/{subpage}"  
            )  
  
            if not status or not header_date:
                print(f"[SKIP] {subpage} (status atau tanggal header tidak terdeteksi)")
                continue
                
            if status.lower() in ["dormant", "terbengkalai", "done", "selesai", "close", "closed", "tutup"] and is_older_than_90_days(header_date):
                print(f"[INFO] Hapus entri selesai: {subpage}")
                changed = True
                continue
                
            if status.lower() not in ["dormant", "terbengkalai", "done", "selesai", "close", "closed", "tutup"] and (
    datetime.utcnow() - header_date > timedelta(days=90)
):
                print(f"[SKIP] {subpage} (kasus lama non-selesai >90 hari)")
                continue
  
            new_line = f"{{{{IPSstatusentry|{subpage}|{status}|{latest_header}|{last_admin}|{last_date}}}}}"  
            if new_line != stripped:  
                changed = True  
                leading_ws = line[: len(line) - len(line.lstrip())]  
                new_lines.append(f"{leading_ws}{new_line}")  
            else:  
                new_lines.append(line)  
            processed.add(subpage)  
            last_index = len(new_lines) - 1  
        else:  
            new_lines.append(line)  
  
    cases_from_cat = get_cases_from_categories()  
    new_cases = cases_from_cat - processed  
    extra_lines = []  
  
    for subpage in sorted(new_cases):  
        status, latest_header, last_admin, last_date, header_date = get_status_from_subpage(  
            f"Wikipedia:Investigasi pengguna siluman/{subpage}"  
        )  
        if not status or not header_date:
            print(f"[SKIP] {subpage} (status atau tanggal header tidak terdeteksi)")
            continue
            
        if status.lower() in ["dormant", "terbengkalai", "done", "selesai", "close", "closed", "tutup"] and is_older_than_90_days(header_date):
            print(f"[INFO] Hapus entri selesai: {subpage}")
            changed = True
            continue
            
        if status.lower() not in ["dormant", "terbengkalai", "done", "selesai", "close", "closed", "tutup"] and (
    datetime.utcnow() - header_date > timedelta(days=90)
):
            print(f"[SKIP] {subpage} (kasus lama non-selesai >90 hari)")
            continue
        new_entry = f"{{{{IPSstatusentry|{subpage}|{status}|{latest_header}|{last_admin}|{last_date}}}}}"  
        extra_lines.append(new_entry)  
        changed = True  
  
    if extra_lines:  
        if last_index is not None:  
            new_lines = new_lines[: last_index + 1] + extra_lines + new_lines[last_index + 1 :]  
        else:  
            new_lines.extend(extra_lines)  
  
    if changed:  
        new_text = "\n".join(new_lines)  
        if new_text != text:  
            central_page.text = new_text  
            central_page.save(summary=SUMMARY, minor=True, bot=True)  
            print("[UPDATE] Halaman pusat diperbarui")  
        else:  
            print("[DEBUG] teks identik, batal simpan")  
    else:  
        print("[NOCHANGE] Tidak ada perubahan")  
  
if __name__ == "__main__":  
    while True:  
        try:  
            print("\n[LOOP] Mulai update...")  
            main()  
            print("[LOOP] Selesai update. Tidur 5 menit.\n")  
        except Exception as e:  
            print("[ERROR] Error di loop utama:", e)  
            traceback.print_exc()  
            print("[LOOP] Tidur 5 menit lalu coba lagi...\n")  
        time.sleep(5 * 60)  
        
