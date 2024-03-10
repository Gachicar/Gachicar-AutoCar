import threading
from socket import *
from select import *
import time
from pop import Pilot


"""
    라인트래킹 + 객체인식 + 장애물 회피
"""

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

"""
    RC카 서버와 소켓 연결
"""

# RC카 서버의 IP 주소와 포트 번호
host = ''  # 예: '192.168.0.100'
port = 9851  # 예: 8080

block = 0
check = 0

def handle_client(client_sock):
    block = 0
    check = 0
    
    def drive(value, value2):   # value는 라인 트래킹 value값, value2는 장애물 회피 value값
        print("----------drive: 차량 주행 코드----------")
        global block
        ac.forward()
        steer = value['x']
        steer * 1.55
        
        # 라인트랙킹을 위한 좌우 조정 (value를 사용)
        if steer > 1:
            steer = 1
        elif steer < -1:
            steer = -1
        
        ac.steering = steer * 1.5
        block = 0   # 장애물 미감지
        
        # 장애물 인식 후 후진하게 허는 코드(value2를 사용)
        if value2 >= 0.5:    # 0.5 초과 시 후진
            block = 2   # 장애물 감지
            ac.backward()

    def cardrive():
        print("----------cardrive: 차량 주행----------")
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
        
    def send(sock):
        global check, block
        while True:
            if check == 1 and block == 2: #장애물
                print("장애물 감지")  
                sendData = 6
                sock.send(sendData.to_bytes(4, byteorder="little"))
            elif check == 1 and block == 0:
                sendData = 7
                sock.send(sendData.to_bytes(4, byteorder="little"))

    def receive(sock):
        global check
        while True:
            data = sock.recv(1024)
            checkdata = data.decode("utf-8")
            print(checkdata)
            print(checkdata[:-1])
            if checkdata[:-1] == "시작":
                check = 1
                print(checkdata[:-1])
                
            elif checkdata[:-1] == "종료":
                check = -1
                print(checkdata[:-1])
                break
            elif checkdata[:-1] == "정지":
                print("정지합니다.")
                Car.setSpeed(0)
                check = 0
                print(checkdata[:-1])
            elif int.from_bytes(data, byteorder='big') != 0:
                speed = int(checkdata[:-1])
                Car.setSpeed(speed)
                print("속도", speed)

    sender = threading.Thread(target=send, args=(client_sock,))
    receiver = threading.Thread(target=receive, args=(client_sock,))
    driver = threading.Thread(target=cardrive)

    sender.start()
    receiver.start()

    cnt = 0
    while True:
        if check == 1 and cnt == 0:
            print("차량 주행 시작")
            driver.start()
            cnt = 1
        if check == -1:
            print("-----------------정지-----------------")
            cnt = 0
            break
        
    # 클라이언트 소켓이 닫히면 해당 IP와의 소켓 연결이 정상적으로 해제됨을 알림
    print("연결이 종료되었습니다:", client_sock.getpeername())
    client_sock.close()

def accept_clients(server_sock):
    while True:
        client_sock, addr = server_sock.accept()
        print(addr, "와 연결완료")
        threading.Thread(target=handle_client, args=(client_sock,)).start()

try:
    server_sock = socket(AF_INET, SOCK_STREAM)
    server_sock.bind((host, port))
    server_sock.listen(10)
    print("연결을 기다리는 중")

    # 클라이언트 연결을 받아들이고 처리하는 함수를 별도의 스레드로 실행
    threading.Thread(target=accept_clients, args=(server_sock,)).start()

    # 메인 스레드가 종료되지 않도록 무한 루프 유지
    while True:
        pass

except Exception as e:
    print(e)
    print("연결 오류")

finally:
    if 'server_sock' in locals():
        server_sock.close()
        