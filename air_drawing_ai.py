import cv2
import mediapipe as mp
import numpy as np
import pyttsx3
import time

# ==============================
# VOICE
# ==============================

engine = pyttsx3.init()
engine.setProperty('rate', 150)

def speak(text):
    engine.say(text)
    engine.runAndWait()

# ==============================
# LOAD MNIST DATA USING OPENCV
# ==============================

digits = cv2.imread("digits.png", 0)

if digits is None:
    print("Download digits.png from OpenCV samples and place in project folder.")
    exit()

cells = [np.hsplit(row,100) for row in np.vsplit(digits,50)]
x = np.array(cells)
train = x.reshape(-1,400).astype(np.float32)

k = np.arange(10)
train_labels = np.repeat(k,500)[:,np.newaxis]

knn = cv2.ml.KNearest_create()
knn.train(train, cv2.ml.ROW_SAMPLE, train_labels)

# ==============================
# MEDIAPIPE
# ==============================

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.7,
                       min_tracking_confidence=0.7)
mp_draw = mp.solutions.drawing_utils

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

canvas = np.zeros((480,640,3), dtype=np.uint8)
prev_x, prev_y = 0,0

expression = ""
history = []
result_timer = 0
animated_result = ""

# ==============================
# HELPERS
# ==============================

def finger_up(hand_landmarks, tip, pip):
    return hand_landmarks.landmark[tip].y < hand_landmarks.landmark[pip].y

def predict_digit(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    small = cv2.resize(gray,(20,20))
    sample = small.reshape(-1,400).astype(np.float32)
    ret, result, neighbours, dist = knn.findNearest(sample, k=5)
    return str(int(result[0][0]))

def solve_expression(expr):
    try:
        expr = expr.replace("×","*").replace("÷","/")
        return str(eval(expr))
    except:
        return "Error"

# ==============================
# MAIN LOOP
# ==============================

while True:
    success, frame = cap.read()
    if not success:
        break

    frame = cv2.flip(frame,1)
    frame = cv2.resize(frame,(640,480))

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(rgb)

    if result.multi_hand_landmarks:
        for hand_landmarks in result.multi_hand_landmarks:

            mp_draw.draw_landmarks(frame,
                                   hand_landmarks,
                                   mp_hands.HAND_CONNECTIONS)

            h,w,_ = frame.shape

            index_up = finger_up(hand_landmarks,8,6)
            middle_up = finger_up(hand_landmarks,12,10)
            ring_up = finger_up(hand_landmarks,16,14)
            thumb_up = finger_up(hand_landmarks,4,2)

            x = int(hand_landmarks.landmark[8].x * w)
            y = int(hand_landmarks.landmark[8].y * h)

            # DRAW
            if index_up and not middle_up:
                if prev_x==0 and prev_y==0:
                    prev_x,prev_y=x,y
                cv2.line(canvas,(prev_x,prev_y),(x,y),(255,255,255),8)
                prev_x,prev_y=x,y
            else:
                prev_x,prev_y=0,0

            # OPERATORS
            if index_up and middle_up and not ring_up:
                expression += "+"
                time.sleep(0.5)

            if index_up and middle_up and ring_up:
                expression += "×"
                time.sleep(0.5)

            if middle_up and ring_up and not index_up:
                expression += "-"
                time.sleep(0.5)

            if ring_up and not index_up and not middle_up:
                expression += "÷"
                time.sleep(0.5)

            # SAVE DIGIT
            if thumb_up:
                digit = predict_digit(canvas)
                expression += digit
                canvas = np.zeros((480,640,3),dtype=np.uint8)
                time.sleep(0.5)

    combined = cv2.add(frame,canvas)

    cv2.putText(combined,"Expression: "+expression,
                (10,450),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,(0,255,0),2)

    if len(expression)>=3:
        result_val = solve_expression(expression)
        full = expression+" = "+result_val
        speak(full)
        history.append(full)
        animated_result = full
        result_timer = time.time()
        expression=""

    for i,item in enumerate(history[-5:]):
        cv2.putText(combined,item,
                    (10,40+i*30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,(0,255,255),2)

    if animated_result:
        if time.time()-result_timer<3:
            cv2.putText(combined,animated_result,
                        (120,200),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1.5,(0,0,255),4)

    cv2.imshow("air_drawing_ai",combined)

    if cv2.waitKey(1)&0xFF==ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
