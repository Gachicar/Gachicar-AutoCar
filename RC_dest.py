import threading
from socket import *
import time
from pop import Pilot

# 라인트래킹 + 객체인식 + 장애물 회피 설정
cam = Pilot.Camera(width=300, height=300)
ac = Pilot.AutoCar()
OF = Pilot.Object_Follow(cam)
LF = Pilot.Track_Follow(camera=cam)
CA = Pilot.Collision_Avoid(cam)

# 저장된 모델 3개를 불러오기
LF.load_model("line_tracer_0126_7.pth")
OF.load_model()
CA.load_model("collision_final.pth")

LF.show()
OF.show()
CA.show()

LF.run()
CA.run()

ac.setSpeed(20)

# RC카 서버와 소켓 연결 설정
host = ''  # 서버의 IP 주소
port = 9851  # 포트 번호

block = 0
check = 0
destination = None
arrived = None
arrived_lock = threading.Lock()  # arrived 변수를 동기화하는 데 사용할 Lock 객체
dest = {1: '집', 2: '회사', 3: '학교'}

def drive(value, value2):
    global block
    ac.forward()
    steer = value['x'] * 1.55
    
    # 라인트래킹을 위한 좌우 조정
    if steer > 1:
        steer = 1
    elif steer < -1:
        steer = -1
    
    ac.steering = steer * 1.5
    block = 0
    
    # 장애물 인식 시 후진
    if value2 >= 0.5:
        block = 2
        ac.backward()

def cardrive():
    global check, destination, arrived
    print("----------cardrive: 차량 주행----------")
    try:
        while True:
            if destination == '집':
                v = OF.detect(index='chair')
                with arrived_lock:
                    arrived = 1
            elif destination == '회사':
                v = OF.detect(index='person')
                with arrived_lock:
                    arrived = 2
            elif destination == '학교':
                v = OF.detect(index='umbrella')
                with arrived_lock:
                    arrived = 3
            else:
                v = False
                
            if v:
                ac.stop()
            else:
                value = LF.run()
                value2 = CA.run()
                drive(value, value2)
                
                if check == -1 or (destination is not None and arrived == destination):
                    print("-----------------주행 종료-----------------")
                    break
    except KeyboardInterrupt:
        ac.stop()

def send(sock):
    global check, block, arrived, dest
    while True:
        if check == 1 and block == 2:
            print("장애물 감지")  
            sendData = 6
            sock.send(sendData.to_bytes(4, byteorder="little"))
        elif check == 1 and block == 0:
            if arrived is not None:
                print(f"{dest[arrived]}로 이동 완료")
                sendData = arrived
                sock.send(sendData.to_bytes(4, byteorder="little"))
                check = -1
            else:
                sendData = 7
                sock.send(sendData.to_bytes(4, byteorder="little"))
                

def receive(sock):
    global check, destination, dest
    while True:
        data = sock.recv(1024)
        command = data.decode("utf-8").strip()
        print(command)
        if command == "시작":
            check = 1
            print("주행을 시작합니다.")
        elif command in dest.values():
            check = 1
            destination = 1 if command == '집' else (2 if command == '회사' else (3 if command == '학교' else None))
            print(f"{command}으로 이동합니다.")
        elif command == "종료":
            check = -1
            print("주행을 종료합니다.")
            break
        elif command == "정지":
            print("정지합니다.")
            ac.setSpeed(0)
            check = 0
        elif command.isdigit():
            speed = int(command)
            ac.setSpeed(speed)
            print("속도", speed)

def handle_client(client_sock):
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
            print("-----------------종료-----------------")
            cnt = 0
            break
        
    print("연결이 종료되었습니다:", client_sock.getpeername())
    client_sock.close()

def accept_clients(server_sock):
    while True:
        client_sock, addr = server_sock.accept()
        print(addr, "와 연결완료")
        threading.Thread(target=handle_client, args=(client_sock,)).start()


# 메인 코드
try:
    server_sock = socket(AF_INET, SOCK_STREAM)
    server_sock.bind((host, port))
    server_sock.listen(10)
    print("연결을 기다리는 중")

    threading.Thread(target=accept_clients, args=(server_sock,)).start()

    while True:
        pass

except Exception as e:
    print(e)
    print("연결 오류")

finally:
    if 'server_sock' in locals():
        server_sock.close()
