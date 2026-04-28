import pyperclip
from pynput import keyboard
import pyautogui
import tkinter as tk
from tkinter import messagebox
import time
import threading
import requests
import queue
import platform
import re
from collections import Counter


# --- AYARLAR ---
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_ADI = "gemini-3-flash-preview:latest"  # Ana model (F8)
TEXT_MODEL_CANDIDATES = [
    MODEL_ADI,
    "gemini-3-flash-preview:cloud",
    "gemini-3-flash-preview",
    "gemma3:4b",
    "gemma3:1b",
]

KISAYOL_METIN = keyboard.Key.f8  # Metin secimi icin kisayol
KOPYALA_KISAYOLU = ("command", "c") if platform.system() == "Darwin" else ("ctrl", "c")
YAPISTIR_KISAYOLU = ("command", "v") if platform.system() == "Darwin" else ("ctrl", "v")


# Global değişkenler
root = None
gui_queue = queue.Queue()
kisayol_basildi = False
YEREL_ISTATISTIK_ISLEMI = "__LOCAL_TEXT_STATS__"
RUBRIK_KRITERLERI = [
    "Dil bilgisi",
    "Yazım ve noktalama",
    "Konu bütünlüğü",
    "Anlatım açıklığı",
    "Yaratıcılık",
    "Kelime çeşitliliği",
]
TURKCE_DURAK_KELIMELER = {
    "acaba",
    "ama",
    "ancak",
    "artık",
    "az",
    "bazı",
    "belki",
    "ben",
    "beni",
    "benim",
    "bir",
    "biraz",
    "biri",
    "biz",
    "bu",
    "buna",
    "bunda",
    "bundan",
    "bunu",
    "da",
    "daha",
    "de",
    "diye",
    "en",
    "gibi",
    "hem",
    "hep",
    "hepsi",
    "her",
    "hiç",
    "için",
    "ile",
    "ise",
    "kadar",
    "ki",
    "mı",
    "mi",
    "mu",
    "mü",
    "nasıl",
    "ne",
    "neden",
    "o",
    "olarak",
    "oldu",
    "olduğu",
    "olmak",
    "onun",
    "sonra",
    "şey",
    "şu",
    "tabii",
    "ve",
    "veya",
    "ya",
}


# --- MENÜ SEÇENEKLERİ VE PROMPT'LAR ---
ISLEMLER = {
    "🧑‍🏫 Tam Öğretmen Raporu": (
        "Bir Türkçe öğretmeni gibi aşağıdaki öğrenci yazısı için kapsamlı ama kısa bir rapor hazırla. "
        "Önce aşağıdaki rubrik formatını SADECE bir kez yaz ve her kriter için 0-10 arasında tam sayı ver:\n"
        "RUBRIK_PUANLARI\n"
        "Dil bilgisi: <0-10>\n"
        "Yazım ve noktalama: <0-10>\n"
        "Konu bütünlüğü: <0-10>\n"
        "Anlatım açıklığı: <0-10>\n"
        "Yaratıcılık: <0-10>\n"
        "Kelime çeşitliliği: <0-10>\n\n"
        "Sonra şu başlıkları kullan:\n"
        "GENEL_DEGERLENDIRME\n"
        "GÜÇLÜ_YÖNLER\n"
        "GELİŞİM_ALANLARI\n"
        "ÖĞRENCİYE_GERİ_BİLDİRİM\n"
        "Bir öğretmenin kararını destekleyen yardımcı analiz dili kullan. Markdown, tablo ve tekrar kullanma."
    ),
    "📌 Metin İstatistikleri + Grafik": YEREL_ISTATISTIK_ISLEMI,
    "📊 Rubrik Puanı + Grafik": (
        "Bir Türkçe öğretmeni gibi, ortaokul-lise düzeyi bir kompozisyonu adil biçimde değerlendir. "
        "Her kriter için 0-10 arasında tam sayı puan ver. Yazım veya dil bilgisi hatası yoksa "
        "ilgili kriterlere 9 ya da 10 ver; içerik eleştirisini dil puanlarına karıştırma. "
        "Cevabı SADECE bir kez yaz. Markdown, kalın yazı, yıldız, tablo veya tekrar kullanma. "
        "Cevabın en başında aşağıdaki formatı kesin kullan:\n"
        "RUBRIK_PUANLARI\n"
        "Dil bilgisi: <0-10>\n"
        "Yazım ve noktalama: <0-10>\n"
        "Konu bütünlüğü: <0-10>\n"
        "Anlatım açıklığı: <0-10>\n"
        "Yaratıcılık: <0-10>\n"
        "Kelime çeşitliliği: <0-10>\n\n"
        "Sonra GENEL_YORUM başlığı altında en fazla 4 kısa madde yaz. "
        "Aynı rubriği veya aynı yorumu ikinci kez yazma."
    ),
    "✍️ Yazım ve Noktalama Hataları": (
        "Aşağıdaki öğrenci yazısındaki yazım, noktalama ve anlatım hatalarını bul. "
        "Hataları şu formatta ver:\n"
        "- Hatalı ifade: ...\n"
        "  Önerilen düzeltme: ...\n"
        "  Kısa açıklama: ...\n"
        "Metnin tamamını baştan yazma; sadece önemli hataları listele."
    ),
    "💬 Öğrenciye Geri Bildirim Yaz": (
        "Aşağıdaki yazı için öğrenciye doğrudan hitap eden, nazik, anlaşılır ve "
        "geliştirici bir geri bildirim yaz. Önce iyi yaptığı şeyleri söyle, sonra "
        "2-3 gelişim önerisi ver. Son cümlede öğrenciyi cesaretlendiren tek bir net hedef belirt. "
        "Kırıcı veya küçümseyici ifade kullanma."
    ),
    "📝 Geliştirilmiş Örnek Metin": (
        "Aşağıdaki öğrenci yazısını anlamını bozmadan daha akıcı, düzgün ve etkili "
        "bir Türkçe ile yeniden yaz. Öğrencinin seviyesine uygun doğal bir dil kullan. "
        "Sadece geliştirilmiş metni ver."
    ),
}


def get_available_text_model():
    """Metin işlemede kullanılabilir modeli seçer."""
    preferred_models = []
    for model in TEXT_MODEL_CANDIDATES:
        if model and model not in preferred_models:
            preferred_models.append(model)

    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code != 200:
            return MODEL_ADI

        models = response.json().get("models", [])
        installed_lower = {m.get("name", "").lower(): m.get("name", "") for m in models}

        for candidate in preferred_models:
            candidate_lower = candidate.lower()
            if candidate_lower in installed_lower:
                return installed_lower[candidate_lower]

            candidate_base = candidate_lower.split(":")[0]
            for installed_name_lower, installed_name in installed_lower.items():
                if installed_name_lower.startswith(candidate_base + ":"):
                    return installed_name
    except Exception:
        pass

    return MODEL_ADI


def ollama_cevap_al(prompt):
    """Ollama API'den cevap al."""
    try:
        aktif_model = get_available_text_model()
        payload = {
            "model": aktif_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.25,
                "top_p": 0.8,
                "repeat_penalty": 1.2,
            },
        }

        response = requests.post(OLLAMA_URL, json=payload, timeout=60)

        if response.status_code == 200:
            result = response.json()
            return result.get("response", "").strip()

        err_msg = (
            f"Ollama API Hatası: {response.status_code}\n"
            f"Model: {aktif_model}\n"
            f"Cevap: {response.text}"
        )
        print(f"❌ {err_msg}")
        gui_queue.put((messagebox.showerror, ("API Hatası", err_msg)))
        return None

    except requests.exceptions.ConnectionError:
        err_msg = (
            "Ollama'ya bağlanılamadı.\n"
            "Programın çalıştığından emin olun!\n"
            "(http://localhost:11434)"
        )
        print(f"❌ {err_msg}")
        gui_queue.put((messagebox.showerror, ("Bağlantı Hatası", err_msg)))
        return None
    except Exception as e:
        err_msg = f"Beklenmeyen Hata: {e}"
        print(f"❌ {err_msg}")
        gui_queue.put((messagebox.showerror, ("Hata", err_msg)))
        return None


def strip_code_fence(text):
    if not text:
        return text
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        lines = lines[1:] if lines else []
        while lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


def metin_gorunumunu_temizle(text):
    if not text:
        return text
    cleaned = strip_code_fence(text)
    cleaned = re.sub(r"[*_`#]", "", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def secili_metni_kopyala(max_deneme=4):
    sentinel = f"__AI_ASISTAN__{time.time_ns()}__"
    try:
        pyperclip.copy(sentinel)
    except Exception:
        pass

    for _ in range(max_deneme):
        pyautogui.hotkey(*KOPYALA_KISAYOLU)
        time.sleep(0.2)
        metin = pyperclip.paste()
        if metin and metin.strip() and metin != sentinel:
            return metin
    return ""


def kelimeleri_ayikla(metin):
    return re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü0-9]+", metin.lower())


def cumleleri_ayikla(metin):
    cumleler = [c.strip() for c in re.split(r"[.!?]+", metin) if c.strip()]
    return cumleler


def metin_istatistikleri_hesapla(metin):
    kelimeler = kelimeleri_ayikla(metin)
    cumleler = cumleleri_ayikla(metin)
    paragraflar = [p.strip() for p in re.split(r"\n\s*\n", metin) if p.strip()]
    anlamli_kelimeler = [
        kelime
        for kelime in kelimeler
        if len(kelime) > 2 and kelime not in TURKCE_DURAK_KELIMELER
    ]
    benzersiz = set(kelimeler)
    ort_cumle = len(kelimeler) / len(cumleler) if cumleler else 0
    cesitlilik = (len(benzersiz) / len(kelimeler) * 100) if kelimeler else 0
    uzun_cumle_sayisi = sum(1 for c in cumleler if len(kelimeleri_ayikla(c)) > 22)
    gecis_ifadeleri = [
        "ancak",
        "fakat",
        "çünkü",
        "bu yüzden",
        "sonra",
        "önce",
        "buna rağmen",
        "ayrıca",
        "oysaki",
        "sonunda",
    ]
    kucuk_metin = metin.lower()
    gecis_sayisi = sum(kucuk_metin.count(ifade) for ifade in gecis_ifadeleri)
    en_sik = Counter(anlamli_kelimeler).most_common(8)

    return {
        "kelime_sayisi": len(kelimeler),
        "cumle_sayisi": len(cumleler),
        "paragraf_sayisi": len(paragraflar),
        "benzersiz_kelime_sayisi": len(benzersiz),
        "kelime_cesitliligi": cesitlilik,
        "ortalama_cumle_uzunlugu": ort_cumle,
        "uzun_cumle_sayisi": uzun_cumle_sayisi,
        "gecis_ifadesi_sayisi": gecis_sayisi,
        "en_sik_kelimeler": en_sik,
    }


def metin_istatistik_raporu_olustur(metin):
    istatistikler = metin_istatistikleri_hesapla(metin)
    en_sik = istatistikler["en_sik_kelimeler"]
    en_sik_metin = (
        ", ".join(f"{kelime} ({adet})" for kelime, adet in en_sik)
        if en_sik
        else "Yeterli anlamlı kelime bulunamadı."
    )
    ort = istatistikler["ortalama_cumle_uzunlugu"]
    cesitlilik = istatistikler["kelime_cesitliligi"]

    yorumlar = []
    if ort > 22:
        yorumlar.append("- Ortalama cümle uzunluğu yüksek; bazı cümleler bölünerek anlatım netleştirilebilir.")
    elif ort < 8 and istatistikler["cumle_sayisi"] > 1:
        yorumlar.append("- Cümleler oldukça kısa; yazıya daha bağlı ve açıklayıcı cümleler eklenebilir.")
    else:
        yorumlar.append("- Cümle uzunluğu genel olarak okunabilir seviyede.")

    if cesitlilik < 45 and istatistikler["kelime_sayisi"] >= 40:
        yorumlar.append("- Kelime çeşitliliği geliştirilebilir; tekrar eden sözcüklerin yerine eş anlamlılar denenebilir.")
    else:
        yorumlar.append("- Kelime çeşitliliği metnin uzunluğuna göre dengeli görünüyor.")

    if istatistikler["gecis_ifadesi_sayisi"] < 2 and istatistikler["cumle_sayisi"] >= 5:
        yorumlar.append("- Paragraflar ve olay akışı arasında daha fazla geçiş ifadesi kullanılabilir.")
    else:
        yorumlar.append("- Metinde düşünceler arasında bağlantı kuran ifadeler bulunuyor.")

    rapor = (
        "METİN İSTATİSTİKLERİ\n"
        f"Kelime sayısı: {istatistikler['kelime_sayisi']}\n"
        f"Cümle sayısı: {istatistikler['cumle_sayisi']}\n"
        f"Paragraf sayısı: {istatistikler['paragraf_sayisi']}\n"
        f"Benzersiz kelime sayısı: {istatistikler['benzersiz_kelime_sayisi']}\n"
        f"Kelime çeşitliliği: %{cesitlilik:.1f}\n"
        f"Ortalama cümle uzunluğu: {ort:.1f} kelime\n"
        f"Uzun cümle sayısı: {istatistikler['uzun_cumle_sayisi']}\n"
        f"Geçiş ifadesi sayısı: {istatistikler['gecis_ifadesi_sayisi']}\n\n"
        "EN SIK KULLANILAN ANLAMLI KELİMELER\n"
        f"{en_sik_metin}\n\n"
        "ÖĞRETMEN İÇİN VERİ YORUMU\n"
        + "\n".join(yorumlar)
    )
    return rapor, istatistikler


def pencere_modunda_gosterilsin_mi(komut_adi):
    return True


def puanlari_ayikla(metin):
    puanlar = []
    temiz_metin = re.sub(r"[*_`#]", "", metin)
    for kriter in RUBRIK_KRITERLERI:
        pattern = rf"{re.escape(kriter)}[^\d\n]{{0,40}}(\d+(?:[.,]\d+)?)"
        match = re.search(pattern, temiz_metin, re.IGNORECASE)
        if not match:
            continue
        try:
            puan = float(match.group(1).replace(",", "."))
        except ValueError:
            continue
        puanlar.append((kriter, max(0, min(10, puan))))
    return puanlar


def rubrik_grafigi_ciz(canvas, puanlar):
    canvas.delete("all")
    genislik = max(canvas.winfo_width(), 720)
    x0 = 190
    x1 = genislik - 80
    y = 24
    bar_yukseklik = 22
    bosluk = 15

    canvas.create_text(
        14,
        8,
        text="Rubrik Puanları",
        anchor="nw",
        fill="#f5f5f5",
        font=("Segoe UI", 13, "bold"),
    )

    for kriter, puan in puanlar:
        canvas.create_text(
            14,
            y + bar_yukseklik / 2,
            text=kriter,
            anchor="w",
            fill="#f5f5f5",
            font=("Segoe UI", 11),
        )
        canvas.create_rectangle(
            x0,
            y,
            x1,
            y + bar_yukseklik,
            fill="#3a3a3a",
            outline="#555555",
        )
        dolu_genislik = (x1 - x0) * (puan / 10)
        renk = "#2e7d32" if puan >= 8 else "#f9a825" if puan >= 5 else "#c62828"
        canvas.create_rectangle(
            x0,
            y,
            x0 + dolu_genislik,
            y + bar_yukseklik,
            fill=renk,
            outline=renk,
        )
        canvas.create_text(
            x1 + 12,
            y + bar_yukseklik / 2,
            text=f"{puan:g}/10",
            anchor="w",
            fill="#ffffff",
            font=("Segoe UI", 10, "bold"),
        )
        y += bar_yukseklik + bosluk


def istatistik_grafigi_ciz(canvas, istatistikler):
    canvas.delete("all")
    genislik = max(canvas.winfo_width(), 720)
    x0 = 190
    x1 = genislik - 330
    y = 42
    bar_yukseklik = 18
    bosluk = 12
    metrikler = [
        ("Kelime sayısı", istatistikler["kelime_sayisi"], 220),
        ("Cümle sayısı", istatistikler["cumle_sayisi"], 24),
        ("Kelime çeşitliliği", istatistikler["kelime_cesitliligi"], 100),
        ("Ort. cümle uzunluğu", istatistikler["ortalama_cumle_uzunlugu"], 30),
        ("Geçiş ifadeleri", istatistikler["gecis_ifadesi_sayisi"], 10),
    ]

    canvas.create_text(
        14,
        10,
        text="Metin Verileri",
        anchor="nw",
        fill="#f5f5f5",
        font=("Segoe UI", 13, "bold"),
    )

    for etiket, deger, maksimum in metrikler:
        oran = 0 if maksimum == 0 else min(deger / maksimum, 1)
        canvas.create_text(
            14,
            y + bar_yukseklik / 2,
            text=etiket,
            anchor="w",
            fill="#f5f5f5",
            font=("Segoe UI", 10),
        )
        canvas.create_rectangle(
            x0,
            y,
            x1,
            y + bar_yukseklik,
            fill="#3a3a3a",
            outline="#555555",
        )
        canvas.create_rectangle(
            x0,
            y,
            x0 + (x1 - x0) * oran,
            y + bar_yukseklik,
            fill="#1565c0",
            outline="#1565c0",
        )
        deger_metni = f"%{deger:.1f}" if "çeşitliliği" in etiket else f"{deger:.1f}" if isinstance(deger, float) else str(deger)
        canvas.create_text(
            x1 + 12,
            y + bar_yukseklik / 2,
            text=deger_metni,
            anchor="w",
            fill="#ffffff",
            font=("Segoe UI", 10, "bold"),
        )
        y += bar_yukseklik + bosluk

    sag_x = max(x1 + 95, genislik - 290)
    canvas.create_text(
        sag_x,
        10,
        text="Sık Kullanılan Kelimeler",
        anchor="nw",
        fill="#f5f5f5",
        font=("Segoe UI", 12, "bold"),
    )
    top_words = istatistikler["en_sik_kelimeler"][:5]
    max_adet = max([adet for _, adet in top_words], default=1)
    kelime_y = 44
    for kelime, adet in top_words:
        bar_uzunluk = 120 * (adet / max_adet)
        canvas.create_text(
            sag_x,
            kelime_y + 8,
            text=kelime,
            anchor="w",
            fill="#f5f5f5",
            font=("Segoe UI", 10),
        )
        canvas.create_rectangle(
            sag_x + 110,
            kelime_y,
            sag_x + 110 + bar_uzunluk,
            kelime_y + 16,
            fill="#00897b",
            outline="#00897b",
        )
        canvas.create_text(
            sag_x + 240,
            kelime_y + 8,
            text=str(adet),
            anchor="w",
            fill="#ffffff",
            font=("Segoe UI", 10, "bold"),
        )
        kelime_y += 30


def renkli_buton_olustur(parent, text, command, bg, hover_bg, side, padx=24):
    buton = tk.Label(
        parent,
        text=text,
        bg=bg,
        fg="#ffffff",
        activebackground=hover_bg,
        activeforeground="#ffffff",
        font=("Segoe UI", 11, "bold"),
        padx=padx,
        pady=10,
        cursor="hand2",
        relief="flat",
        bd=0,
    )
    buton.pack(side=side)

    def ustune_gelince(_event):
        buton.configure(bg=hover_bg)

    def ayrilinca(_event):
        buton.configure(bg=bg)

    def tiklayinca(_event):
        command()

    buton.bind("<Enter>", ustune_gelince)
    buton.bind("<Leave>", ayrilinca)
    buton.bind("<Button-1>", tiklayinca)
    return buton


def sonuc_penceresi_goster(baslik, icerik, puanlar=None, istatistikler=None):
    pencere = tk.Toplevel(root)
    pencere.title(baslik)
    pencere.geometry("900x780" if puanlar and istatistikler else "840x650" if puanlar or istatistikler else "780x520")
    pencere.minsize(560, 380)
    pencere.attributes("-topmost", True)

    if puanlar or istatistikler:
        grafik_frame = tk.Frame(pencere, bg="#1f1f1f")
        grafik_frame.pack(fill="x", padx=10, pady=(10, 0))
        if puanlar:
            grafik = tk.Canvas(
                grafik_frame,
                height=260,
                bg="#242424",
                highlightthickness=1,
                highlightbackground="#3d3d3d",
            )
            grafik.pack(fill="x", pady=(0, 8 if istatistikler else 0))
            grafik.after(100, lambda: rubrik_grafigi_ciz(grafik, puanlar))
        if istatistikler:
            istatistik_grafik = tk.Canvas(
                grafik_frame,
                height=220,
                bg="#242424",
                highlightthickness=1,
                highlightbackground="#3d3d3d",
            )
            istatistik_grafik.pack(fill="x")
            istatistik_grafik.after(
                100, lambda: istatistik_grafigi_ciz(istatistik_grafik, istatistikler)
            )

    frame = tk.Frame(pencere, bg="#1f1f1f")
    frame.pack(fill="both", expand=True, padx=10, pady=10)

    text_alani = tk.Text(
        frame,
        wrap="word",
        bg="#2b2b2b",
        fg="white",
        insertbackground="white",
        font=("Segoe UI", 10),
        padx=10,
        pady=10,
    )
    kaydirma = tk.Scrollbar(frame, command=text_alani.yview)
    text_alani.configure(yscrollcommand=kaydirma.set)

    text_alani.pack(side="left", fill="both", expand=True)
    kaydirma.pack(side="right", fill="y")

    text_alani.insert("1.0", icerik)
    text_alani.config(state="disabled")

    alt_frame = tk.Frame(pencere, bg="#1f1f1f")
    alt_frame.pack(fill="x", padx=10, pady=(0, 10))

    def panoya_kopyala():
        pyperclip.copy(icerik)

    renkli_buton_olustur(
        alt_frame,
        "Panoya Kopyala",
        panoya_kopyala,
        "#1565c0",
        "#1e88e5",
        "left",
        padx=28,
    )

    renkli_buton_olustur(
        alt_frame,
        "Kapat",
        pencere.destroy,
        "#b71c1c",
        "#d32f2f",
        "right",
        padx=32,
    )

    pencere.focus_force()
    pencere.lift()


def islemi_yap(komut_adi, secili_metin):
    prompt_emri = ISLEMLER[komut_adi]
    if prompt_emri == YEREL_ISTATISTIK_ISLEMI:
        rapor, istatistikler = metin_istatistik_raporu_olustur(secili_metin)
        gui_queue.put((sonuc_penceresi_goster, (komut_adi, rapor, None, istatistikler)))
        print("✅ Metin istatistikleri ayrı pencerede gösterildi.")
        return

    full_prompt = f"{prompt_emri}:\n\n'{secili_metin}'"

    print(f"🤖 İşlem: {komut_adi}")
    print("⏳ Ollama ile işleniyor...")

    sonuc = ollama_cevap_al(full_prompt)
    if not sonuc:
        print("❌ Sonuç alınamadı.")
        return

    sonuc = metin_gorunumunu_temizle(sonuc)
    if sonuc.startswith("'") and sonuc.endswith("'"):
        sonuc = sonuc[1:-1]

    if pencere_modunda_gosterilsin_mi(komut_adi):
        puanlar = puanlari_ayikla(sonuc)
        istatistikler = None
        if puanlar or "Rubrik" in komut_adi or "Raporu" in komut_adi:
            istatistik_raporu, istatistikler = metin_istatistik_raporu_olustur(secili_metin)
            sonuc = f"{sonuc}\n\n---\n\n{istatistik_raporu}"
        gui_queue.put((sonuc_penceresi_goster, (komut_adi, sonuc, puanlar, istatistikler)))
        print("✅ Sonuç ayrı pencerede gösterildi.")
        return

    time.sleep(0.2)
    pyperclip.copy(sonuc)
    time.sleep(0.1)
    pyautogui.hotkey(*YAPISTIR_KISAYOLU)
    print("✅ İşlem tamamlandı!")


def process_queue():
    """Kuyruktaki GUI işlemlerini ana thread'de çalıştırır."""
    try:
        while True:
            try:
                task = gui_queue.get_nowait()
            except queue.Empty:
                break
            func, args = task
            func(*args)
    finally:
        if root:
            root.after(100, process_queue)


def menu_goster():
    """Metni kopyalar ve menüyü gösterir (ana thread)."""
    secili_metin = secili_metni_kopyala()
    if not secili_metin.strip():
        gui_queue.put(
            (
                messagebox.showwarning,
                (
                    "Secim Bulunamadi",
                    "Lutfen once metin secin, sonra F8 ile menuyu acin.",
                ),
            )
        )
        return

    menu = tk.Menu(
        root,
        tearoff=0,
        bg="#2b2b2b",
        fg="white",
        activebackground="#4a4a4a",
        activeforeground="white",
        font=("Segoe UI", 10),
    )

    def komut_olustur(k_adi, s_metin):
        def komut_calistir():
            threading.Thread(
                target=islemi_yap, args=(k_adi, s_metin), daemon=True
            ).start()

        return komut_calistir

    for baslik in ISLEMLER.keys():
        menu.add_command(label=baslik, command=komut_olustur(baslik, secili_metin))

    menu.add_separator()
    menu.add_command(label="❌ İptal", command=lambda: None)

    try:
        x, y = pyautogui.position()
        menu.tk_popup(x, y)
    finally:
        menu.grab_release()


def on_press(key):
    global kisayol_basildi
    try:
        if key == KISAYOL_METIN and not kisayol_basildi:
            kisayol_basildi = True
            gui_queue.put((menu_goster, ()))
    except AttributeError:
        pass


def on_release(key):
    global kisayol_basildi
    try:
        if key == KISAYOL_METIN:
            kisayol_basildi = False
    except AttributeError:
        pass


if __name__ == "__main__":
    print("=" * 60)
    print("🧑‍🏫 Akıllı Öğretmen Asistanı")
    print("=" * 60)
    aktif_text_model = get_available_text_model()
    print(f"📦 Değerlendirme Modeli (F8): {aktif_text_model}")
    print()
    print("🔧 Kullanım:")
    print("   F8 - Öğrenci metnini seç ve değerlendirme menüsünü aç")
    print()
    print("⚠️ Programı kapatmak için bu pencereyi kapatın veya Ctrl+C yapın.")
    print("=" * 60)

    try:
        test_response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if test_response.status_code == 200:
            print("✅ Ollama bağlantısı başarılı!")
        else:
            print("⚠️ Ollama'ya bağlanılamadı, servisi kontrol edin!")
    except Exception:
        print("⚠️ Ollama çalışmıyor olabilir! 'ollama serve' ile başlatın.")

    print()

    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()

    root = tk.Tk()
    root.withdraw()
    root.after(100, process_queue)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("Kapatılıyor...")
