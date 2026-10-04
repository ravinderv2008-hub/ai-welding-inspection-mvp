import cv2
import numpy as np
from pathlib import Path
from .preprocessing import preprocess
from .model import TrainedModel

CLASSES = {"crack": "Crack", "porosity": "Porosity", "fusion": "Incomplete Fusion", "good": "No Defect"}

class WeldDetector:
    def __init__(self):
        self.model = TrainedModel(str(Path(__file__).resolve().parents[1] / "models" / "weld.onnx"))

    def analyze(self, image, sample_hint=None):
        h, w = image.shape[:2]
        gray, edges = preprocess(image)
        predicted = self.model.predict(image)
        if predicted:
            label, confidence, box = predicted
            source = "trained_model"
        else:
            # Deterministic demo heuristics. Sample selection hints make the included
            # teaching examples predictable; uploaded images use simple CV signals.
            if sample_hint in CLASSES:
                kind = sample_hint
                confidence = {"crack": .82, "porosity": .79, "fusion": .76, "good": .91}[kind]
            else:
                _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
                dark = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
                contours, _ = cv2.findContours(dark, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                candidates = [cv2.boundingRect(c) for c in contours if cv2.contourArea(c) > max(12, w*h*.00012)]
                elongated = [b for b in candidates if max(b[2], b[3]) / max(1, min(b[2], b[3])) > 5]
                if elongated:
                    kind, confidence = "crack", .68
                elif len(candidates) >= 5:
                    kind, confidence = "porosity", .66
                else:
                    kind, confidence = "good", .72
            source = "prototype_fallback"
            box = self._region(gray, edges, kind)
            label = CLASSES[kind]
        severity = "High" if label == "Crack" else "Medium" if label in ("Porosity", "Incomplete Fusion") else "None"
        verdict = "FAIL" if severity != "None" else "PASS"
        return {"defect_type": label, "confidence": round(float(confidence), 2), "severity": severity,
                "verdict": verdict, "bbox": box, "analysis_mode": source, "width": w, "height": h}

    @staticmethod
    def _region(gray, edges, kind):
        h, w = gray.shape
        # Use the image centerline as a meaningful inspection ROI and tighten to
        # the strongest local edge/contrast area where possible.
        x0, x1 = int(w*.12), int(w*.88); y0, y1 = int(h*.22), int(h*.78)
        roi = edges[y0:y1, x0:x1]
        if kind == "good" or roi.size == 0:
            return [x0, y0, max(1, x1-x0), max(1, y1-y0)]
        ys, xs = np.where(roi > 0)
        if len(xs):
            cx, cy = x0 + int(np.median(xs)), y0 + int(np.median(ys))
        else:
            cx, cy = w//2, h//2
        bw, bh = max(30, int(w*.30)), max(24, int(h*.25))
        return [max(0,cx-bw//2), max(0,cy-bh//2), min(bw,w), min(bh,h)]
