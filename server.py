import  time, os, sys, json, webbrowser, ssl
from datetime import datetime, timezone
from flask import Flask, render_template, jsonify, Response, request
from flask_cors import CORS
from supabase import create_client
from dotenv import load_dotenv
from threading import Event, Timer

ssl._create_default_https_context = ssl._create_unverified_context

load_dotenv()
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

TABLE_NAME = "plates"
supabase = None

def get_supabase():
    global supabase
    if supabase is None:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return supabase


def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

app = Flask(
    __name__,
    template_folder=get_resource_path("templates"),
    static_folder=get_resource_path("static")
)

CORS(app)

plate_event = Event()
latest_plate = {"text": "-", "valid": False}

def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000")

def update_plate(text, valid):
    global latest_plate
    latest_plate = {"text": text, "valid": valid}
    print("Updated plate:", latest_plate)
    plate_event.set()

def format_plate(text):
    return f"{text[:-6]} {text[-6:-2]} {text[-2:]}"

@app.route("/")
def index():
    return render_template("display.html")

@app.route("/plate")
def plate():
    return jsonify(latest_plate)

@app.route("/api/plate", methods=["POST"])
def receive_plate():

    data = request.json
    plate = data.get("plate")

    if not plate:
        return jsonify({"error": "No plate"}), 400

    formatted_plate = format_plate(plate)
    now = datetime.now(timezone.utc).isoformat()

    try:
        db = get_supabase()

        res = db.table(TABLE_NAME)\
            .select("*")\
            .eq("plate_text", plate)\
            .eq("status", "IN")\
            .execute()

        if res.data:
            carPlate = res.data[0]

            time_in = datetime.fromisoformat(
                carPlate["time_in"].replace("Z", "+00:00")
            )

            time_diff = (
                datetime.now(timezone.utc) - time_in
            ).total_seconds()

            if time_diff <= 600:
                db.table(TABLE_NAME)\
                    .update({
                        "status": "OUT",
                        "time_out": now
                    })\
                    .eq("plate_text", plate)\
                    .eq("status", "IN")\
                    .execute()

                print("EXIT FREE:", plate)
                update_plate(formatted_plate, True)
                return jsonify({"status": "ok", "exit": "free"})

            if not carPlate["paid"]:
                print("NOT PAID:", plate)
                update_plate(formatted_plate, False)
                return jsonify({"error": "NOT PAID"}), 400

            db.table(TABLE_NAME)\
                .update({
                    "status": "OUT",
                    "time_out": now
                })\
                .eq("plate_text", plate)\
                .eq("status", "IN")\
                .execute()

            print("EXIT PAID:", plate)
            update_plate(formatted_plate, True)
            return jsonify({"status": "ok", "exit": "paid"})

        else:
            db.table(TABLE_NAME).insert({
                "plate_text": plate,
                "status": "IN",
                "paid": False,
                "time_in": now
            }).execute()

            print("ENTER:", plate)
            return jsonify({"status": "ok", "action": "enter"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/plate/stream")
def plate_stream():

    def event_stream():

        last_sent = {"text": None, "valid": None}

        while True:
            plate_event.wait()

            if latest_plate != last_sent:

                data = json.dumps(latest_plate)
                yield f"data: {data}\n\n"

                last_sent = latest_plate.copy()

            time.sleep(0.1)
            plate_event.clear()

    return Response(event_stream(), mimetype="text/event-stream")


def run_flask():
    Timer(2, open_browser).start()
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
        threaded=True,
        use_reloader=False
    )