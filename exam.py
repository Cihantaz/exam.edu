import os
import io
import base64
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, send_file, session, flash
import sys

def resource_path(relative_path):
    """PyInstaller ile paketlenmiş dosyalar için yol düzeltmesi."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

app = Flask(
    __name__,
    template_folder=resource_path('templates'),
    static_folder=resource_path('static')
)

app.secret_key = "exam_secret_key"

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

def temizle_sayi(s):
    if isinstance(s, str):
        s = s.replace('.', '').replace(',', '')
    try:
        return int(s)
    except:
        return 0

def etiketle(ogr_siralama, taban, z_riskli):
    try:
        ogr_siralama = int(ogr_siralama)
        taban = int(taban)
    except:
        return "Bilinmiyor"
    if taban >= ogr_siralama:
        return "Uygun"
    elif z_riskli is not None and taban >= z_riskli:
        return "Riskli"
    else:
        return "Uygunsuz"

def analiz_yap(df, parametreler):
    result = []
    for p in parametreler:
        ogr_siralama_int = temizle_sayi(p["ogr_siralama"])
        sinir_int = temizle_sayi(p["sinir"])
        riskli_t_int = temizle_sayi(p["riskli_t"])
        z = ogr_siralama_int - sinir_int
        z_riskli = z - riskli_t_int if riskli_t_int else None

        df_filtered = df.copy()
        if p["puan_turu"] and 'Puan Türü' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['Puan Türü'].astype(str).str.strip().str.upper() == p["puan_turu"]]
        bos_veya_eksi_bolumler = []
        if 'En Düşük Sıralama' in df_filtered.columns:
            def kontrol_et(x):
                try:
                    x_sayi = int(str(x).replace('.', '').replace(',', ''))
                except:
                    return False
                if z_riskli is not None:
                    return x_sayi > z_riskli
                else:
                    return x_sayi > z
            df_filtered_main = df_filtered[df_filtered['En Düşük Sıralama'].apply(kontrol_et)]
            bos_veya_eksi_bolumler = df_filtered[df_filtered['En Düşük Sıralama'].apply(lambda x: pd.isna(x) or str(x).strip() == "" or str(x).strip() == "-")]
        else:
            df_filtered_main = df_filtered

        for _, row in df_filtered_main.iterrows():
            program_adi = str(row.get('Program Adı', '')).strip()
            burs = str(row.get('Burs/İndirim', '')).strip() if 'Burs/İndirim' in row else ''
            if not burs:
                for burs_kw in ["Burslu", "Ücretli", "%50 İndirimli", "%25 İndirimli", "%75 İndirimli", "%100 Burslu"]:
                    if burs_kw.lower() in program_adi.lower():
                        burs = burs_kw
                        break
                if not burs:
                    import re
                    m = re.search(r'(%\d{1,3}\s*İndirimli)', program_adi, re.IGNORECASE)
                    if m:
                        burs = m.group(1)
            ucret = row['Ücret'] if 'Ücret' in row and pd.notnull(row['Ücret']) else ''
            if ucret:
                try:
                    ucret_num = float(str(ucret).replace('.', '').replace(',', '').replace('₺','').strip())
                    ucret = f"{ucret_num:,.0f}".replace(",", ".") + " TL"
                except:
                    ucret = str(ucret) + " TL"
            if "(İngilizce)" in program_adi or "(ingilizce)" in program_adi:
                dil = "EN"
            else:
                dil = "TR"
            etiket = etiketle(ogr_siralama_int, row.get('En Düşük Sıralama', 0), z_riskli)
            result.append({
                'Bölüm Adı': program_adi,
                'Puan Türü': row.get('Puan Türü', ''),
                'Burs Oranı': burs,
                'Taban Sıralama': row.get('En Düşük Sıralama', ''),
                'Taban Puan': row.get('Taban Puan', ''),
                'Tavan Puan': row.get('Tavan Puan', ''),
                'Ücret': ucret,
                'Dil': dil,
                'Etiket': etiket,
                'Riskli T': riskli_t_int,
                'Z Riskli': z_riskli if z_riskli is not None else "",
                'Parametre': f"{p['puan_turu']} / {p['ogr_siralama']} / {p['sinir']} / {p['riskli_t']}"
            })

        if 'En Düşük Sıralama' in df_filtered.columns:
            for _, row in bos_veya_eksi_bolumler.iterrows():
                program_adi = str(row.get('Program Adı', '')).strip()
                burs = str(row.get('Burs/İndirim', '')).strip() if 'Burs/İndirim' in row else ''
                if not burs:
                    for burs_kw in ["Burslu", "Ücretli", "%50 İndirimli", "%25 İndirimli", "%75 İndirimli", "%100 Burslu"]:
                        if burs_kw.lower() in program_adi.lower():
                            burs = burs_kw
                            break
                    if not burs:
                        import re
                        m = re.search(r'(%\d{1,3}\s*İndirimli)', program_adi, re.IGNORECASE)
                        if m:
                            burs = m.group(1)
                ucret = row['Ücret'] if 'Ücret' in row and pd.notnull(row['Ücret']) else ''
                if ucret:
                    try:
                        ucret_num = float(str(ucret).replace('.', '').replace(',', '').replace('₺','').strip())
                        ucret = f"{ucret_num:,.0f}".replace(",", ".") + " TL"
                    except:
                        ucret = str(ucret) + " TL"
                if "(İngilizce)" in program_adi or "(ingilizce)" in program_adi:
                    dil = "EN"
                else:
                    dil = "TR"
                etiket = etiketle(ogr_siralama_int, row.get('En Düşük Sıralama', 0), z_riskli)
                if not any(r['Bölüm Adı'] == program_adi and r['Taban Sıralama'] == row.get('En Düşük Sıralama', '') for r in result):
                    result.append({
                        'Bölüm Adı': program_adi,
                        'Puan Türü': row.get('Puan Türü', ''),
                        'Burs Oranı': burs,
                        'Taban Sıralama': row.get('En Düşük Sıralama', ''),
                        'Taban Puan': row.get('Taban Puan', ''),
                        'Tavan Puan': row.get('Tavan Puan', ''),
                        'Ücret': ucret,
                        'Dil': dil,
                        'Etiket': etiket,
                        'Riskli T': riskli_t_int,
                        'Z Riskli': z_riskli if z_riskli is not None else "",
                        'Parametre': f"{p['puan_turu']} / {p['ogr_siralama']} / {p['sinir']} / {p['riskli_t']}"
                    })
    if not result:
        result = [{'Bölüm Adı': 'Sonuç bulunamadı'}]
    return pd.DataFrame(result)

@app.route("/", methods=["GET", "POST"])
def index():
    # Session'da parametreler ve dosya yolu tutulur
    if "parametreler" not in session:
        session["parametreler"] = []
    parametreler = session["parametreler"]
    excel_path = session.get("excel_path", None)
    df = None
    puan_turu_options = []
    yuklenen_bilgi = None

    if request.method == "POST":
        if "excel" in request.files:
            file = request.files["excel"]
            if file and file.filename.endswith(".xlsx"):
                path = os.path.join(UPLOAD_FOLDER, file.filename)
                file.save(path)
                session["excel_path"] = path
                df = pd.read_excel(path)
                df.columns = df.columns.str.strip()
                session["df_shape"] = (df.shape[0], df.shape[1])
                yuklenen_bilgi = f"Yüklenen veri: {df.shape[0]} satır, {df.shape[1]} sütun"
                # Puan türü seçenekleri güncelle
                if "Puan Türü" in df.columns:
                    puan_turu_options = sorted(df["Puan Türü"].dropna().astype(str).str.strip().str.upper().unique())
                session["puan_turu_options"] = puan_turu_options
                return redirect(url_for("index"))
            else:
                flash("Lütfen bir Excel dosyası (.xlsx) yükleyin.", "danger")
        elif "ekle_param" in request.form:
            puan_turu = request.form.get("puan_turu")
            ogr_siralama = request.form.get("ogr_siralama")
            sinir = request.form.get("sinir")
            riskli_t = request.form.get("riskli_t", "0")
            if puan_turu and ogr_siralama and sinir and puan_turu != "Seçiniz":
                parametreler.append({
                    "puan_turu": puan_turu,
                    "ogr_siralama": ogr_siralama,
                    "sinir": sinir,
                    "riskli_t": riskli_t
                })
                session["parametreler"] = parametreler
            else:
                flash("Lütfen puan türü, öğrenci sıralaması ve taban sıralama sınırı giriniz.", "warning")
            return redirect(url_for("index"))
        elif "sil_param" in request.form:
            idx = int(request.form.get("sil_param"))
            if 0 <= idx < len(parametreler):
                parametreler.pop(idx)
                session["parametreler"] = parametreler
            return redirect(url_for("index"))
        elif "analiz_et" in request.form:
            session["analiz"] = True
            return redirect(url_for("index"))

    # GET veya POST sonrası
    if excel_path and os.path.exists(excel_path):
        df = pd.read_excel(excel_path)
        df.columns = df.columns.str.strip()
        yuklenen_bilgi = f"Yüklenen veri: {df.shape[0]} satır, {df.shape[1]} sütun"
        puan_turu_options = session.get("puan_turu_options", [])
    analiz_df = None
    if session.get("analiz", False) and df is not None and parametreler:
        analiz_df = analiz_yap(df, parametreler)
        session["analiz_df"] = analiz_df.to_dict("records")
        session["analiz"] = False

    # Logo base64
    logo_path = os.path.join("static", "iu.logo.png")
    logo_base64 = get_base64_image(logo_path) if os.path.exists(logo_path) else None
    footer_logo_path = os.path.join("static", "mesela.png")
    footer_logo_base64 = get_base64_image(footer_logo_path) if os.path.exists(footer_logo_path) else None

    return render_template(
        "index.html",
        logo_base64=logo_base64,
        footer_logo_base64=footer_logo_base64,
        yuklenen_bilgi=yuklenen_bilgi,
        df=df,
        parametreler=parametreler,
        puan_turu_options=puan_turu_options,
        analiz_df=analiz_df
    )

@app.route("/indir")
def indir():
    analiz_df = session.get("analiz_df", None)
    if analiz_df:
        df = pd.DataFrame(analiz_df)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Sonuclar')
        output.seek(0)
        return send_file(
            output,
            as_attachment=True,
            download_name="analiz_sonuclari.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        flash("Önce analiz yapmalısınız.", "warning")
        return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
