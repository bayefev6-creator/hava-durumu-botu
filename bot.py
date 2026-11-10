import requests
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "9093836053:AAH3W_kxjhM8UU_eEFLOHCF3p_3b53PJP1s"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.mgm.gov.tr/",
    "Origin": "https://www.mgm.gov.tr"
}

HADISE_CEVIRI = {
    "A": "Güneşli / Açık",
    "AB": "Az Bulutlu",
    "PB": "Parçalı Bulutlu",
    "CB": "Çok Bulutlu",
    "GY": "Güneşli",
    "HY": "Hafif Yağmurlu",
    "Y": "Yağmurlu",
    "KY": "Kuvvetli Yağmurlu",
    "SY": "Sağanak Yağışlı",
    "KSY": "Kuvvetli Sağanak Yağışlı",
    "K": "Karlı",
    "HK": "Hafif Karlı",
    "YK": "Yoğun Karlı",
    "S": "Sisli",
    "PUS": "Puslu",
    "D": "Dumanlı",
    "R": "Rüzgarlı",
    "GKS": "Gökgürültülü Sağanak Yağışlı",
}

def hadise_aciklama(kod):
    if not kod:
        return "Bilinmiyor"
    return HADISE_CEVIRI.get(str(kod).upper(), str(kod))

def ruzgar_yonu_cevir(derece):
    if derece is None or derece == -9999:
        return "Bilinmiyor"
    yonler = [
        "Kuzey (K)", "Kuzeydoğu (KD)", "Doğu (D)", "Güneydoğu (GD)",
        "Güney (G)", "Güneybatı (GB)", "Batı (B)", "Kuzeybatı (KB)"
    ]
    try:
        indeks = round(float(derece) / 45) % 8
        return yonler[indeks]
    except:
        return "Bilinmiyor"

def saat_formatla(veri_zamani):
    if not veri_zamani:
        return "Bilinmiyor"
    try:
        zaman_str = str(veri_zamani).replace("Z", "").split(".")[0]
        dt = datetime.fromisoformat(zaman_str) + timedelta(hours=3)
        return dt.strftime("%d.%m.%Y %H:%M")
    except Exception:
        return str(veri_zamani)

def tarih_formatla(tarih_str):
    if not tarih_str:
        return ""
    try:
        zaman_str = str(tarih_str).replace("Z", "").split("T")[0]
        dt = datetime.fromisoformat(zaman_str)
        gunler = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
        gun_isim = gunler[dt.weekday()]
        return f"{dt.strftime('%d.%m.%Y')} ({gun_isim})"
    except:
        return str(tarih_str)

def deger_temizle(deger, birim=""):
    if deger is None or deger == -9999:
        return "Veri yok"
    return f"{deger}{birim}"

def mgm_merkez_bul(sorgu: str):
    sorgu = sorgu.strip()
    try:
        url = f"https://servis.mgm.gov.tr/web/merkezler?ilce={sorgu}"
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200 and r.json():
            sonuclar = r.json()
            if isinstance(sonuclar, list) and len(sonuclar) > 0:
                return sonuclar[0]
    except:
        pass

    try:
        url = f"https://servis.mgm.gov.tr/web/merkezler?il={sorgu}"
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200 and r.json():
            sonuclar = r.json()
            if isinstance(sonuclar, list) and len(sonuclar) > 0:
                return sonuclar[0]
    except:
        pass

    try:
        url = f"https://servis.mgm.gov.tr/web/merkezler?sorgu={sorgu}"
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200 and r.json():
            sonuclar = r.json()
            if isinstance(sonuclar, list) and len(sonuclar) > 0:
                return sonuclar[0]
    except:
        pass

    return None

# 1. /hava Komutu (Sadece Anlık Durum - Tahminler Kaldırıldı)
async def sehir_sorgu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        sorgu = " ".join(context.args)
    else:
        sorgu = update.message.text.lstrip('/')
    
    haric_komutlar = ["start", "help", "radar", "tahmin", "uyarilar", "hava"]
    if sorgu.lower() in haric_komutlar:
        return

    bekleme = await update.message.reply_text(f"⏳ '{sorgu.capitalize()}' için anlık hava durumu verileri çekiliyor...")

    merkez = mgm_merkez_bul(sorgu)
    if not merkez:
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=bekleme.message_id, text=f"❌ '{sorgu}' için MGM'de kayıtlı bir istasyon bulunamadı.")
        return

    ist_no = merkez.get("gunlukTahminIstNo") or merkez.get("istNo")
    il_adi = merkez.get("il", "")
    ilce_adi = merkez.get("ilce", "")
    lokasyon_adi = f"{il_adi} / {ilce_adi}" if ilce_adi and ilce_adi.lower() != ilce_adi.lower() else il_adi

    try:
        durum_url = f"https://servis.mgm.gov.tr/web/sondurumlar?merkezid={ist_no}"
        r_durum = requests.get(durum_url, headers=HEADERS, timeout=10)
        durum = r_durum.json()[0] if r_durum.status_code == 200 and r_durum.json() else {}
    except:
        durum = {}

    sicaklik = deger_temizle(durum.get("sicaklik"), " °C")
    nem = deger_temizle(durum.get("nem"), "%")
    
    ruzgar_hiz_ham = durum.get("ruzgarHiz")
    if ruzgar_hiz_ham is not None and ruzgar_hiz_ham != -9999:
        try:
            ruzgar_hiz = f"{round(float(ruzgar_hiz_ham))} km/sa"
        except:
            ruzgar_hiz = "Veri yok"
    else:
        ruzgar_hiz = "Veri yok"

    ruzgar_yon = ruzgar_yonu_cevir(durum.get("ruzgarYon"))
    ruzgar_str = "Veri yok" if ruzgar_hiz == "Veri yok" else f"{ruzgar_hiz} ({ruzgar_yon})"
    
    yagis = deger_temizle(durum.get("yagis00Now"), " mm")
    basinc = deger_temizle(durum.get("denizeGoreBasinc") or durum.get("basinc"), " hPa")
    
    gorus_ham = durum.get("gorus")
    if gorus_ham is not None and gorus_ham != -9999:
        try:
            gorus_deger = float(gorus_ham)
            gorus = "Veri yok" if gorus_deger <= 0 else f"{gorus_deger / 1000:.1f} km"
        except:
            gorus = "Veri yok"
    else:
        gorus = "Veri yok"

    guncelleme = saat_formatla(durum.get("veriZamani"))
    hava_durumu_str = hadise_aciklama(durum.get("hadiseKodu"))

    mesaj = (
        f"📍 **{lokasyon_adi} Anlık Hava Durumu**\n"
        f"🕒 Son Güncelleme: `{guncelleme}`\n"
        f"----------------------------------\n"
        f"🌤️ Durum: **{hava_durumu_str}**\n"
        f"🌡️ Sıcaklık: **{sicaklik}**\n"
        f"💧 Nem: **{nem}**\n"
        f"🌧️ Günlük Yağış: **{yagis}**\n"
        f"💨 Rüzgar: **{ruzgar_str}**\n"
        f"📊 Basınç: **{basinc}**\n"
        f"👁️ Görüş Mesafesi: **{gorus}**"
    )

    await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=bekleme.message_id, text=mesaj, parse_mode="Markdown")

# 2. Ayrı /tahmin Komutu (5 Günlük Detaylı Tablo İçin)
async def tahmin_komutu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Lütfen bir şehir adı belirtin. Örnek: `/tahmin düzce`", parse_mode="Markdown")
        return
    
    sorgu = " ".join(context.args)
    bekleme = await update.message.reply_text(f"⏳ '{sorgu.capitalize()}' için detaylı 5 günlük tahmin tablosu hazırlanıyor...")

    merkez = mgm_merkez_bul(sorgu)
    if not merkez:
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=bekleme.message_id, text=f"❌ '{sorgu}' için MGM'de kayıtlı bir istasyon bulunamadı.")
        return

    ist_no = merkez.get("gunlukTahminIstNo") or merkez.get("istNo")
    il_adi = merkez.get("il", "")
    ilce_adi = merkez.get("ilce", "")
    lokasyon_adi = f"{il_adi} / {ilce_adi}" if ilce_adi and ilce_adi.lower() != ilce_adi.lower() else il_adi

    try:
        tahmin_url = f"https://servis.mgm.gov.tr/web/tahminler/gunluk?merkezid={ist_no}"
        r_tahmin = requests.get(tahmin_url, headers=HEADERS, timeout=10)
        tahmin_veri = r_tahmin.json() if r_tahmin.status_code == 200 else []

        if not tahmin_veri:
            tahmin_url = f"https://servis.mgm.gov.tr/web/tahminler/gunluk?merkezid={merkez.get('istNo')}"
            r_tahmin = requests.get(tahmin_url, headers=HEADERS, timeout=10)
            tahmin_veri = r_tahmin.json() if r_tahmin.status_code == 200 else []

        if not tahmin_veri or not isinstance(tahmin_veri, list):
            await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=bekleme.message_id, text="❌ MGM bu merkez için şu an tahmin verisi döndürmüyor.")
            return

        gunler = tahmin_veri[0].get("gunluk", [])[:5]
        tahmin_metni = f"🇹🇷 **{lokasyon_adi.upper()} - 5 GÜNLÜK HAVA TAHMİNİ**\n----------------------------------"

        for g in gunler:
            tarih = tarih_formatla(g.get("tarih"))
            hadise = hadise_aciklama(g.get("hadise"))
            d_sicaklik = g.get("enDusukSicaklik", "?")
            y_sicaklik = g.get("enYuksekSicaklik", "?")
            d_nem = g.get("enDusukNem", "?")
            y_nem = g.get("enYuksekNem", "?")
            r_hiz = g.get("ruzgarHiz", "?")
            r_yon = ruzgar_yonu_cevir(g.get("ruzgarYon"))

            tahmin_metni += (
                f"\n📅 **{tarih}**\n"
                f"  🌤️ Hadise: **{hadise}**\n"
                f"  🌡️ Sıcaklık: Min **{d_sicaklik}°C** / Maks **{y_sicaklik}°C**\n"
                f"  💧 Nem: Min **%{d_nem}** / Maks **%{y_nem}**\n"
                f"  💨 Rüzgar: **{r_hiz} km/sa ({r_yon})**\n"
                f"----------------------------------"
            )

        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=bekleme.message_id, text=tahmin_metni, parse_mode="Markdown")
    except Exception as e:
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=bekleme.message_id, text="❌ Tahmin verileri alınamadı.")

if __name__ == "__main__":
    try:
        app = ApplicationBuilder().token(TOKEN).build()
        
        app.add_handler(CommandHandler("hava", sehir_sorgu))
        app.add_handler(CommandHandler("tahmin", tahmin_komutu))
        app.add_handler(MessageHandler(filters.COMMAND & ~filters.Regex(r'^/($|@)'), sehir_sorgu))

        print("Hava durumu botu güncellendi ve aktif!")
        app.run_polling()
    except Exception as e:
        print(f"\n❌ Bir hata oluştu:\n{e}\n")
        input("Kapatmak için Enter tuşuna basın...")