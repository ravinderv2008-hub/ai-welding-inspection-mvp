import cv2
import numpy as np

def preprocess(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    denoised = cv2.GaussianBlur(gray, (5, 5), 0)
    normalized = cv2.normalize(denoised, None, 0, 255, cv2.NORM_MINMAX)
    edges = cv2.Canny(normalized, 45, 130)
    return normalized, edges
