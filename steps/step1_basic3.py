# 1.30미팅 후 라인 트랙킹 + 객체 인식 + 장애물 회피를 합친 코드 
# 2.22 수정 완료
from pop import Pilot

cam = Pilot.Camera(width=300, height=300)
ac = Pilot.AutoCar()
OF = Pilot.Object_Follow(cam)
LF = Pilot.Track_Follow(camera=cam)
CA = Pilot.Collision_Avoid(cam)

# 저장된 모델 3개를 불러오기
LF.load_model("line_tracer_0126_7.pth") # 라인트래킹 모델 로드
OF.load_model() # 객체 인식 모델 불러오기 ("ssd_mobilenet_v2_coco.engine"를 자동으로 불러옴)
CA.load_model("collision_final.pth") # 장애물 회피 모델 로드

LF.show()
OF.show()
CA.show()

LF.run()
CA.run()

ac.setSpeed(20)

def drive(value, value2): # value는 라인 트래킹 value값, value2는 장애물 회피 value값
    ac.forward()
    steer = value['x']
    steer * 1.55
    
    # 라인트랙킹을 위한 좌우 조정 (value를 사용)
    if steer > 1:
        steer = 1
    elif steer < -1:
        steer = -1
    
    ac.steering = steer * 1.5
    
    # 장애물 인식 후 후진하게 허는 코드(value2를 사용)
    if value2 >= 0.5:    # 0.5 초과 시 후진
        ac.backward()
        
try:
    while True:# 의자, 사람, 우산 객체를 탐지하는 루프 
        v = OF.detect(index='chair') 
        v2 = OF.detect(index='person')
        v3 = OF.detect(index='umbrella')
        if v or v2 or v3: # 의자, 사람, 우산 중 하나가 감지되면 멈춤.
            ac.stop()
        else:
            # 세개 중 하나도 해당되는 것이 없으면 라인트랙킹 진행.
            value = LF.run()
            value2 = CA.run()
            drive(value, value2)
except KeyboardInterrupt:
    ac.stop() # 키보드로 진행 멈춤