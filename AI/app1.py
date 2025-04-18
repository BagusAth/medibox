import streamlit as st
import google.generativeai as genai
from pymongo import MongoClient
from bson.json_util import dumps
import certifi
import pandas as pd
from datetime import datetime
import pytz

# ===========================
# KONFIGURASI AWAL
# ===========================
# API Key Gemini
api_key = st.secrets["GEMINI_API"]
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.0-flash')

# MongoDB Config
MONGO_URI = "mongodb+srv://bramantyo989:jkGjM7paFoethotj@cluster0.zgafu.mongodb.net/?appName=Cluster0"
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client["SentinelSIC"]
collection = db["SensorSentinel"]

# Fungsi untuk mendapatkan timestamp lokal
def get_local_timestamp():
    # Ubah sesuai zona waktu lokal yang diinginkan, misal Asia/Jakarta
    local_tz = pytz.timezone("Asia/Jakarta")
    timestamp = datetime.now(local_tz)
    # Format timestamp sebagai string (bisa juga dikembalikan sebagai objek datetime jika perlu)
    return timestamp.strftime("%Y-%m-%d %H:%M:%S")

# ===========================
# PENGATURAN SESSION STATE
# ===========================
if 'page' not in st.session_state:
    st.session_state.page = 'main'
if 'medical_history' not in st.session_state:
    st.session_state.medical_history = ''
if 'generated_questions' not in st.session_state:
    st.session_state.generated_questions = []
if 'answers' not in st.session_state:
    st.session_state.answers = []
if 'current_question' not in st.session_state:
    st.session_state.current_question = 0
if 'sensor_history' not in st.session_state:
    st.session_state.sensor_history = None
if 'reset_obat_count' not in st.session_state:
    st.session_state.reset_obat_count = False

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

from datetime import timedelta

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
        
        # Reset counter jika diminta
        if st.session_state.reset_obat_count:
            obat_count = 0
            st.session_state.reset_obat_count = False

        for record in records:
            changes = {}
            for key in ['temperature', 'humidity', 'ldr_value']:
                current_val = record.get(key)
                changes[key] = current_val
                last[key] = current_val

            # Logika untuk menghitung penambahan obat
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
                # Jika transisi dari < 1000 ke >= 1000, tambah counter obat
                if previous_ldr < 1000 and current_ldr >= 1000:
                    obat_count += 1
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

            changes['jumlah obat diminum'] = obat_count
            
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
    Anda adalah dokter profesional. Buat 3-5 pertanyaan spesifik tentang gejala 
    yang mungkin terkait dengan riwayat penyakit berikut dan data sensor terbaru:
    
    Riwayat Pasien: {history}
    {sensor_info}
    
    Format output:
    - Apakah Anda mengalami [gejala spesifik]?
    - Apakah Anda merasa [gejala spesifik]?
    
    Perhatikan data sensor dalam membuat pertanyaan yang relevan.
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
    """Generate personalized recommendations"""
    try:
        # Get latest sensor data
        latest_sensor_data = get_sensor_data()
        
        # Get medication consumption history
        medication_info = ""
        obat_count = 0
        temp_avg = 0
        
        # Get medication history and temperature data from sensor history
        if st.session_state.sensor_history is not None and not st.session_state.sensor_history.empty:
            df = st.session_state.sensor_history
            obat_count = df['jumlah obat diminum'].max() if 'jumlah obat diminum' in df.columns else 0
            temp_avg = df['temperature'].mean() if 'temperature' in df.columns else 0
            
            medication_info = f"""
            4. Informasi Penggunaan Obat:
               - Total obat yang telah diminum: {obat_count}
               - Rata-rata suhu penyimpanan: {temp_avg:.1f} °C
            """
        
        sensor_info = ""
        if latest_sensor_data:
            sensor_info = f"""
            3. Data Sensor Terbaru:
               - Suhu: {latest_sensor_data.get('temperature', 'N/A')} °C
               - Kelembaban: {latest_sensor_data.get('humidity', 'N/A')}%
               - Nilai LDR: {latest_sensor_data.get('ldr_value', 'N/A')}
            """
            
        history = st.session_state.medical_history or "Tidak ada riwayat"
        symptoms = "\n".join([
            f"{q} - {'Ya' if a else 'Tidak'}" 
            for q, a in zip(st.session_state.generated_questions, st.session_state.answers)
        ])
        
        prompt = f"""
        Analisis riwayat medis, gejala, data sensor, dan kepatuhan penggunaan obat berikut:
        
        1. Riwayat Medis: {history}
        2. Gejala:
        {symptoms}
        {sensor_info}
        {medication_info}
        
        Berikan rekomendasi dalam Bahasa Indonesia dengan format:
        - Analisis kondisi kesehatan
        - Evaluasi kepatuhan penggunaan obat (apakah jumlah obat yang diminum sesuai dengan kebutuhan)
        - Analisis kondisi penyimpanan obat (evaluasi suhu penyimpanan, idealnya 15-25°C)
        - Tindakan medis yang diperlukan
        - Langkah pencegahan
        - Rekomendasi dokter spesialis (jika perlu)
        - Tips perawatan mandiri
        
        Pertimbangkan data sensor dan konsumsi obat dalam analisis Anda.
        Gunakan format markdown dengan poin-point jelas.
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Error generating recommendations: {str(e)}")
        return None

# ===========================
# HALAMAN APLIKASI
# ===========================
def main_page():
    """Halaman Utama"""
    st.title("🩺 Aplikasi Pemeriksaan Kesehatan")
    st.header("Apakah kamu merasa sakit hari ini?")
    
    # Inisialisasi session state
    if 'show_healthy_message' not in st.session_state:
        st.session_state.show_healthy_message = False

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Ya", help="Klik jika merasa tidak sehat", type="primary"):
            st.session_state.page = 'medical_history'
            st.session_state.show_healthy_message = False
            st.rerun()
    with col2:
        if st.button("Tidak", help="Klik jika merasa sehat"):
            st.session_state.show_healthy_message = True
            st.rerun()
    if st.session_state.show_healthy_message:
        st.success("""
            🎉 **Bagus! Tetap jaga kesehatan dan perhatikan kondisi tubuh Anda.**\n\n
            🥗 *Tetap patuhi pola hidup sehat!*\n\n
            ⚠️ Jika ada gejala yang muncul, silakan kembali ke aplikasi ini.
        """)
        # Tombol untuk menutup pesan
        if st.button("Tutup Pesan", key="close_message"):
            st.session_state.show_healthy_message = False
            st.rerun()
    st.divider()
    st.subheader("📚 Riwayat Perubahan Sensor")
    # Tombol Refresh Manual untuk data sensor historis
    if st.button("🔃 Refresh Riwayat Sensor"):
        new_history = get_sensor_history()
        if not new_history.empty:
            st.session_state.sensor_history = new_history
        else:
            latest_data = get_sensor_data()
            if latest_data and st.session_state.sensor_history is not None and not st.session_state.sensor_history.empty:
                st.session_state.sensor_history.loc[st.session_state.sensor_history.index[-1], 'temperature'] = latest_data.get('temperature')
                st.session_state.sensor_history.loc[st.session_state.sensor_history.index[-1], 'humidity'] = latest_data.get('humidity')

    if st.session_state.sensor_history is None or st.session_state.sensor_history.empty:
        st.session_state.sensor_history = get_sensor_history()

    df = st.session_state.sensor_history
    st.dataframe(df.sort_values(by="timestamp", ascending=False), use_container_width=True)

def medical_history_page():
    """Halaman Riwayat Medis"""
    st.title("📋 Riwayat Medis")
    
    # Get latest sensor data
    latest_sensor_data = get_sensor_data()
    
    # Display sensor information if available
    if latest_sensor_data:
        with st.expander("Data Sensor Medibox", expanded=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Suhu", f"{latest_sensor_data.get('temperature', 'N/A')} °C")
            with col2:
                st.metric("Kelembaban", f"{latest_sensor_data.get('humidity', 'N/A')}%")
            with col3:
                st.metric("Intensitas Cahaya", latest_sensor_data.get('ldr_value', 'N/A'))
    
    with st.form("medical_form"):
        st.write("Mohon isi informasi berikut!")
        history = st.text_area(
            "Riwayat penyakit/kondisi medis yang pernah dimiliki :",
            height=150,
            key="medical_history"
        )
        
        if st.form_submit_button("Lanjutkan"):
            if history.strip():
                # Pass sensor data to question generator
                questions = generate_medical_questions(history, latest_sensor_data)
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

def questioning_page():
    """Halaman Pertanyaan Gejala"""
    st.title("🔍 Pemeriksaan Gejala")
    
    if st.session_state.current_question < len(st.session_state.generated_questions):
        current_q = st.session_state.generated_questions[st.session_state.current_question]
        
        # Header Progress
        st.subheader(f"Pertanyaan {st.session_state.current_question + 1}/{len(st.session_state.generated_questions)}")
        st.progress((st.session_state.current_question + 1)/len(st.session_state.generated_questions))
        
        # Pertanyaan
        st.markdown(f"**{current_q.replace('-', '•')}**")
        
        # Tombol Jawaban
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Ya ✅", key=f"yes_{st.session_state.current_question}"):
                st.session_state.answers.append(True)
                st.session_state.current_question += 1
                st.rerun()
        with col2:
            if st.button("Tidak ❌", key=f"no_{st.session_state.current_question}"):
                st.session_state.answers.append(False)
                st.session_state.current_question += 1
                st.rerun()
    else:
        st.session_state.page = 'results'
        st.rerun()

def results_page():
    """Halaman Hasil Akhir"""
    st.title("📝 Hasil Analisis")
    
    # Generate Rekomendasi
    with st.spinner("🔄 Membuat analisis khusus untuk Anda..."):
        recommendations = generate_recommendations()
    
    # Tampilkan Hasil
    st.subheader("📊 Ringkasan Jawaban")
    st.write(f"Total gejala yang dialami: {sum(st.session_state.answers)} dari {len(st.session_state.answers)}")
    
    st.subheader("💡 Rekomendasi Medis")
    if recommendations:
        st.markdown(recommendations)
    else:
        st.warning("""
        **Rekomendasi Umum:**
        - Konsultasikan ke dokter umum terdekat
        - Pantau perkembangan gejala
        - Istirahat yang cukup
        - Hindari aktivitas berat
        """)
    
    # Tombol Reset
    st.divider()
    if st.button("🔄 Mulai Pemeriksaan Baru"):
        st.session_state.page = 'main'
        st.rerun()

# Jika ada halaman sensor terpisah (jika diperlukan)
def sensor_page():
    st.title("📊 Data Sensor")
    # Implementasi halaman sensor jika diperlukan
    st.write("Halaman ini untuk data sensor secara khusus.")

# ===========================
# ROUTING HALAMAN
# ===========================
if st.session_state.page == 'main':
    main_page()
elif st.session_state.page == 'medical_history':
    medical_history_page()
elif st.session_state.page == 'questioning':
    questioning_page()
elif st.session_state.page == 'results':
    results_page()
elif st.session_state.page == 'sensor':
    sensor_page()

# ===========================
# FOOTER
# ===========================
st.divider()
st.caption("⚠️ Aplikasi ini bukan pengganti diagnosis medis profesional. Selalu konsultasikan dengan tenaga kesehatan terkait kondisi medis Anda.")
