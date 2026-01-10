import os, re, time, json, cv2
from threading import Thread
from collections import defaultdict
from queue import Queue
import easyocr
from supabase import create_client
from ultralytics import YOLO

CAMERA_SOURCE = 0
SUPABASE_URL = "https://sxkwiwzeemnqvjgctvva.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN4a3dpd3plZW1ucXZqZ2N0dnZhIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzAzNDU4OSwiZXhwIjoyMDc4NjEwNTg5fQ.j7yG8Xgmg2o4iw0NoiGhYEdCutdfzolHxX-2pOOuf6s"
TABLE_NAME = "plates"  
CONFIRM_FRAMES = 2  # Брой последователни кадри за потвърждение на номера
FRAME_SKIP = 4      # Пропускане на всеки N кадъра за оптимизация
QUEUE_MAX = 5       # Максимален брой кадри в опашката

DATASET_DIR = "dataset_auto"
IMAGES_DIR = os.path.join(DATASET_DIR, "images")
LABELS_DIR = os.path.join(DATASET_DIR, "labels")

# Регулярен израз за валиден български регистрационен номер
BG_PLATE_REGEX = re.compile(r'^[A-Z]{1,2}[0-9]{4}[A-Z]{2}$')

# Създаване на директории, ако не съществуват
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(LABELS_DIR, exist_ok=True)


frame_queue = Queue(maxsize=QUEUE_MAX)
seen_counts = defaultdict(int)
confirmed = set()

# Инициализация на EasyOCR (български език)
reader = easyocr.Reader(['bg'], gpu=False)

model = YOLO("iliev_licence_plate.pt")
model.fuse() 

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Функция за непрекъснато заснемане на кадри от камерата
def capture_frames():
    cap = cv2.VideoCapture(CAMERA_SOURCE)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    if not cap.isOpened(): return print("Cannot open camera")
    while True:
        ret, frame = cap.read()
        frame_queue.put(frame) if ret and not frame_queue.full() else time.sleep(0.05)

# Функция за почистване на текст (премахва дублирани символи и невалидни)
def clean_text(text):
    return re.sub(r'^(.)\1+|[^A-Z0-9]', lambda m: m.group(1) if m.group(1) else '', text.upper())

# OCR за разпознаване на номера от изображение
def ocr_plate(img):
    res = reader.readtext(
        cv2.cvtColor(img, cv2.COLOR_BGR2RGB),
        allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
        detail=0
    )
    if not res: return None
    text = clean_text(''.join(res))
    return text if 6 <= len(text) <= 9 else None  

# Проверка дали даден текст е валиден български номер
def is_valid_bg_plate(text): 
    return bool(BG_PLATE_REGEX.match(text))

# Функция за запис на потвърден номер в Supabase
def save_plate_db(text):
    try:
        supabase.table(TABLE_NAME).insert({"plate_text": text}).execute()
    except Exception as e:
        print("Supabase error:", e)

Thread(target=capture_frames, daemon=True).start()
print("Parking System Started. Press 'q' to quit.")

frame_index = 0
while True:
    if frame_queue.empty(): 
        time.sleep(0.01)
        continue

    frame = frame_queue.get()
    frame_index += 1

    # Пропускане на кадри за оптимизация
    if frame_index % FRAME_SKIP != 0: continue

    results = model(frame, conf=0.4, verbose=False)
    for box in results[0].boxes.xyxy:
        x1, y1, x2, y2 = map(int, box)
        plate_roi = frame[y1:y2, x1:x2]  
        text = ocr_plate(plate_roi)
        if not text: continue

        # Проверка на валидност и оцветяване на рамката
        valid = is_valid_bg_plate(text)
        color = (0,255,0) if valid else (0,0,255)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, text, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

        # Потвърждаване на номер след няколко последователни кадъра
        if valid:
            seen_counts[text] += 1
            if seen_counts[text] >= CONFIRM_FRAMES and text not in confirmed:
                confirmed.add(text)
                print("Confirmed Plate:", text)
                save_plate_db(text)

    # Показване на текущия кадър с рамки и текст
    cv2.imshow("Parking System", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"): break

cv2.destroyAllWindows()
print("Parking System Stopped.")
