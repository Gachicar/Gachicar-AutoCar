import threading
from socket import *
import time
from pop import Pilot

cam = Pilot.Camera(width=300, height=300)
ac = Pilot.AutoCar()
OF = Pilot.Object_Follow(cam)
LF = Pilot.Track_Follow(camera=cam)
CA = Pilot.Collision_Avoid(cam)

# 저장된 모델 3개를 불러오기
LF.load_model("line_tracer_0313_2.pth") # 라인트래킹 모델 로드
OF.load_model() # 객체 인식 모델 불러오기 ("ssd_mobilenet_v2_coco.engine"를 자동으로 불러옴)
CA.load_model("collision_final.pth") # 장애물 회피 모델 로드

steering_correction = 0.05
ac.setSpeed(0)


# RC카 서버의 IP 주소와 포트 번호
host = ''
port = 9851

block = 0
check = 0
destination = None
arrived = None

dest = {1: '집', 2: '회사', 3: '학교'}
dest_obj = {1: 'chair', 2: 'person', 3: 'umbrella'}

# 객체 감지 쓰레드와 라인 트래킹 쓰레드를 전역 변수로 선언
object_detection_thread = None
line_tracking_thread = None

def drive(value, value2):   # value는 라인 트래킹 value값, value2는 장애물 회피 value값
    global arrived, check, block

    if check == 1:  # 주행을 수행
        if arrived is not None:  # 목적지에 도착했을 때
            while arrived:  # 목적지에 도착한 상태에서 클라이언트가 다시 명령을 내지 않으면 대기
                time.sleep(1)
        else:
            ac.setSpeed(10)
            ac.forward()
            steer = value['x']

            # 라인트랙킹을 위한 좌우 조정 (value를 사용)
            if steer > 1:
                steer = 1
            elif steer < -1:
                steer = -1

            ac.steering = steer * 1.5

            block = 0
            # 장애물 인식 후 후진하게 하는 코드(value2를 사용)
            if value2 >= 0.5:    # 0.5 초과 시 후진
                block = 1
                ac.backward()
#             time.sleep(1)  # 수정

def object_detection():
    global dest_obj, destination, arrived

    if destination is not None:
        index = dest_obj[destination]

        try:
            while True:
                # 객체 감지를 수행하는 로직
                v = OF.detect(index=index)

                if v is not None: 
                    if v.get('size_rate', 0) >= 0.25:
                        print(index + " 감지", v.get('size_rate', 0))
                        arrived = destination
                        break   # 0407 추가

                # 객체 감지 주기 조정
                time.sleep(0.5)  # 예시로 0.5초로 설정

        except KeyboardInterrupt:
            pass
    else:
        return None


def line_tracking():
    global destination, arrived, check

    try:
        while True:
            if destination is not None:
                # 라인 트래킹을 수행하는 로직
                value = LF.run()
                value2 = CA.run()
                drive(value, value2)

            else:
                print("목적지가 설정되지 않았습니다. 대기 중...")
                time.sleep(1)

    except KeyboardInterrupt:
        pass

def cardrive():
    global arrived
    print("----------Cardrive: Autonomous Driving----------")
    try:
        while check != -1:  # check가 -1이 아닐 때만 실행
#             if check == 1:
            # 객체 감지 및 라인 트래킹을 동시에 수행하는 로직
            object_detection_thread = threading.Thread(target=object_detection)
            line_tracking_thread = threading.Thread(target=line_tracking)

            object_detection_thread.start()
            line_tracking_thread.start()

            object_detection_thread.join()  # 쓰레드가 종료될 때까지 기다립니다.
            line_tracking_thread.join()  # 쓰레드가 종료될 때까지 기다립니다.

            time.sleep(0.1)  # 예시로 0.1초에 한 번씩 주요 작업 수행
    except KeyboardInterrupt:
        pass
    finally:
        # 예외가 발생했을 때 쓰레드를 종료합니다.
        print("예외 발생: 쓰레드 종료")
        if object_detection_thread.is_alive():
            object_detection_thread.join()
        if line_tracking_thread.is_alive():
            line_tracking_thread.join()



def send(sock):
    global check, block, arrived, dest
    carStatus = {'종료': 0, '시작': 4, '정지': 5, '장애물 감지': 6, '정상 주행 중': 7}

    while True:
        if check == -1:
            sendData = carStatus["종료"]
        elif check == 0:
            print("정지 중")
            time.sleep(1)
            sendData = carStatus["정지"]
        elif check == 1 and block == 1:
            print("장애물 감지")
            sendData = carStatus["장애물 감지"]
            sock.send(sendData.to_bytes(4, byteorder="big"))
            time.sleep(1)
        elif arrived is not None:
            print(f"{dest[arrived]}로 이동 완료")
            sendData = arrived
            sock.send(sendData.to_bytes(4, byteorder="big"))
            check = -1
        elif check == 1 and block == 0:
            time.sleep(10)
            sendData = carStatus["정상 주행 중"]
            sock.send(sendData.to_bytes(4, byteorder="big"))

def receive(sock):
    global check, destination
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
    global check, destination, arrived
    try:
        check = 0    # 초기화
        sender = threading.Thread(target=send, args=(client_sock,))
        receiver = threading.Thread(target=receive, args=(client_sock,))
        driver = threading.Thread(target=cardrive)

        sender.start()
        receiver.start()

        cnt = 0
        while True:
            time.sleep(1)
            if cnt == 0 and check == 1 and destination:
                print("차량 주행 시작")
                driver.start()
                cnt = 1
            if check == 0:
                ac.stop()
                arrived = None
                print("-----------------정지-----------------")
                cnt = 0
            if check == -1:
                ac.stop()  
                arrived = None
                print("-----------------종료-----------------")
                cnt = 0
                break
    finally:
        # 클라이언트 소켓이 닫히면 해당 IP와의 소켓 연결이 정상적으로 해제됨을 알림
        print("연결이 종료되었습니다:", client_sock.getpeername())
        client_sock.close()

def accept_clients(server_sock):
    while True:
        client_sock, addr = server_sock.accept()
        print(addr, "와 연결완료")
        if client_sock is not None:
            threading.Thread(target=handle_client, args=(client_sock,)).start()


try:
    LF.show()
    server_sock = socket(AF_INET, SOCK_STREAM)
    server_sock.bind((host, port))
    server_sock.listen(10)
    print("연결을 기다리는 중")
    accept_clients(server_sock)

except OSError as e:
    print(e)
    print("연결 오류")
    server_sock.close()
except Exception as e:
    print(e)
finally:
    server_sock.close()