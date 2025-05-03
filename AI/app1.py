import streamlit as st
import google.generativeai as genai
from pymongo import MongoClient
from bson.json_util import dumps
import certifi
import pandas as pd
from datetime import datetime, timedelta
import pytz

# ===========================
# KONFIGURASI AWAL
# ===========================
# API Key Gemini
api_key = st.secrets["GEMINI_API"]
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.0-flash')

# MongoDB Config
MONGO_URI = st.secrets["MONGO_URI"]
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client["SentinelSIC"]
collection = db["SensorSentinel"]
boxcfg_coll = db["IdUserBox"]  # Koleksi konfigurasi kotak
hide_menu_style = """
    <style>
    #MainMenu {visibility: hidden;}
    </style>
"""
st.markdown(hide_menu_style, unsafe_allow_html=True)

# Fungsi untuk mendapatkan timestamp lokal
def get_local_timestamp():
    local_tz = pytz.timezone("Asia/Jakarta")
    timestamp = datetime.now(local_tz)
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")

# ===========================
# PENGATURAN SESSION STATE
# ===========================
session_defaults = {
    'page': 'login',
    'box_id': None,
    'box_cfg': {},
    'medical_history': '',
    'generated_questions': [],
    'answers': [],
    'current_question': 0,
    'sensor_history': None,
    'reset_obat_count': False,
    'show_healthy_message': False
}

for key, val in session_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# Check for URL parameters to auto-login
if 'box_id' in st.query_params and st.session_state.page == 'login':
    box_id = st.query_params['box_id']
    # Verify the box_id exists in the database
    cfg = boxcfg_coll.find_one({"box_id": box_id})
    if cfg:
        st.session_state.box_id = box_id
        st.session_state.box_cfg = cfg
        st.session_state.page = 'confirm_config'  # Navigate to confirm page instead of directly to config
        st.rerun()
    else:
        st.error(f"❌ ID Kotak '{box_id}' tidak ditemukan dalam database.")

# ===========================
# FUNGSI PENDUKUNG
# ===========================
def get_sensor_data():
    try:
        latest = list(collection.find().sort("timestamp", -1).limit(1))
        return latest[0] if latest else None
    except Exception as e:
        st.error(f"Gagal mengambil data dari MongoDB: {str(e)}")
        return None

def get_sensor_history(limit=2000):
    try:
        # Ambil riwayat data sensor terbaru dari MongoDB
        records = list(collection.find().sort("timestamp", -1).limit(limit))
        # Urutkan dari yang paling lama ke terbaru
        records.reverse()  

        filtered_changes = []
        last = {}
        obat_count = 0  # Inisialisasi counter untuk jumlah obat
        previous_ldr = None  # Nilai ldr sebelumnya
        last_timestamp = None  # Track the last time we added a record
        medications_taken = 0  # Jumlah obat yang telah diambil
        
        # Ambil informasi last_updated dan jumlah obat dari konfigurasi box
        box_config = None
        if st.session_state.box_id and st.session_state.box_cfg:
            box_config = st.session_state.box_cfg
            last_updated = box_config.get('last_updated')
            current_med_count = box_config.get('Jumlah_obat', 0)
            
            # Convert last_updated ke format datetime jika ada
            if last_updated:
                if isinstance(last_updated, datetime):
                    config_last_updated = last_updated
                else:
                    try:
                        config_last_updated = datetime.fromisoformat(str(last_updated))
                    except:
                        config_last_updated = None
            else:
                config_last_updated = None
        else:
            config_last_updated = None
            current_med_count = 0
        
        # Reset counter jika diminta
        if st.session_state.reset_obat_count:
            medications_taken = 0
            st.session_state.reset_obat_count = False

        for record in records:
            changes = {}
            for key in ['temperature', 'humidity', 'ldr_value']:
                current_val = record.get(key)
                changes[key] = current_val
                last[key] = current_val

            # Logika untuk menghitung pengambilan obat
            current_ldr = record.get('ldr_value')
            
            # Tambahkan status kotak (terbuka/tertutup)
            if current_ldr >= 1000:
                changes['status_kotak'] = "TERBUKA 📂"
            else:
                changes['status_kotak'] = "TERTUTUP 📁"
            
            # Get current timestamp
            timestamp = record.get('timestamp')
            current_timestamp = pd.to_datetime(timestamp) if timestamp else None
            
            # Cek apakah ini data pertama atau ada perubahan signifikan pada LDR atau sudah lewat 1 jam
            add_record = False
            
            # Jika ini data pertama, tambahkan
            if previous_ldr is None or last_timestamp is None:
                add_record = True
            # Atau jika ada perubahan signifikan pada LDR (crossing 1000 threshold)
            elif (previous_ldr < 1000 and current_ldr >= 1000) or (previous_ldr >= 1000 and current_ldr < 1000):
                add_record = True
                # Jika transisi dari < 1000 ke >= 1000 (kotak dibuka) 
                # Dan waktu setelah last_updated konfigurasi
                if (previous_ldr < 1000 and current_ldr >= 1000 and 
                    config_last_updated and current_timestamp and 
                    current_timestamp > config_last_updated):
                    medications_taken += 1
                    # Update jumlah obat di database jika perlu
                    if current_med_count > medications_taken:
                        new_count = current_med_count - medications_taken
                        # Hanya update jika telah login dan ada ID kotak
                        if st.session_state.box_id:
                            try:
                                boxcfg_coll.update_one(
                                    {"box_id": st.session_state.box_id},
                                    {"$set": {"Jumlah_obat": new_count}}
                                )
                                # Update juga di session state
                                if st.session_state.box_cfg:
                                    st.session_state.box_cfg["Jumlah_obat"] = new_count
                            except Exception as e:
                                st.error(f"Gagal memperbarui jumlah obat: {str(e)}")
            # Atau jika sudah lebih dari 1 jam sejak update terakhir
            elif current_timestamp and last_timestamp and (current_timestamp - last_timestamp).total_seconds() >= 3600:  # 3600 seconds = 1 hour
                add_record = True
            
            previous_ldr = current_ldr

            # Tambahkan jumlah obat dan waktu yang disesuaikan
            if timestamp:
                adjusted_timestamp = pd.to_datetime(timestamp) + timedelta(hours=7)
                changes['timestamp'] = adjusted_timestamp
            else:
                changes['timestamp'] = None

            # Hitung sisa obat yang sebenarnya
            remaining_meds = max(0, current_med_count - medications_taken)
            changes['sisa_obat'] = remaining_meds
            changes['obat_diambil'] = medications_taken
            
            # Hanya tambahkan record jika perlu
            if add_record:
                filtered_changes.append(changes)
                last_timestamp = current_timestamp  # Update the last timestamp we added

        return pd.DataFrame(filtered_changes)
    except Exception as e:
        st.error(f"Gagal mengambil riwayat sensor: {str(e)}")
        return pd.DataFrame()
    
# fungsi untuk menyimpan data sensor dengan timestamp lokal ke MongoDB
def insert_sensor_data(temperature, humidity, ldr_value):
    sensor_data = {
        "temperature": temperature,
        "humidity": humidity,
        "ldr_value": ldr_value,
        "timestamp": get_local_timestamp()  # Menggunakan timestamp lokal
    }
    try:
        collection.insert_one(sensor_data)
    except Exception as e:
        st.error(f"Gagal menyimpan data sensor: {str(e)}")

def generate_medical_questions(history, sensor_data=None):
    """Generate medical questions based on history and sensor data"""
    
    # Include sensor data in prompt if available
    sensor_info = ""
    if sensor_data is not None:
        sensor_info = f"""
        Data Sensor Terbaru:
        - Suhu: {sensor_data.get('temperature', 'N/A')} °C
        - Kelembaban: {sensor_data.get('humidity', 'N/A')}%
        - Nilai LDR (Intensitas Cahaya): {sensor_data.get('ldr_value', 'N/A')}
        """
    
    prompt = f"""
    Anda adalah dokter profesional. Buat 3-5 pertanyaan dengan jawaban ya atau tidak spesifik tentang gejala 
    yang mungkin terkait dengan riwayat penyakit berikut dan data terbaru:
    
    Riwayat Pasien: {history}
    {sensor_info}
    
    Format output:
    - Apakah Anda mengalami [gejala spesifik]?
    - Apakah Anda merasa [gejala spesifik]?
    
    Perhatikan data dalam membuat pertanyaan yang relevan.
    Asumsikan data selain yang tersedia di atas adalah normal.
    Misalnya, jika suhu tinggi, tanyakan tentang gejala demam. 
    Jika kelembaban rendah, tanyakan tentang gejala kulit kering.
    
    Hanya berikan list pertanyaan tanpa penjelasan tambahan.
    """
    try:
        response = model.generate_content(prompt)
        questions = response.text.split('\n')
        return [q.strip() for q in questions if q.strip() and q.startswith('-')]
    except Exception as e:
        st.error(f"Gagal membuat pertanyaan: {str(e)}")
        return []
    
def generate_recommendations():
    """Generate personalized recommendations based on configuration data"""
    try:
        # Get configuration data instead of sensor data
        cfg = st.session_state.box_cfg or {}
        
        # Format configuration information
        config_info = f"""
        4. Informasi Kotak Medibox:
           - Penyakit/Kondisi: {cfg.get('nama_penyakit', 'Tidak diatur')}
           - Nama Obat: {cfg.get('medication_name', 'Tidak diatur')}
           - Jumlah Obat: {cfg.get('Jumlah_obat', 0)}
           - Usia Pasien: {cfg.get('usia', 'Tidak diatur')} tahun
           - Jenis Kelamin Pasien: {cfg.get('jenis_kelamin', 'Tidak diatur')}
           - Riwayat Alergi: {cfg.get('riwayat_alergi', 'Tidak diatur')}
           - Aturan Penyimpanan: {cfg.get('storage_rules', 'Tidak diatur')}
           - Aturan Minum: {cfg.get('dosage_rules', 'Tidak diatur')}
        """
        
        history = st.session_state.medical_history or "Tidak ada riwayat"
        symptoms = "\n".join([
            f"{q} - {'Ya' if a else 'Tidak'}" 
            for q, a in zip(st.session_state.generated_questions, st.session_state.answers)
        ])
        
        prompt = f"""
        Analisis riwayat medis, gejala, dan informasi konfigurasi obat berikut:
        
        1. Riwayat Medis: {history}
        2. Gejala:
        {symptoms}
        {config_info}
        
        Berikan rekomendasi dalam Bahasa Indonesia dengan format:
        - Analisis kondisi kesehatan
        - Evaluasi kesesuaian penggunaan obat dengan kondisi pasien
        - Tindakan medis yang diperlukan
        - Langkah pencegahan
        - Rekomendasi dokter spesialis (jika perlu)
        - Tips perawatan mandiri
        
        Pertimbangkan informasi konfigurasi obat dalam analisis Anda.
        Gunakan format markdown dengan poin-point jelas.
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Error generating recommendations: {str(e)}")
        return None

def generate_diet_plan(history):
    """Generate diet recommendations based on medical history"""
    # Get configuration data for age and gender
    cfg = st.session_state.box_cfg or {}
    usia = cfg.get('usia')
    jenis_kelamin = cfg.get('jenis_kelamin')
    riwayat_alergi = cfg.get('riwayat_alergi', 'Tidak ada')
    
    prompt = f"""
    Anda adalah ahli gizi profesional. Berdasarkan riwayat penyakit/kondisi medis berikut,
    rekomendasikan pola makan harian dengan daftar makanan dan kandungan nutrisinya.

    Riwayat Pasien: {history}
    Usia Pasien: {usia} tahun
    Jenis Kelamin Pasien: {jenis_kelamin}
    Riwayat Alergi: {riwayat_alergi}

    Format output:
    - Makanan: [nama makanan] - Kandungan: [kalori, protein, lemak, karbohidrat, vitamin/mineral]
    - Sajikan 3-5 rekomendasi makanan utama.
    - Hindari makanan yang dapat memicu alergi pasien.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Error generating diet plan: {str(e)}")
        return "Tidak dapat membuat rekomendasi pola makan saat ini."

# ===========================
# HALAMAN LOGIN DAN KONFIGURASI
# ===========================
def login_page():
    st.title("🔐 Login Kotak Obat")
    with st.form("login_form"):
        box_id = st.text_input("Masukkan ID Kotak")
        submitted = st.form_submit_button("Masuk")
        if submitted:
            if not box_id.strip():
                st.warning("ID tidak boleh kosong")
            else:
                cfg = boxcfg_coll.find_one({"box_id": box_id})
                if cfg is None:
                    st.error("❌ ID Kotak tidak terdaftar. Silakan periksa kembali ID anda.")
                else:
                    st.session_state.box_id = box_id
                    st.session_state.box_cfg = cfg
                    st.session_state.page = 'confirm_config'  # Changed from 'config' to 'confirm_config'
                    st.rerun()

def confirm_config_page():
    """Halaman konfirmasi untuk mengubah konfigurasi atau langsung ke halaman utama"""
    st.title("✅ Login Berhasil")
    
    # Display current box configuration
    cfg = st.session_state.box_cfg
    
    # Check if all required fields are configured (except riwayat_alergi)
    nama_penyakit = cfg.get('nama_penyakit', '')
    medication_name = cfg.get('medication_name', '')
    usia = cfg.get('usia', None)
    jenis_kelamin = cfg.get('jenis_kelamin', '')
    storage_rules = cfg.get('storage_rules', '')
    dosage_rules = cfg.get('dosage_rules', '')
    jumlah_obat = cfg.get('Jumlah_obat', None)
    
    # Check each field is properly set
    is_condition_set = (
        nama_penyakit and nama_penyakit.strip() != '' and nama_penyakit.lower() != 'belum diatur'
        and medication_name and medication_name.strip() != '' and medication_name.lower() != 'belum diatur'
        and usia is not None
        and jenis_kelamin and jenis_kelamin.strip() != '' and jenis_kelamin.lower() != 'belum diatur'
        and storage_rules and storage_rules.strip() != '' and storage_rules.lower() != 'belum diatur'
        and dosage_rules and dosage_rules.strip() != '' and dosage_rules.lower() != 'belum diatur'
        and jumlah_obat is not None and jumlah_obat >= 0
    )
    
    col1, col2 = st.columns(2)
    with col1:
        st.info("**Informasi Saat Ini:**")
        st.write(f"**Penyakit/Kondisi:** {cfg.get('nama_penyakit', 'Belum diatur')}")
        st.write(f"**Nama Obat:** {cfg.get('medication_name', 'Belum diatur')}")
        st.write(f"**Jumlah Obat:** {cfg.get('Jumlah_obat', 0)}")
        st.write(f"**Usia:** {cfg.get('usia', 'Belum diatur')}")
        st.write(f"**Jenis Kelamin:** {cfg.get('jenis_kelamin', 'Belum diatur')}")
        st.write(f"**Riwayat Alergi:** {cfg.get('riwayat_alergi', 'Belum diatur')}")
        
        # Format last updated time if available
        last_updated = cfg.get('last_updated', None)
        if last_updated:
            try:
                # If it's already a datetime object
                if isinstance(last_updated, datetime):
                    # Add 7 hours for Asia/Jakarta timezone
                    last_updated_str = (last_updated + timedelta(hours=7)).strftime("%d %b %Y, %H:%M")
                else:
                    # Try to parse from string, then add 7 hours
                    last_updated_str = (datetime.fromisoformat(str(last_updated)) + timedelta(hours=7)).strftime("%d %b %Y, %H:%M")
            except:
                last_updated_str = str(last_updated)
            st.write(f"**Terakhir Diperbarui:** {last_updated_str}")   
    # Display a warning if condition is not set
    if not is_condition_set:
        st.warning("⚠️ Informasi belum lengkap. Anda perlu mengatur semua informasi terlebih dahulu.")
        
    # Action buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✏️ Ubah Informasi", type="primary"):
            st.session_state.page = 'config'
            st.rerun()
    
    # Only show the direct to app button if condition is set
    with col2:
        if is_condition_set:
            if st.button("➡️ Langsung ke Aplikasi"):
                st.session_state.page = 'main'
                st.rerun()

def config_page():
    st.title(f"⚙️ Informasi Kotak Obat")
    cfg = st.session_state.box_cfg or {}
    with st.form("cfg_form"):
        nama_penyakit = st.text_input("Nama Penyakit/Kondisi", 
                                     value=cfg.get("nama_penyakit", ""),
                                     help="Kondisi medis yang sedang ditangani")
        med_name = st.text_input("Nama Obat", value=cfg.get("medication_name", ""))
        
        # Add age and gender fields
        col1, col2 = st.columns(2)
        with col1:
            usia = st.number_input("Usia", 
                                min_value=0, 
                                max_value=120, 
                                value=cfg.get("usia", 30),
                                help="Usia pengguna kotak obat")
        with col2:
            gender_options = ["Laki-laki", "Perempuan"]
            default_idx = 0
            if "jenis_kelamin" in cfg:
                if cfg["jenis_kelamin"] in gender_options:
                    default_idx = gender_options.index(cfg["jenis_kelamin"])
            jenis_kelamin = st.selectbox("Jenis Kelamin", 
                                       options=gender_options,
                                       index=default_idx)
        
        # Add riwayat alergi field
        riwayat_alergi = st.text_area("Riwayat Alergi", 
                                      value=cfg.get("riwayat_alergi", ""),
                                      help="Daftar alergi yang dimiliki")
        
        storage = st.text_area("Aturan Penyimpanan", value=cfg.get("storage_rules", ""), height=80)
        dosage = st.text_area("Aturan Minum", value=cfg.get("dosage_rules", ""), height=80)
        
        # Field for Jumlah_obat
        Jumlah_obat = st.number_input("Jumlah Obat", 
                                    min_value=0, 
                                    value=cfg.get("Jumlah_obat", 0),
                                    help="Jumlah obat dalam kotak")
        
        submitted = st.form_submit_button("Simpan Informasi")
        if submitted:
            now = datetime.now(pytz.timezone("Asia/Jakarta"))
            boxcfg_coll.update_one(
                {"box_id": st.session_state.box_id},
                {"$set": {
                    "nama_penyakit": nama_penyakit,
                    "medication_name": med_name,
                    "storage_rules": storage,
                    "dosage_rules": dosage,
                    "Jumlah_obat": int(Jumlah_obat),
                    "usia": int(usia),  # Save age
                    "jenis_kelamin": jenis_kelamin,  # Save gender
                    "riwayat_alergi": riwayat_alergi,  # Save allergy history
                    "last_updated": now
                }},
                upsert=True
            )
            st.success("✅ Informasi disimpan")
            # langsung lanjut ke halaman utama
            st.session_state.page = 'main'
            st.rerun()

# ===========================
# HALAMAN APLIKASI
# ===========================
def main_page():
    st.title("🩺 Aplikasi Pemeriksaan Kesehatan")
    
    
    # Display medicine info from box config
    cfg = st.session_state.box_cfg
    if cfg:
        with st.expander("💊 Informasi Obat", expanded=True):
            st.write(f"**Penyakit/Kondisi   :** {cfg.get('nama_penyakit', 'Belum diatur')}")
            st.write(f"**Nama Obat          :** {cfg.get('medication_name', 'Belum diatur')}")
            st.write(f"**Jumlah Obat        :** {cfg.get('Jumlah_obat', 0)}")
            st.write(f"**Usia               :** {cfg.get('usia', 'Belum diatur')} tahun")
            st.write(f"**Jenis Kelamin      :** {cfg.get('jenis_kelamin', 'Belum diatur')}")
            st.write(f"**Riwayat Alergi     :** {cfg.get('riwayat_alergi', 'Belum diatur')}")
            
            dosage = cfg.get('dosage_rules', '')
            if dosage:
                st.write(f"**Aturan Minum        :** {dosage}")
    if st.button("Ganti Informasi Pengguna", key="change_box"): 
        for k in ['box_id','box_cfg','sensor_history']:
            st.session_state.pop(k, None)
        st.session_state.page = 'login'
        st.rerun()
    st.header("Apakah kamu merasa sakit hari ini?")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Ya", type="primary"): 
            st.session_state.page = 'medical_history'
            st.rerun()
    with c2:
        if st.button("Tidak"): 
            st.session_state.show_healthy_message = True
            st.rerun()
    if st.session_state.show_healthy_message:
        st.success("🎉 Bagus! Tetap jaga kesehatan...")
        if st.button("Tutup Pesan", key="close_message"):
            st.session_state.show_healthy_message = False
            
    

def medical_history_page():
    """Halaman Riwayat Medis"""
    st.title("📋 Riwayat Medis")
    
    # Ambil data konfigurasi dari session state
    cfg = st.session_state.box_cfg
    
    # Tampilkan data konfigurasi sebagai pengganti data sensor
    if cfg:
        with st.expander("📦 Informasi Kotak Medibox", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Penyakit/Kondisi:** {cfg.get('nama_penyakit', 'Belum diatur')}")
                st.markdown(f"**Nama Obat:** {cfg.get('medication_name', 'Belum diatur')}")
                st.markdown(f"**Jumlah Obat:** {cfg.get('Jumlah_obat', 0)}")
                st.markdown(f"**Usia:** {cfg.get('usia', 'Belum diatur')} tahun")
                st.markdown(f"**Jenis Kelamin:** {cfg.get('jenis_kelamin', 'Belum diatur')}")
                st.markdown(f"**Riwayat Alergi:** {cfg.get('riwayat_alergi', 'Belum diatur')}")
            with col2:
                st.markdown("**Aturan Minum:**")
                st.markdown(f"{cfg.get('dosage_rules', 'Belum diatur')}")   
    with st.form("medical_form"):
        st.write("Mohon isi informasi berikut!")
        history = st.text_area(
            "Riwayat penyakit/kondisi medis yang pernah dimiliki :",
            height=150,
            key="medical_history"
        )
        
        if st.form_submit_button("Lanjutkan"):
            if history.strip():
                # Pass configuration data to question generator instead of sensor data
                questions = generate_medical_questions(history)
                if questions:
                    st.session_state.generated_questions = questions
                    st.session_state.page = 'questioning'
                    st.session_state.current_question = 0
                    st.session_state.answers = []
                    st.rerun()
                else:
                    st.error("Gagal membuat pertanyaan. Silakan coba lagi.")
            else:
                st.warning("Mohon isi riwayat medis Anda terlebih dahulu")
    
    # Add back button outside the form
    if st.button("« Kembali ke Halaman Utama", key="back_to_main"):
        st.session_state.page = 'main'
        st.rerun()

def questioning_page():
    st.title("🔍 Pemeriksaan Gejala")
    idx = st.session_state.current_question
    qs = st.session_state.generated_questions
    if idx < len(qs):
        st.subheader(f"Pertanyaan {idx+1}/{len(qs)}")
        st.progress((idx+1)/len(qs))
        st.markdown(f"**{qs[idx].replace('-', '•')}**")
        c1, c2 = st.columns(2)
        if c1.button("Ya ✅", key=f"yes_{idx}"):
            st.session_state.answers.append(True)
            st.session_state.current_question += 1
            if st.session_state.current_question >= len(qs):
                st.session_state.page = 'results'
                st.rerun()  # Add rerun here
            else:
                st.rerun()  # Add rerun for next question
        if c2.button("Tidak ❌", key=f"no_{idx}"):
            st.session_state.answers.append(False)
            st.session_state.current_question += 1
            if st.session_state.current_question >= len(qs):
                st.session_state.page = 'results'
                st.rerun()  # Add rerun here
            else:
                st.rerun()  # Add rerun for next question
    else:
        st.session_state.page = 'results'
        st.rerun()  # Add rerun here


def results_page():
    st.title("📝 Hasil Analisis")
    with st.spinner("🔄 Membuat analisis khusus untuk Anda..."):
        rec = generate_recommendations()
        diet_plan = generate_diet_plan(st.session_state.medical_history)
    
    st.subheader("📊 Ringkasan Jawaban")
    st.write(f"Total gejala yang dialami: {sum(st.session_state.answers)} dari {len(st.session_state.answers)}")
    
    st.subheader("💡 Rekomendasi Medis")
    if rec:
        st.markdown(rec)
    else:
        st.warning(
            "**Rekomendasi Umum:**\n" +
            "- Konsultasikan ke dokter umum terdekat\n" +
            "- Pantau perkembangan gejala\n" +
            "- Istirahat yang cukup\n" +
            "- Hindari aktivitas berat"
        )
        
    # Add diet plan section
    st.subheader("🍏 Rekomendasi Pola Makan")
    st.markdown(diet_plan)
    
    st.divider()
    if st.button("🔄 Mulai Pemeriksaan Baru"):
        st.session_state.page = 'main'
        st.rerun()

def sensor_history_page():
    """Page dedicated to viewing sensor history data"""
    st.title("📚 Riwayat Perubahan Sensor")
    
    # Only load sensor history when this page is accessed
    with st.spinner("Memuat data sensor..."):
        if st.button("🔃 Refresh Riwayat Sensor"):
            st.session_state.sensor_history = get_sensor_history()
            st.success("✅ Data berhasil diperbarui!")
        
        # Load sensor history if not already loaded
        if st.session_state.sensor_history is None:
            st.session_state.sensor_history = get_sensor_history()
    
    # Display the data
    df = st.session_state.sensor_history
    if df is not None and not df.empty:
        # Get last_updated timestamp from box configuration
        last_updated = None
        if st.session_state.box_cfg and 'last_updated' in st.session_state.box_cfg:
            last_updated_raw = st.session_state.box_cfg['last_updated']
            if isinstance(last_updated_raw, datetime):
                last_updated = last_updated_raw
            else:
                try:
                    last_updated = datetime.fromisoformat(str(last_updated_raw))
                except:
                    last_updated = None
        
        # Filter data to show only records after last_updated
        if last_updated and 'timestamp' in df.columns:
            # Convert last_updated to pandas timestamp with timezone adjustment
            adjusted_last_updated = last_updated + timedelta(hours=7)
            # Filter dataframe
            filtered_df = df[df['timestamp'] > adjusted_last_updated]
            
            # Show information about filtering
            st.info(f"📅 Menampilkan data setelah perubahan terakhir: {adjusted_last_updated.strftime('%d %b %Y, %H:%M')}")
            
            # If no data after last_updated
            if filtered_df.empty:
                st.warning("Tidak ada data sensor baru sejak perubahan terakhir.")
            else:
                # Remove specific tracking columns
                if 'obat_diambil' in filtered_df.columns:
                    display_df = filtered_df.drop(columns=['obat_diambil'])
                else:
                    display_df = filtered_df
                
                # Show medication stats
                if 'sisa_obat' in filtered_df.columns:
                    latest_row = filtered_df.iloc[-1]
                    obat_diambil = latest_row.get('obat_diambil', 0)
                    sisa_obat = latest_row.get('sisa_obat', 0)
                    
                    st.info(f"**Informasi Obat:** {obat_diambil} obat telah diambil, sisa {sisa_obat} obat.")
                
                st.dataframe(display_df.sort_values(by="timestamp", ascending=False), use_container_width=True)
        else:
            # If last_updated is not available, display all data
            if 'obat_diambil' in df.columns:
                display_df = df.drop(columns=['obat_diambil'])
            else:
                display_df = df
            
            # Show medication stats
            if 'sisa_obat' in df.columns:
                latest_row = df.iloc[-1]
                obat_diambil = latest_row.get('obat_diambil', 0)
                sisa_obat = latest_row.get('sisa_obat', 0)
                
                st.info(f"**Informasi Obat:** {obat_diambil} obat telah diambil, sisa {sisa_obat} obat.")
            
            st.dataframe(display_df.sort_values(by="timestamp", ascending=False), use_container_width=True)
    else:
        st.info("Tidak ada data sensor yang tersedia.")
        

# ===========================
# SIDEBAR NAVIGATION
# ===========================
# Only show sidebar when not on login/config pages
if st.session_state.page not in ['login', 'config', 'confirm_config']:
    st.sidebar.title("🔀 Menu")
    if st.session_state.box_id:  # Only show navigation when logged in
        menu = st.sidebar.radio("Pilih Halaman:", ["🩺 Pemeriksaan Kesehatan", "📚 Riwayat Sensor"])
    else:
        # Jika belum login, tombol menu tidak aktif
        st.sidebar.info("Silakan login terlebih dahulu")
        menu = "🩺 Pemeriksaan Kesehatan"  # Default menu
else:
    # For pages where sidebar is hidden, we still need to set a default menu value
    # to avoid errors in the routing section
    menu = "🩺 Pemeriksaan Kesehatan"  # Default menu value

# ===========================
# ROUTING
# ===========================
# Determine if we should show login or content pages
if st.session_state.page == 'login':
    login_page()
elif st.session_state.page == 'confirm_config':
    confirm_config_page()
elif st.session_state.page == 'config':
    config_page()
else:
    # Navigation based on sidebar selection when logged in
    if st.session_state.box_id:
        # Display main title after login
        st.title(f"📊 MediBox")
        
        # Route to appropriate content based on sidebar selection
        if menu == "🩺 Pemeriksaan Kesehatan":
            if st.session_state.page == 'main':
                main_page()
            elif st.session_state.page == 'medical_history':
                medical_history_page()
            elif st.session_state.page == 'questioning':
                questioning_page()
            elif st.session_state.page == 'results':
                results_page()
        elif menu == "📚 Riwayat Sensor":
            # Only load sensor history when this option is selected
            sensor_history_page()
    else:
        # If not logged in but not on login page, redirect to login
        st.session_state.page = 'login'
        st.rerun()

# ===========================
# FOOTER
# ===========================
st.divider()
st.caption("⚠️ Aplikasi ini bukan pengganti diagnosis medis profesional.")
