import asyncio
import threading
from socket import *
import time
from pop import Pilot

"""_summary_
    최종 코드 --> '코루틴 + 스레드' 혼합 사용 방식으로 변경한 버전 (2024.09.13)
    - 스레드를 활용한 CPU 바운드 작업: 라인트래킹 + 장애물 회피 + 객체 인식
    - 소켓 통신으로 제어
    - 목적지를 구체적으로 설정하여 이동 -> 설정된 객체 인식 시 정지 후 도착 알림
    - 장애물 감지 시 후진 및 알림
    
    [변경 내용]
    - 비동기 소켓 통신: 소켓 통신 부분을 async/await 방식의 코루틴으로 처리하여 비동기 작업 처리 -> 대기시간 감소 및 자원 효율성 증대
"""

# 카메라와 자율 주행 객체 초기화
cam = Pilot.Camera(width=300, height=300)
ac = Pilot.AutoCar()
OF = Pilot.Object_Follow(cam)
LF = Pilot.Track_Follow(camera=cam)
CA = Pilot.Collision_Avoid(cam)

# 모델 로드
LF.load_model("track_follow_model.pth")
OF.load_model()
CA.load_model("collision_final.pth")

# 기본 설정
steering_correction = 0.05
ac.setSpeed(0)
host = ''
port = 9851
block = 0
check = 0
destination = None
arrived = None

dest = {1: '집', 2: '회사', 3: '학교'}
dest_obj = {1: 'chair', 2: 'person', 3: 'umbrella'}

# 객체 감지, 라인 트래킹 스레드 전역 변수 선언
object_detection_thread = None
line_tracking_thread = None


# 주행
def drive(value, value2) -> None:
    global arrived, check, block

    if check == 1:
        if arrived is not None:
            while arrived:
                time.sleep(1)
        else:
            ac.setSpeed(10)
            ac.forward()
            steer = max(-1, min(1, value['x']))  # steer 값을 범위 내로 조정
            ac.steering = steer * 1.5

            block = 0
            if value2 >= 0.5:
                block = 1
                ac.backward()


# 객체 인식
def object_detection() -> None:
    global dest_obj, destination, arrived
    if destination is not None:
        index = dest_obj[destination]
        try:
            while True:
                v = OF.detect(index=index)
                if v is not None and v.get('size_rate', 0) >= 0.25:
                    print(f"{index} 감지", v.get('size_rate', 0))
                    arrived = destination
                    ac.stop()
                    break
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
    else:
        return None

# 라인 트래킹
def line_tracking() -> None:
    global destination, arrived, check
    try:
        while True:
            if destination is not None:
                value = LF.run()
                value2 = CA.run()
                drive(value, value2)
            else:
                print("목적지가 설정되지 않았습니다. 대기 중...")
                time.sleep(1)
    except KeyboardInterrupt:
        pass

# 주행 제어
# 스레드로 처리하여 CPU 바운드 작업이 병렬로 동작하도록
# 스레드 기반으로 처리한 이유는 CPU 작업을 별도의 스레드에서 실행해야 실시간 처리가 가능하기 때문
async def cardrive():
    print("----------Cardrive: Autonomous Driving----------")
    global check, arrived
    object_detection_thread = threading.Thread(target=object_detection)
    line_tracking_thread = threading.Thread(target=line_tracking)

    object_detection_thread.start()
    line_tracking_thread.start()

    # 스레드가 끝날 때까지 기다림
    while check != -1 and arrived is None:
        await asyncio.sleep(0.1)  # 0.1초마다 반복적으로 상태를 확인하며 대기

    if arrived is not None:
        ac.stop()

    object_detection_thread.join()
    line_tracking_thread.join()


# 소켓 통신 (비동기 방식으로 처리)
async def send(sock):
    global check, block, arrived, dest
    carStatus = {'종료': 0, '시작': 4, '정지': 5, '장애물 감지': 6, '정상 주행 중': 7}

    while True:
        if check == -1:
            sendData = carStatus["종료"]
        elif check == 0:
            print("정지 중")
            await asyncio.sleep(1)  # 코루틴을 사용하여 1초 대기
            sendData = carStatus["정지"]
        elif check == 1 and block == 1:
            print("장애물 감지")
            sendData = carStatus["장애물 감지"]
            sock.send(sendData.to_bytes(4, byteorder="big"))
            await asyncio.sleep(1)  # 코루틴을 사용하여 1초 대기
        elif arrived is not None:
            print(f"{dest[arrived]}로 이동 완료")
            sendData = arrived
            sock.send(sendData.to_bytes(4, byteorder="big"))
            check = -1
        elif check == 1 and block == 0:
            await asyncio.sleep(10) # 코루틴을 사용하여 10초 대기
            sendData = carStatus["정상 주행 중"]
            sock.send(sendData.to_bytes(4, byteorder="big"))


async def receive(sock):
    global check, destination
    while True:
        data = await sock.recv(1024)
        command = data.decode("utf-8").strip()
        print(command)
        if command == "시작":
            check = 1
            print("주행을 시작합니다.")
        elif command in dest.values():
            check = 1
            destination = 1 if command == '집' else (2 if command == '회사' else 3)
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


async def handle_client(client_sock):
    global check, destination, arrived
    try:
        check = 0
        send_task = asyncio.create_task(send(client_sock))  # 코루틴으로 소켓 데이터 전송
        receive_task = asyncio.create_task(receive(client_sock))  # 코루틴으로 소켓 데이터 수신
        drive_task = asyncio.create_task(cardrive())  # 자율 주행 작업

        await asyncio.gather(send_task, receive_task, drive_task)  # 비동기 작업을 동시에 실행
    finally:
        print("연결이 종료되었습니다:", client_sock.getpeername())
        client_sock.close()



async def accept_clients(server_sock):
    while True:
        client_sock, addr = await server_sock.accept()  # 비동기적으로 클라이언트 연결 수락
        print(addr, "와 연결완료")
        asyncio.create_task(handle_client(client_sock))


async def main():
    LF.show()
    server_sock = socket(AF_INET, SOCK_STREAM)
    server_sock.bind((host, port))
    server_sock.listen(10)
    print("연결을 기다리는 중")
    await accept_clients(server_sock)  # 클라이언트 연결을 비동기로 처리


# asyncio 이벤트 루프 실행
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except OSError as e:
        print(e)
        print("연결 오류")
    finally:
        print("서버 종료")
