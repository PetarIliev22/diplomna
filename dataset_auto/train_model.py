from ultralytics import YOLO
import shutil

dataset_yaml = "dataset_auto/plates.yaml"
output_model_name = "iliev_licence_plate.pt"

model = YOLO("yolov8n.pt")

model.train(
    data="dataset_auto/plates.yaml",
    epochs=60,
    imgsz=640,
    batch=4,
    augment=True,
    patience=0,     
    workers=2,
    name="iliev_licence_plate",
    project="runs/train"
)

shutil.copy(
    "runs/train/iliev_licence_plate/weights/best.pt",
    output_model_name
)

print(f"SAVED: {output_model_name}")
