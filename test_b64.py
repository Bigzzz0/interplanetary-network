import cv2
import numpy as np
import base64

frame = np.zeros((480, 640, 3), dtype=np.uint8)
cv2.circle(frame, (320, 240), 50, (0, 255, 255), -1)

encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 85]
_, encoded = cv2.imencode('.jpg', frame, encode_param)
b64 = base64.b64encode(encoded.tobytes()).decode('utf-8')
print(b64[:100])
