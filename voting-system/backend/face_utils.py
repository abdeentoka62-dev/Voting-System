import os
import cv2
import numpy as np
import base64
from deepface import DeepFace

FACE_MODEL = "ArcFace"
DETECTOR = "skip"
DISTANCE_METRIC = "cosine"
THRESHOLD = 0.40

FACES_DIR = os.path.join(os.path.dirname(__file__), "faces")
os.makedirs(FACES_DIR, exist_ok=True)

# Warm-up: pre-load model at startup to avoid delay on first request
def _warmup():
    try:
        print("[face_utils] Loading ArcFace model...")
        # Create a tiny blank image and run a dummy verify to force model load
        dummy = np.zeros((112, 112, 3), dtype=np.uint8)
        dummy_path = os.path.join(FACES_DIR, "_warmup.jpg")
        cv2.imwrite(dummy_path, dummy)
        try:
            DeepFace.represent(
                img_path=dummy_path,
                model_name=FACE_MODEL,
                detector_backend="skip",
                enforce_detection=False
            )
        except Exception:
            pass
        if os.path.exists(dummy_path):
            os.remove(dummy_path)
        print("[face_utils] ArcFace model loaded ✓")
    except Exception as e:
        print(f"[face_utils] Warmup failed (non-critical): {e}")

_warmup()


def save_face_from_base64(national_id: str, b64_image: str) -> str:
    img_data = base64.b64decode(b64_image.split(",")[-1])
    img_array = np.frombuffer(img_data, np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    temp_path = os.path.join(FACES_DIR, f"_temp_{national_id}.jpg")
    cv2.imwrite(temp_path, img)

    detected = False
    for detector in ["opencv", "ssd", "mtcnn"]:
        try:
            faces = DeepFace.extract_faces(
                img_path=temp_path,
                detector_backend=detector,
                enforce_detection=True
            )
            if faces:
                detected = True
                break
        except Exception as e:
            print(f"[face_utils] detector={detector} failed: {e}")
            continue

    if not detected:
        try:
            faces = DeepFace.extract_faces(
                img_path=temp_path,
                detector_backend="skip",
                enforce_detection=False
            )
            if faces:
                detected = True
                print("[face_utils] fallback skip detector used — face accepted")
        except Exception as e:
            print(f"[face_utils] fallback skip failed: {e}")

    if os.path.exists(temp_path):
        os.remove(temp_path)

    if not detected:
        raise ValueError("لم يتم اكتشاف وجه في الصورة. تأكد من الإضاءة الجيدة وأن وجهك واضح في الكاميرا.")

    path = os.path.join(FACES_DIR, f"{national_id}.jpg")
    cv2.imwrite(path, img)
    return path


def verify_face(national_id: str, b64_image: str) -> dict:
    stored_path = os.path.join(FACES_DIR, f"{national_id}.jpg")
    if not os.path.exists(stored_path):
        return {"verified": False, "distance": 1.0, "message": "لا توجد صورة مسجلة لهذا المستخدم"}

    img_data = base64.b64decode(b64_image.split(",")[-1])
    img_array = np.frombuffer(img_data, np.uint8)
    live_img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    temp_path = os.path.join(FACES_DIR, f"_temp_live_{national_id}.jpg")
    cv2.imwrite(temp_path, live_img)

    try:
        result = DeepFace.verify(
            img1_path=stored_path,
            img2_path=temp_path,
            model_name=FACE_MODEL,
            detector_backend=DETECTOR,
            distance_metric=DISTANCE_METRIC,
            enforce_detection=False,
            align=True
        )
        verified = result["verified"] and result["distance"] <= THRESHOLD
        return {
            "verified": verified,
            "distance": round(result["distance"], 4),
            "message": "تم التحقق بنجاح ✓" if verified else "فشل التحقق من الوجه ✗"
        }
    except Exception as e:
        return {"verified": False, "distance": 1.0, "message": f"خطأ في التحقق: {str(e)}"}
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
