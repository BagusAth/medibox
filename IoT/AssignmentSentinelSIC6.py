from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime
import requests

app = Flask(__name__)
CORS(app)

# 🔹 MongoDB Connection
MONGO_URI = "mongodb+srv://bramantyo989:jkGjM7paFoethotj@cluster0.zgafu.mongodb.net/?appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client["SentinelSIC"]
collection = db["SensorSentinel"]
counter_collection = db["ObatCounter"]  # Koleksi untuk menghitung obat

# 🔹 Ubidots Configuration
UBIDOTS_TOKEN = "BBUS-uR3eDVaspOWqwibr9FTE1GRL4bSBTj"
UBIDOTS_DEVICE = "esp32-sic6-sentinel"
UBIDOTS_URL = f"https://industrial.api.ubidots.com/api/v1.6/devices/{UBIDOTS_DEVICE}"

# 🔹 Function to Send Data to Ubidots dengan logging lebih detail
def send_to_ubidots(data):
    headers = {
        "Content-Type": "application/json",
        "X-Auth-Token": UBIDOTS_TOKEN
    }

    # Format data sesuai dengan variabel di Ubidots
    formatted_data = {
        "temperature": data.get("temperature", 0),
        "humidity": data.get("humidity", 0),
        "motion": data.get("motion", 0),
        "light_duration": data.get("light_duration", 0),
        "ldr_value": data.get("ldr_value", 0),
        "jumlah_obat": data.get("jumlah_obat_diminum", 0)  # Pastikan nama variabel sama dengan di Ubidots
    }

    print("\n📤 Data yang akan dikirim ke Ubidots:")
    print(formatted_data)

    try:
        response = requests.post(UBIDOTS_URL, json=formatted_data, headers=headers)
        print("\n📩 Response dari Ubidots:")
        print(f"Status Code: {response.status_code}")
        print(f"Response Text: {response.text}")
        
        # Cek jika ada error dari Ubidots
        if response.status_code >= 400:
            print(f"❌ Error dari Ubidots: {response.json()}")
        else:
            print("✅ Data berhasil dikirim ke Ubidots")
            
        return response
    except Exception as e:
        print(f"❌ Gagal mengirim ke Ubidots: {str(e)}")
        if hasattr(e, 'response') and e.response:
            print(f"Error response: {e.response.text}")
        return None

# 🔹 Home Endpoint
@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Flask API is running!"})

# 🔹 Endpoint to Receive Data from ESP32
@app.route("/send_data", methods=["POST"])
def receive_data():
    try:
        data = request.json
        print("\n📥 Data diterima dari ESP32:")
        print(data)
        
        # Tambahkan timestamp
        data["timestamp"] = datetime.utcnow()

        # Simpan ke MongoDB
        collection.insert_one(data)
        print("✅ Data disimpan ke MongoDB")

        # Periksa jika obat diminum dan update counter
        if data.get("medicine_taken", False):
            print("💊 Obat diminum - update counter")
            # Gunakan upsert untuk memastikan dokumen counter selalu ada
            counter_collection.update_one(
                {}, 
                {"$inc": {"jumlah": 1}}, 
                upsert=True
            )

        # Ambil jumlah obat diminum terbaru
        count_doc = counter_collection.find_one({})
        jumlah_obat_diminum = count_doc["jumlah"] if count_doc else 0
        data["jumlah_obat_diminum"] = jumlah_obat_diminum
        print(f"🔢 Jumlah obat diminum: {jumlah_obat_diminum}")

        # Kirim ke Ubidots
        ubidots_response = send_to_ubidots(data)

        return jsonify({
            "message": "Data saved and sent to Ubidots!",
            "data": data,
            "ubidots_status": ubidots_response.status_code if ubidots_response else "failed"
        }), 201
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# 🔹 Endpoint untuk mendapatkan data terakhir
@app.route("/get_data", methods=["GET"])
def get_data():
    try:
        latest_data = collection.find().sort("timestamp", -1).limit(1)
        data_list = []
        for doc in latest_data:
            doc["_id"] = str(doc["_id"])
            data_list.append(doc)
        return jsonify(data_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🔹 Endpoint untuk mendapatkan jumlah obat diminum
@app.route("/jumlah_obat_diminum", methods=["GET"])
def get_medicine_count():
    try:
        count_doc = counter_collection.find_one({})
        count = count_doc["jumlah"] if count_doc else 0
        return jsonify({"jumlah_obat_diminum": count})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🔹 Endpoint untuk reset counter
@app.route("/reset_counter", methods=["POST"])
def reset_counter():
    try:
        counter_collection.update_one({}, {"$set": {"jumlah": 0}}, upsert=True)
        return jsonify({"message": "Counter has been reset."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🔹 Run the App
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)