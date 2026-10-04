"""Optional model adapter. Add a trained CPU-compatible model here when available."""
import cv2
import numpy as np

class TrainedModel:
    def __init__(self, model_path=None):
        self.available = False
        self.model = None
        if model_path:
            try:
                import onnxruntime as ort
                self.model = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
                self.available = True
            except Exception:
                pass

    def predict(self, image):
        if not self.available:
            return None
        try:
            metadata = self.model.get_inputs()[0]
            shape = metadata.shape
            height = shape[2] if isinstance(shape[2], int) else 224
            width = shape[3] if isinstance(shape[3], int) else 224
            rgb = cv2.cvtColor(cv2.resize(image, (width, height)), cv2.COLOR_BGR2RGB)
            tensor = (rgb.astype(np.float32) / 255.0).transpose(2, 0, 1)[None, ...]
            scores = np.asarray(self.model.run(None, {metadata.name: tensor})[0]).reshape(-1)
            if len(scores) < 4 or not np.isfinite(scores[:4]).all():
                return None
            if np.any(scores[:4] < 0) or not np.isclose(scores[:4].sum(), 1, atol=.02):
                scores = np.exp(scores[:4] - np.max(scores[:4]))
                scores /= scores.sum()
            labels = ["Crack", "Porosity", "Incomplete Fusion", "No Defect"]
            index = int(np.argmax(scores[:4]))
            h, w = image.shape[:2]
            return labels[index], float(scores[index]), [int(w*.12), int(h*.22), int(w*.76), int(h*.56)]
        except Exception:
            # Unknown model tensor layouts fall back cleanly to the demo detector.
            return None
