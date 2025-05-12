import streamlit as st
import google.generativeai as genai
from pymongo import MongoClient
from bson.json_util import dumps
import certifi
import pandas as pd
from datetime import datetime, timedelta
import pytz

def set_custom_theme():
    """Apply custom color theme to the app"""
    custom_css = """
    <style>
        /* Main background color */
        .stApp {
            background-color: #fef9e1;
        }
        
        /* NEW: Top line highlight with cream color */
        .stApp > header, div[data-testid="stHeader"] {
            background-color: #e98b1f !important;
            border-bottom: 2px solid #e98b1f;
        }
        
        /* Ensure text in header area is dark color for contrast */
        .stApp > header span, div[data-testid="stHeader"] span,
        .stApp > header div, div[data-testid="stHeader"] div {
            color: #2b2e2d !important;
        }
        
        /* General text color for all elements */
        p, h1, h2, h3, h4, h5, h6, .stMarkdown, div.stText, 
        label, .st-bk, .st-c0, .stTextInput, .stDateInput, 
        .stTimeInput, .stSelectbox, span {
            color: #2b2e2d !important;
        }
        
        /* Sidebar background color */
        [data-testid="stSidebar"] {
            background-color: #fef9e1;
        }
        
        /* Sidebar text color */
        [data-testid="stSidebar"] p, 
        [data-testid="stSidebar"] h1, 
        [data-testid="stSidebar"] h2, 
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] div,
        [data-testid="stSidebar"] label, 
        [data-testid="stSidebar"] .stMarkdown {
            color: #2b2e2d !important;
        }
        
        /* UPDATED: Button styling with stronger specificity for text */
        .stButton button, .stDownloadButton button, button, 
        [data-testid="baseButton-secondary"], [data-testid="baseButton-primary"] {
            background-color: #fef9e1 !important;
            color: #2b2e2d !important;
            border-color: #e98b1f !important;
            border-width: 2px !important;
        }

        /* Gender selectbox and dropdown styling - specifically target these components */
        .stSelectbox > div[data-baseweb="select"] > div, 
        .stSelectbox div[role="listbox"],
        div[data-baseweb="popover"] div[role="listbox"],
        div[data-baseweb="select"] {
            background-color: #fef9e1 !important;
            color: #2b2e2d !important;
        }

        /* Selected option in dropdown */
        .stSelectbox div[role="option"][aria-selected="true"] {
            background-color: rgba(233, 139, 31, 0.2) !important;
            color: #2b2e2d !important;
        }
        
        /* Hover state for options */
        .stSelectbox div[role="option"]:hover {
            background-color: rgba(233, 139, 31, 0.1) !important;
        }
        
        
        /* NEW: Ensure button text color with higher specificity */
        .stButton button span, .stDownloadButton button span,
        button span, button p, button div, button label {
            color: #2b2e2d !important;
        }
        
        /* NEW: Button hover effects */
        .stButton button:hover, .stDownloadButton button:hover, button:hover {
            background-color: #fef9e1 !important;
            border-color: #ff9d23 !important;
            box-shadow: 0px 0px 5px rgba(233, 139, 31, 0.5) !important;
        }
        
        /* NEW: Form input fields styling */
        input, textarea, [data-baseweb="input"], [data-baseweb="textarea"],
        [data-baseweb="select"] .control, [data-baseweb="select"] input,
        .stNumberInput input, .stTextArea textarea, .stTextInput input, 
        .stSelectbox div[role="listbox"], .stDateInput input {
            background-color: #fef9e1 !important;
            color: #2b2e2d !important;
            border-color: #2b2e2d !important;
        }
        
        /* NEW: Multi-select styling */
        .stMultiSelect [data-baseweb="tag"] {
            background-color: #fef9e1 !important;
            color: #2b2e2d !important;
        }
        
        /* NEW: Dropdown menu items */
        div[role="menuitem"], div[role="listbox"] ul li {
            background-color: #fef9e1 !important;
            color: #2b2e2d !important;
        }
        
        /* NEW: Checkbox and Radio button text colors */
        .stCheckbox label, .stRadio label {
            color: #fef9e1 !important;
        }
        
        /* KEEPING: Sidebar checkbox/radio text color */
        [data-testid="stSidebar"] .stRadio label,
        [data-testid="stSidebar"] .stCheckbox label {
            color: #2b2e2d !important;
        }
        
        /* Specific elements that need color adjustments */
        .stTextArea textarea, .stTextInput>div>div>input {
            background-color: #fef9e1 !important;
            color: #2b2e2d !important;
            border: 1px solid #2b2e2d;
        }
        
        /* Dataframe styling for better visibility */
        .dataframe {
            color: #2b2e2d;
        }
        
        /* Divider color */
        hr {
            border-color: #fef9e1;
        }
        
        /* Card/container elements */
        [data-testid="stExpander"] {
            border: 1px solid #fef9e1;
            background-color: rgba(255, 157, 35, 0.7);
        }
        
        /* Success/info messages */
        .st-success, .st-info {
            color: #2b2e2d;
        }
        
        /* Caption text */
        .st-caption {
            color: #e98b1f !important;
        }

        /* Fix for markdown lists */
        .stMarkdown ul, .stMarkdown ol, .stMarkdown li {
            color: #fef9e1 !important;
        }
        
        /* Table styling - SIMPLIFIED AND FIXED */
        .stDataFrame, .dataframe, div[data-testid="stTable"] {
            background-color: #fef9e1 !important;
            color: #2b2e2d !important;
        }

        .stDataFrame table,
        .dataframe, 
        div[data-testid="stTable"] table {
            background-color: #fef9e1 !important;
            color: #2b2e2d !important;
            border: 2px solid #e98b1f !important;
        }

        .stDataFrame th,
        .dataframe th {
            background-color: rgba(233, 139, 31, 0.2) !important;
            color: #2b2e2d !important;
            font-weight: bold !important;
        }

        .stDataFrame td,
        .dataframe td {
            background-color: #fef9e1 !important;
            color: #2b2e2d !important;
        }
        
        /* Table hover effect */
        .stDataFrame tr:hover td {
            background-color: #e98b1f !important;
        }
        
        /* Pagination buttons in tables */
        .stDataFrame button, .stDataFrame [role="button"] {
            background-color: #fef9e1 !important;
            color: #2b2e2d !important;
            border-color: #e98b1f !important;
        }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)
# Add this line after your imports and before any other Streamlit elements
set_custom_theme()
# Add this after set_custom_theme() call
# Add this right after your set_custom_theme() call to override the existing table styling
st.markdown("""
<style>
/* More specific table styling with complete targeting */
div[data-testid="stTable"] table,
.element-container div.dataframe-container,
.element-container div.table-container,
.stDataFrame table,
div.stDataFrame > div {
    background-color: #fef9e1 !important;
    color: #2b2e2d !important;
    border: 2px solid #e98b1f !important;
}

/* Target column headers specifically */
div[data-testid="stTable"] th,
.stDataFrame th,
.dataframe th,
div.dataframe thead th,
div.stDataFrame thead th,
.element-container div.dataframe-container thead th,
.element-container div.table-container thead th,
.index_name,
.col_heading {
    background-color: #fef9e1 !important; 
    color: #2b2e2d !important;
    font-weight: bold !important;
    border: 1px solid #e98b1f !important;
}

/* Target row indices specifically */
div[data-testid="stTable"] tbody th,
.stDataFrame tbody th,
.dataframe tbody th,
div.dataframe tbody th,
.element-container div.dataframe-container tbody th,
.row_heading {
    background-color: #fef9e1 !important;
    color: #2b2e2d !important;
    font-weight: bold !important;
    border: 1px solid #e98b1f !important;
}

/* Regular cells */
div[data-testid="stTable"] td,
.stDataFrame td,
.dataframe td {
    background-color: #fef9e1 !important;
    color: #2b2e2d !important;
    border: 1px solid #e98b1f !important;
}
</style>
""", unsafe_allow_html=True)
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
reminder_collection = db["MedicineReminders"]

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
    'show_healthy_message': False,
    'medication_schedule': None  # Add this line for storing active schedule
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
        medications_taken = 0  # Jumlah obat yang telah diambil
        previous_ldr = None
        last_timestamp = None
        
        # Ambil informasi last_updated dan jumlah obat dari konfigurasi box
        box_config = None
        if st.session_state.box_id and st.session_state.box_cfg:
            box_config = st.session_state.box_cfg
            last_updated = box_config.get('last_updated')
            initial_med_count = box_config.get('Jumlah_obat', 0)  # Renamed to initial_med_count
            
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
            initial_med_count = 0
        
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
                    # REMOVED: Update to database for Jumlah_obat
                    # Only update the tracking variable, not the database
            # Atau jika sudah lebih dari 1 jam sejak update terakhir
            elif current_timestamp and last_timestamp and (current_timestamp - last_timestamp).total_seconds() >= 3600:
                add_record = True
            
            previous_ldr = current_ldr

            # Tambahkan jumlah obat dan waktu yang disesuaikan
            if timestamp:
                adjusted_timestamp = pd.to_datetime(timestamp) + timedelta(hours=7)
                changes['timestamp'] = adjusted_timestamp
            else:
                changes['timestamp'] = None

            # Track medication stats with proper variable names
            changes['jumlah_obat_awal'] = initial_med_count  # Original medication count
            changes['jumlah_obat_diminum'] = medications_taken  # Pills consumed 
            changes['jumlah_obat_saat_ini'] = max(0, initial_med_count - medications_taken)  # Current pills
            
            # Hanya tambahkan record jika perlu
            if add_record:
                filtered_changes.append(changes)
                last_timestamp = current_timestamp

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

def reminder_page():
    """Page for viewing and managing medication reminders"""
    st.title("⏰ Pengingat Obat")
    
    # Initialize reminder collection
    if "reminder_collection" not in globals():
        global reminder_collection
        reminder_collection = db["MedicineReminders"]
    
    # Fetch the active schedule for this box
    schedule = reminder_collection.find_one({"box_id": st.session_state.box_id, "is_active": True})
    if not schedule:
        # If no active schedule found, try to find any schedule for this box
        schedule = reminder_collection.find_one({"box_id": st.session_state.box_id})
    
    if schedule:
        # Display schedule availability with custom styling
        st.markdown("""
        <div style="padding:10px; border-radius:5px; border-left:3px solid #e98b1f; background-color:rgba(233, 139, 31, 0.1);">
          <p style="color:#e98b1f; font-weight:bold; margin-bottom:10px;">✅ Jadwal pengingat tersedia</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Explanation section with custom styling
        st.subheader("ℹ️ Penjelasan")
        if "explanation" in schedule:
            st.markdown(f"""
            <div style="padding:10px; border-radius:5px; border-left:3px solid #e98b1f; background-color:rgba(233, 139, 31, 0.1);">
              <p style="color:#e98b1f; margin-left:15px;">{schedule["explanation"]}</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="padding:10px; border-radius:5px; border-left:3px solid #e98b1f; background-color:rgba(233, 139, 31, 0.1);">
              <p style="color:#e98b1f; margin-left:15px;">Tidak ada penjelasan tersedia untuk jadwal ini.</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Medicine times with custom styling
        st.subheader("⏰ Jadwal Minum Obat")
        if schedule.get("medicine_times", []):

            for entry in schedule.get("medicine_times", []):
                st.info(f"**{entry['time']}** - {entry['message']}")
            
        else:
            st.warning("⚠️ Belum ada jadwal pengingat obat")
        
        # Meal times with custom styling
        st.subheader("🍽️ Jadwal Makan")
        if schedule.get("meal_times", []):
            for entry in schedule.get("meal_times", []):
                st.info(f"**{entry['time']}** - {entry['message']}")
        else:
            st.warning("⚠️ Belum ada jadwal pengingat obat")
        
        # Update last accessed time
        try:
            reminder_collection.update_one(
                {"_id": schedule["_id"]},
                {"$set": {"last_accessed": datetime.now(pytz.timezone("Asia/Jakarta"))}}
            )
        except Exception:
            pass
            
        # Regenerate option
        if st.button("🔄 Perbarui Jadwal"):
            with st.spinner("Memperbarui jadwal..."):
                new_schedule = generate_and_save_medicine_schedule(
                    st.session_state.medical_history or schedule.get("medical_history", ""),
                    st.session_state.box_cfg
                )
                if new_schedule:
                    st.session_state.medication_schedule = new_schedule
                    st.success("✅ Jadwal berhasil diperbarui!")
                    st.rerun()
    else:
        st.markdown("""
        <div style="padding:10px; border-radius:5px; border-left:3px solid #e98b1f; background-color:rgba(233, 139, 31, 0.1);">
          <p style="color:#e98b1f; font-weight:bold; margin-bottom:10px;">⚠️ Belum ada jadwal pengingat obat</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Create schedule option
        if st.button("➕ Buat Jadwal Baru"):
            with st.spinner("Membuat jadwal pengingat..."):
                new_schedule = generate_and_save_medicine_schedule(
                    st.session_state.medical_history or f"Pasien dengan {st.session_state.box_cfg.get('nama_penyakit', '')}",
                    st.session_state.box_cfg
                )
                if new_schedule:
                    st.session_state.medication_schedule = new_schedule
                    st.success("✅ Jadwal berhasil dibuat!")
                    st.rerun()

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
           - Nama Pengguna: {cfg.get('nama', 'Tidak diatur')}
           - Penyakit/Kondisi: {cfg.get('nama_penyakit', 'Tidak diatur')}
           - Nama Obat: {cfg.get('medication_name', 'Tidak diatur')}
           - Jumlah Obat: {cfg.get('Jumlah_obat', 0)}
           - Usia Pasien: {cfg.get('usia', 'Tidak diatur')} tahun
           - Jenis Kelamin Pasien: {cfg.get('jenis_kelamin', 'Tidak diatur')}
           - Riwayat Alergi: {cfg.get('riwayat_alergi', 'Tidak diatur')}
           - Aturan Penyimpanan: {cfg.get('storage_rules', 'Tidak diatur')}
           - Aturan Minum: {cfg.get('dosage_rules', 'Tidak diatur')}
        """
        
        # Add pharmacist notes if available
        catatan_apoteker = cfg.get('catatan_apoteker', '')
        if catatan_apoteker and catatan_apoteker.strip():
            config_info += f"           - Catatan Apoteker: {catatan_apoteker}"
        
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

def display_header_with_logo():
    """Display MediBox header with logo image"""
    st.markdown("""
        <h1 style="margin-top: 5px; margin-left: 10px; padding-top: 0;">MediBox</h1>
        """, unsafe_allow_html=True)
        
def generate_diet_plan(history):
    """Generate diet recommendations based on medical history"""
    # Get configuration data for age and gender
    cfg = st.session_state.box_cfg or {}
    nama = cfg.get('nama', '')
    usia = cfg.get('usia')
    jenis_kelamin = cfg.get('jenis_kelamin')
    riwayat_alergi = cfg.get('riwayat_alergi', 'Tidak ada')
    
    prompt = f"""
    Anda adalah ahli gizi profesional. Berdasarkan riwayat penyakit/kondisi medis berikut,
    rekomendasikan pola makan harian dengan daftar makanan dan kandungan nutrisinya.

    Nama Pasien: {nama}
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
    st.title("✅ Berhasil Masuk Medibox")
    
    # Display current box configuration
    cfg = st.session_state.box_cfg
    
    # Check if all required fields are configured (except riwayat_alergi and catatan_apoteker)
    nama = cfg.get('nama', '')
    nama_penyakit = cfg.get('nama_penyakit', '')
    medication_name = cfg.get('medication_name', '')
    usia = cfg.get('usia', None)
    jenis_kelamin = cfg.get('jenis_kelamin', '')
    storage_rules = cfg.get('storage_rules', '')
    dosage_rules = cfg.get('dosage_rules', '')
    jumlah_obat = cfg.get('Jumlah_obat', None)
    
    # Check each field is properly set (catatan_apoteker can be empty)
    is_condition_set = (
        nama and nama.strip() != '' and nama.lower() != 'belum diatur'
        and nama_penyakit and nama_penyakit.strip() != '' and nama_penyakit.lower() != 'belum diatur'
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
        st.write(f"**Nama Pengguna:** {cfg.get('nama', 'Belum diatur')}")
        st.write(f"**Penyakit/Kondisi:** {cfg.get('nama_penyakit', 'Belum diatur')}")
        st.write(f"**Nama Obat:** {cfg.get('medication_name', 'Belum diatur')}")
        st.write(f"**Jumlah Obat:** {cfg.get('Jumlah_obat', 0)}")
        st.write(f"**Usia:** {cfg.get('usia', 'Belum diatur')}")
        st.write(f"**Jenis Kelamin:** {cfg.get('jenis_kelamin', 'Belum diatur')}")
        st.write(f"**Riwayat Alergi:** {cfg.get('riwayat_alergi', 'Belum diatur')}")
        
        # Display pharmacist notes if available
        catatan_apoteker = cfg.get('catatan_apoteker', '')
        if catatan_apoteker and catatan_apoteker.strip():
            st.write(f"**Catatan Apoteker:** {catatan_apoteker}")
        else:
            st.write("**Catatan Apoteker:** Tidak ada")
            
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
        nama = st.text_input("Nama Pengguna", 
                           value=cfg.get("nama", ""),
                           help="Nama lengkap pengguna kotak obat")
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
        
        # Add catatan apoteker field
        catatan_apoteker = st.text_area("Catatan Apoteker", 
                                       value=cfg.get("catatan_apoteker", ""),
                                       help="Catatan khusus dari apoteker (opsional)",
                                       height=100)
        
        # Field for Jumlah_obat
        Jumlah_obat = st.number_input("Jumlah Obat", 
                                    min_value=0, 
                                    value=cfg.get("Jumlah_obat", 0),
                                    help="Jumlah obat dalam kotak")
        
        submitted = st.form_submit_button("Simpan Informasi")
        if submitted:
            now = datetime.now(pytz.timezone("Asia/Jakarta"))
            
            # Create updated configuration document
            updated_cfg = {
                "nama": nama,
                "nama_penyakit": nama_penyakit,
                "medication_name": med_name,
                "storage_rules": storage,
                "dosage_rules": dosage,
                "Jumlah_obat": int(Jumlah_obat),
                "usia": int(usia),
                "jenis_kelamin": jenis_kelamin,
                "riwayat_alergi": riwayat_alergi,
                "catatan_apoteker": catatan_apoteker,  # Add pharmacist notes
                "last_updated": now
            }
            
            # Update database
            boxcfg_coll.update_one(
                {"box_id": st.session_state.box_id},
                {"$set": updated_cfg},
                upsert=True
            )
            
            # Update session state with new config
            st.session_state.box_cfg = {**st.session_state.box_cfg, **updated_cfg}
            
            # Generate medication schedule automatically
            with st.spinner("Membuat jadwal pengingat obat..."):
                # Get existing medical history if available
                medical_history = st.session_state.medical_history or f"Pasien dengan {nama_penyakit}" 
                
                # Generate and save medication schedule
                schedule = generate_and_save_medicine_schedule_from_config(
                    medical_history=medical_history,
                    box_cfg=st.session_state.box_cfg
                )
                
                if schedule:
                    st.session_state.medication_schedule = schedule
                    st.success("✅ Informasi dan jadwal pengingat berhasil dibuat dan disimpan!")
                else:
                    st.success("✅ Informasi disimpan, tetapi jadwal pengingat gagal dibuat.")
            
            # Navigate to main page
            st.session_state.page = 'main'
            st.rerun()

# ===========================
# HALAMAN APLIKASI
# ===========================
def main_page():
    # Create personalized greeting based on gender and name
    cfg = st.session_state.box_cfg
    if cfg:
        nama = cfg.get('nama', '')
        jenis_kelamin = cfg.get('jenis_kelamin', '')
        
        if nama:
            # Use Nyonya for women, Tuan for men
            title_prefix = "Nyonya" if jenis_kelamin == "Perempuan" else "Tuan"
            st.header(f"👋 Selamat Datang, {title_prefix} {nama}!")
    
    st.title("🩺 Aplikasi Pemeriksaan Kesehatan")
    
    # Display medicine info with styled orange themed box
    if cfg:
        # Display medicine info with styled orange themed box
        medicine_info = f"""
        <div style="padding:10px; border-radius:5px; border-left:3px solid #e98b1f; background-color:rgba(233, 139, 31, 0.1);">
          <p style="color:#e98b1f; font-weight:bold; margin-bottom:10px;">💊 Informasi Obat:</p>
          <p style="color:#e98b1f; margin-left:15px;">• <strong>Nama Pengguna:</strong> {cfg.get('nama', 'Belum diatur')}</p>
          <p style="color:#e98b1f; margin-left:15px;">• <strong>Penyakit/Kondisi:</strong> {cfg.get('nama_penyakit', 'Belum diatur')}</p>
          <p style="color:#e98b1f; margin-left:15px;">• <strong>Nama Obat:</strong> {cfg.get('medication_name', 'Belum diatur')}</p>
          <p style="color:#e98b1f; margin-left:15px;">• <strong>Jumlah Obat:</strong> {cfg.get('Jumlah_obat', 0)}</p>
          <p style="color:#e98b1f; margin-left:15px;">• <strong>Usia:</strong> {cfg.get('usia', 'Belum diatur')} tahun</p>
          <p style="color:#e98b1f; margin-left:15px;">• <strong>Jenis Kelamin:</strong> {cfg.get('jenis_kelamin', 'Belum diatur')}</p>
          <p style="color:#e98b1f; margin-left:15px;">• <strong>Riwayat Alergi:</strong> {cfg.get('riwayat_alergi', 'Belum diatur')}</p>
        """
        
        # Add pharmacist notes if available
        catatan_apoteker = cfg.get('catatan_apoteker', '')
        if catatan_apoteker and catatan_apoteker.strip():
            medicine_info += f'<p style="color:#e98b1f; margin-left:15px;">• <strong>Catatan Apoteker:</strong> {catatan_apoteker}</p>'
        else:
            medicine_info += '<p style="color:#e98b1f; margin-left:15px;">• <strong>Catatan Apoteker:</strong> Tidak ada</p>'
        
        # Add dosage rules if available
        dosage = cfg.get('dosage_rules', '')
        if dosage:
            medicine_info += f'<p style="color:#e98b1f; margin-left:15px;">• <strong>Aturan Minum:</strong> {dosage}</p>'
        
        # Close the div and display the formatted info
        medicine_info += "</div>"
        st.markdown(medicine_info, unsafe_allow_html=True)
    if st.button("Ganti Informasi Pengguna", key="change_box"): 
        # Keep the box_id, just navigate to config page
        st.session_state.page = 'config'
        # Clear sensor_history to refresh it later if needed
        if 'sensor_history' in st.session_state:
            st.session_state.pop('sensor_history', None)
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
                st.markdown(f"**Nama Pengguna:** {cfg.get('nama', 'Belum diatur')}")
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
    
    # Get user's gender from configuration
    cfg = st.session_state.box_cfg or {}
    jenis_kelamin = cfg.get('jenis_kelamin', '')
    
    # Set appropriate title based on gender
    title_prefix = "Nyonya" if jenis_kelamin == "Perempuan" else "Tuan"
    
    # Use personalized spinner message
    with st.spinner(f"🔄 Mohon tunggu sebentar {title_prefix}..."):
        rec = generate_recommendations()
        diet_plan = generate_diet_plan(st.session_state.medical_history)
        
        # Generate medication schedule
        medication_schedule = generate_and_save_medicine_schedule(
            st.session_state.medical_history,
            st.session_state.box_cfg
        )
        
        # Store in session state for other pages
        if medication_schedule:
            st.session_state.medication_schedule = medication_schedule

    # Display medical recommendations
    if rec:
        st.subheader("📋 Rekomendasi Medis")
        st.markdown(rec)
    
    # Display diet recommendations
    if diet_plan:
        st.subheader("🍎 Rekomendasi Pola Makan")
        st.markdown(diet_plan)
    
    # Display medication schedule
    if medication_schedule:
        st.subheader("⏰ Jadwal Pengingat Obat")
        st.success("✅ Jadwal pengingat obat telah dibuat berdasarkan kondisi Anda")
        
        # Show schedule in an expandable section
        with st.expander("Lihat Jadwal", expanded=True):
            # Medicine times
            st.write("**Waktu Minum Obat:**")
            for time_entry in medication_schedule.get("medicine_times", []):
                st.info(f"• **{time_entry['time']}** - {time_entry['message']}")
            
            # Meal times
            st.write("**Waktu Makan:**")
            for time_entry in medication_schedule.get("meal_times", []):
                st.success(f"• **{time_entry['time']}** - {time_entry['message']}")
        
        # Button to go to reminders page
        if st.button("⏰ Kelola Jadwal Pengingat"):
            st.session_state.page = 'reminders'
            st.rerun()
    
    # Button to return to main page
    if st.button("🏠 Kembali ke Halaman Utama"):
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
                # Show medication stats with the new variables
                if 'jumlah_obat_saat_ini' in filtered_df.columns:
                    latest_row = filtered_df.iloc[-1]
                    jumlah_awal = latest_row.get('jumlah_obat_awal', 0)
                    obat_diminum = latest_row.get('jumlah_obat_diminum', 0)
                    obat_saat_ini = latest_row.get('jumlah_obat_saat_ini', 0)
                    
                    # Display medication information with custom orange color
                    st.markdown(f"""
                    <div style="padding:10px; border-radius:5px; border-left:3px solid #e98b1f; background-color:rgba(233, 139, 31, 0.1);">
                      <p style="color:#e98b1f; font-weight:bold; margin-bottom:10px;">📊 Informasi Obat:</p>
                      <p style="color:#e98b1f; margin-left:15px;">• Jumlah obat awal: {jumlah_awal}</p>
                      <p style="color:#e98b1f; margin-left:15px;">• Jumlah obat diminum: {obat_diminum}</p>
                      <p style="color:#e98b1f; margin-left:15px;">• Jumlah obat saat ini: {obat_saat_ini}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Prepare display dataframe - remove tracking columns
                display_columns = [col for col in filtered_df.columns if col not in 
                                  ['jumlah_obat_awal', 'jumlah_obat_diminum']]
                
                display_df = filtered_df[display_columns].copy()
                # Rename column for display
                if 'jumlah_obat_saat_ini' in display_df.columns:
                    display_df = display_df.rename(columns={'jumlah_obat_saat_ini': 'sisa_obat'})
                
                # Apply styling directly to the DataFrame
                # First sort the DataFrame
                # Replace the current styling code with this enhanced version in both places:

                # First sort the DataFrame
                display_df = display_df.sort_values(by="timestamp", ascending=False)

                # Then apply comprehensive styling for ALL table elements
                display_df = display_df.style.set_properties(**{
                    'background-color': '#fef9e1',
                    'color': '#2b2e2d',
                    'border': '1px solid #e98b1f'
                }).set_table_styles([
                    # Style for header cells
                    {'selector': 'th', 
                    'props': [('background-color', '#fef9e1'), 
                            ('color', '#2b2e2d'),
                            ('font-weight', 'bold'),
                            ('border', '1px solid #e98b1f')]},
                    # Style for index cells
                    {'selector': 'th.row_heading',
                    'props': [('background-color', '#fef9e1'),
                            ('color', '#2b2e2d'),
                            ('border', '1px solid #e98b1f')]},
                    # Style for the header index cell (top-left cell)
                    {'selector': 'th.col_heading.level0.index_name',
                    'props': [('background-color', '#fef9e1'),
                            ('color', '#2b2e2d'),
                            ('border', '1px solid #e98b1f')]}
                ])

                # Finally display it
                st.dataframe(display_df, use_container_width=True)
        else:
            # If last_updated is not available, display all data
            # Show medication stats with the new variables
            if 'jumlah_obat_saat_ini' in df.columns:
                latest_row = df.iloc[-1]
                jumlah_awal = latest_row.get('jumlah_obat_awal', 0)
                obat_diminum = latest_row.get('jumlah_obat_diminum', 0)
                obat_saat_ini = latest_row.get('jumlah_obat_saat_ini', 0)
                
                # Display medication information with custom orange color
                st.markdown(f"""
                <div style="padding:10px; border-radius:5px; border-left:3px solid #e98b1f; background-color:rgba(233, 139, 31, 0.1);">
                  <p style="color:#e98b1f; font-weight:bold; margin-bottom:10px;">📊 Informasi Obat:</p>
                  <p style="color:#e98b1f; margin-left:15px;">• Jumlah obat awal: {jumlah_awal}</p>
                  <p style="color:#e98b1f; margin-left:15px;">• Jumlah obat diminum: {obat_diminum}</p>
                  <p style="color:#e98b1f; margin-left:15px;">• Jumlah obat saat ini: {obat_saat_ini}</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Prepare display dataframe - remove tracking columns
            display_columns = [col for col in df.columns if col not in 
                              ['jumlah_obat_awal', 'jumlah_obat_diminum']]
            
            display_df = df[display_columns].copy()
            # Rename column for display
            if 'jumlah_obat_saat_ini' in display_df.columns:
                display_df = display_df.rename(columns={'jumlah_obat_saat_ini': 'sisa_obat'})
            
            # Apply styling directly to the DataFrame
            display_df = display_df.style.set_properties(**{
                'background-color': '#fef9e1',
                'color': '#2b2e2d',
                'border': '1px solid #e98b1f'
            })
            
            st.dataframe(display_df.sort_values(by="timestamp", ascending=False), use_container_width=True)
    else:
        st.info("Tidak ada data sensor yang tersedia.")

def generate_and_save_medicine_schedule(medical_history, box_cfg):
    """Generate and save medicine schedule automatically"""
    # Pastikan ada data yang cukup
    if not box_cfg or not medical_history:
        return None
    
    medication_name = box_cfg.get("medication_name", "")
    dosage_rules = box_cfg.get("dosage_rules", "")
    catatan_apoteker = box_cfg.get("catatan_apoteker", "")
    box_id = st.session_state.box_id
    
    if not medication_name or not dosage_rules or not box_id:
        return None
    
    # Buat koleksi baru jika belum ada
    if "reminder_collection" not in globals():
        global reminder_collection
        reminder_collection = db["MedicineReminders"]
    
    try:
        # Add pharmacist notes to prompt if available
        pharmacist_notes = ""
        if catatan_apoteker and catatan_apoteker.strip():
            pharmacist_notes = f"\nCatatan dari Apoteker: {catatan_apoteker}"
        
        # Gunakan AI untuk membuat jadwal
        prompt = f"""
        Sebagai ahli farmasi, analisis informasi berikut dan buat jadwal optimal:
        
        Riwayat medis: {medical_history}
        Nama obat: {medication_name}
        Aturan minum: {dosage_rules}{pharmacist_notes}
        
        Buat jadwal dalam format JSON dengan struktur berikut:
        {{
            "medicine_times": [
                {{"time": "05.00", "message": "Minum {medication_name} setelah sarapan"}},
                {{"time": "15:00", "message": "Minum {medication_name} setelah makan siang"}},
                {{"time": "20:00", "message": "Minum {medication_name} setelah makan malam"}}
            ],
            "meal_times": [
                {{"time": "04:30", "message": "Sarapan pagi"}},
                {{"time": "14:00", "message": "Makan siang"}},
                {{"time": "19:00", "message": "Makan malam"}}
            ],
            "explanation": "Penjelasan singkat tentang jadwal ini"
        }}
        
        Waktu harus dalam format 24 jam. Jadwal harus sesuai dengan aturan dosis dan kondisi medis pasien.
        Jika ada catatan khusus dari apoteker, prioritaskan informasi tersebut dalam pembuatan jadwal.
        """
        
        response = model.generate_content(prompt)
        
        # Ekstrak JSON dari respons
        import re
        import json
        
        # Cari blok JSON dalam respons
        try:
            # Coba parse langsung jika responnya hanya JSON
            schedule_data = json.loads(response.text)
        except:
            # Jika gagal, coba ekstrak blok JSON menggunakan regex
            json_match = re.search(r'```json\s*(.*?)\s*```', response.text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Coba ambil semua yang ada di dalam kurung kurawal
                json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    return None
                    
            try:
                schedule_data = json.loads(json_str)
            except:
                return None
        
        # Tambahkan metadata
        schedule_data["box_id"] = box_id
        schedule_data["updated_at"] = datetime.now(pytz.timezone("Asia/Jakarta"))
        schedule_data["is_active"] = True
        schedule_data["medical_history"] = medical_history
        
        # Update existing schedule or create new one if it doesn't exist
        result = reminder_collection.update_one(
            {"box_id": box_id},
            {"$set": schedule_data},
            upsert=True
        )
        
        # Log keberhasilan
        if result.upserted_id:
            print(f"✅ Jadwal baru dibuat dengan ID: {result.upserted_id}")
        else:
            print(f"✅ Jadwal diperbarui untuk Box ID: {box_id}")
        
        # Fetch the updated document to return
        updated_schedule = reminder_collection.find_one({"box_id": box_id})
        return updated_schedule
    
    except Exception as e:
        print(f"❌ Error saat memperbarui jadwal: {str(e)}")
        return None

def generate_and_save_medicine_schedule_from_config(medical_history, box_cfg):
    """Generate and save medicine schedule from configuration data"""
    # Pastikan ada data yang cukup
    if not box_cfg:
        return None
    
    medication_name = box_cfg.get("medication_name", "")
    dosage_rules = box_cfg.get("dosage_rules", "")
    condition = box_cfg.get("nama_penyakit", "")
    usia = box_cfg.get("usia", "")
    jenis_kelamin = box_cfg.get("jenis_kelamin", "")
    riwayat_alergi = box_cfg.get("riwayat_alergi", "")
    catatan_apoteker = box_cfg.get("catatan_apoteker", "")
    box_id = st.session_state.box_id
    
    if not medication_name or not dosage_rules or not box_id:
        return None
    
    # Buat koleksi baru jika belum ada
    if "reminder_collection" not in globals():
        global reminder_collection
        reminder_collection = db["MedicineReminders"]
    
    try:
        # Add pharmacist notes to prompt if available
        pharmacist_notes = ""
        if catatan_apoteker and catatan_apoteker.strip():
            pharmacist_notes = f"\nCatatan dari Apoteker: {catatan_apoteker}"
        
        # Gunakan AI untuk membuat jadwal
        prompt = f"""
        Sebagai ahli farmasi, buat jadwal pengingat obat berdasarkan informasi berikut:
        
        Nama obat: {medication_name}
        Aturan minum: {dosage_rules}
        Penyakit/Kondisi: {condition}
        Usia: {usia} tahun
        Jenis Kelamin: {jenis_kelamin}
        Riwayat Alergi: {riwayat_alergi}{pharmacist_notes}
        Informasi medis tambahan: {medical_history}
        
        Buat jadwal dalam format JSON dengan struktur berikut:
        {{
            "medicine_times": [
                {{"time": "08:00", "message": "Minum {medication_name} setelah sarapan"}},
                {{"time": "14:00", "message": "Minum {medication_name} setelah makan siang"}},
                {{"time": "20:00", "message": "Minum {medication_name} setelah makan malam"}}
            ],
            "meal_times": [
                {{"time": "07:30", "message": "Sarapan pagi"}},
                {{"time": "13:00", "message": "Makan siang"}},
                {{"time": "19:00", "message": "Makan malam"}}
            ],
            "explanation": "Penjelasan tentang jadwal pengobatan ini dan bagaimana jadwal ini dibuat sesuai dengan kondisi pasien."
        }}
        
        Jadwal harus mengikuti aturan dosis dan sesuai dengan kondisi medis pasien.
        Jika ada catatan khusus dari apoteker, pertimbangkan dengan serius dalam membuat jadwal.
        Berikan penjelasan yang informatif tentang jadwal dan hubungannya dengan kondisi kesehatan.
        Hanya berikan output dalam format JSON tanpa kode atau penjelasan tambahan di luar JSON.
        """
        
        response = model.generate_content(prompt)
        
        # Ekstrak JSON dari respons
        import re
        import json
        
        # Coba parse JSON dari respons
        try:
            # Coba parse langsung jika responnya hanya JSON
            schedule_data = json.loads(response.text)
        except:
            # Jika gagal, coba ekstrak blok JSON menggunakan regex
            json_match = re.search(r'```json\s*(.*?)\s*```', response.text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Coba ambil semua yang ada di dalam kurung kurawal
                json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    # Fallback jika semua metode ekstraksi gagal
                    return create_fallback_schedule(medication_name)
                    
            try:
                schedule_data = json.loads(json_str)
            except:
                # Fallback jika parsing JSON gagal
                return create_fallback_schedule(medication_name)
        
        # Tambahkan metadata
        schedule_data["box_id"] = box_id
        schedule_data["updated_at"] = datetime.now(pytz.timezone("Asia/Jakarta"))
        schedule_data["is_active"] = True
        schedule_data["medical_history"] = medical_history
        
        # Update existing schedule or create new one if it doesn't exist
        result = reminder_collection.update_one(
            {"box_id": box_id},
            {"$set": schedule_data},
            upsert=True
        )
        
        # Fetch the updated document to return
        updated_schedule = reminder_collection.find_one({"box_id": box_id})
        return updated_schedule
    
    except Exception as e:
        print(f"❌ Error saat memperbarui jadwal: {str(e)}")
        return create_fallback_schedule(medication_name)


def create_fallback_schedule(medication_name):
    """Create a simple fallback schedule if AI generation fails"""
    box_id = st.session_state.box_id
    
    # Create fallback schedule data
    fallback_data = {
        "medicine_times": [
            {"time": "08:00", "message": f"Minum {medication_name} setelah sarapan"},
            {"time": "12:00", "message": f"Minum {medication_name} setelah makan siang"},
            {"time": "20:00", "message": f"Minum {medication_name} setelah makan malam"}
        ],
        "meal_times": [
            {"time": "07:30", "message": "Sarapan pagi"},
            {"time": "11:30", "message": "Makan siang"},
            {"time": "19:00", "message": "Makan malam"}
        ],
        "explanation": "Jadwal pengingat standar untuk tiga kali minum obat sehari setelah makan.",
        "box_id": box_id,
        "updated_at": datetime.now(pytz.timezone("Asia/Jakarta")),
        "is_active": True,
        "medical_history": ""
    }
    
    # Update database with fallback schedule
    if "reminder_collection" in globals():
        try:
            reminder_collection.update_one(
                {"box_id": box_id},
                {"$set": fallback_data},
                upsert=True
            )
        except Exception as e:
            print(f"❌ Error saat menyimpan jadwal fallback: {str(e)}")
    
    return fallback_data

# ===========================
# SIDEBAR NAVIGATION
# ===========================
# Only show sidebar when not on login/config pages
if st.session_state.page not in ['login', 'config', 'confirm_config']:
    st.sidebar.title("🔀 Menu")
    if st.session_state.box_id:  # Only show navigation when logged in
        menu = st.sidebar.radio("Pilih Halaman:", 
                              ["🩺 Pemeriksaan Kesehatan", "⏰ Pengingat Obat", "📚 Riwayat Sensor"])
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
    display_header_with_logo()
    login_page()
elif st.session_state.page == 'confirm_config':
    display_header_with_logo()
    confirm_config_page()
elif st.session_state.page == 'config':
    display_header_with_logo()
    config_page()
else:
    # Navigation based on sidebar selection when logged in
    if st.session_state.box_id:
        # Display main title after login
        # Display header with logo
        display_header_with_logo()
        
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
            elif st.session_state.page == 'reminders':  # New route for reminders from results
                reminder_page()
        elif menu == "⏰ Pengingat Obat":
            reminder_page()
        elif menu == "📚 Riwayat Sensor":
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
