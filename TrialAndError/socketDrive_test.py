# RC카 서버의 IP 주소와 포트 번호
host = ''
port = 9851

block = 0
check = 0
destination = None
arrived = None
dest = {1: '집', 2: '회사', 3: '학교'}

def drive(LF_value, CA_value, OF_chair, OF_person):   # value는 라인 트래킹 value값, value2는 장애물 회피 value값
    global arrived, check
    
    if check == 1:  # 주행을 수행
        if OF_chair is not None:  # 목적지에 도착했을 때
            if OF_chair.get('size_rate', 0) >= 0.2:
                print("의자 감지", OF_chair.get('size_rate', 0))
                arrived = 1
        if OF_person is not None:
            if OF_person.get('size_rate', 0) >= 0.2:
                print("사람 감지", OF_person.get('size_rate', 0))
                arrived = 2
                
         # 목적지에 도착하지 않았을 때
        print("----------drive: 차량 주행 코드----------")
        ac.setSpeed(10)
        ac.forward()
        steer = LF_value['x']
        
        # 라인트랙킹을 위한 좌우 조정 (value를 사용)
        if steer > 1:
            steer = 1
        elif steer < -1:
            steer = -1
        
        ac.steering = steer * 1.5
        
        # 장애물 인식 후 후진하게 하는 코드(value2를 사용)
        if CA_value >= 0.5:    # 0.5 초과 시 후진
            ac.backward()


def cardrive():
    global CA, LF, OF, check, destination, arrived
    print("----------Cardrive: Autonomous Driving----------")
    while True:
        v1 = LF.run()
        v2 = CA.run()
        v3 = OF.detect(index='chair')
        v4 = OF.detect(index='person')
        drive(v1, v2, v3, v4)
        if check == -1 or arrived:
            ac.stop()
            print("-----------------주행 종료-----------------")
            break
                

def send(sock):
    global check, block, arrived, dest
    carStatus = {'종료': 0, '시작': 4, '정지': 5, '장애물 감지': 6, '정상 주행 중': 7}
    
    while True:
        if check == 0:
            print("정지 중")
            time.sleep(1)
            sendData = carStatus["정지"]
        elif check == 1 and block == 2:
            print("장애물 감지")
            time.sleep(3)
            sendData = carStatus["장애물 감지"]
            sock.send(sendData.to_bytes(4, byteorder="big"))
        elif check == 1 and block == 0:
            if arrived is not None:
                print(f"{dest[arrived]}로 이동 완료")
                sendData = arrived
                sock.send(sendData.to_bytes(4, byteorder="big"))
                arrived = None
                time.sleep(3)
                check = 0
            else:
                time.sleep(10)
                sendData = carStatus["정상 주행 중"]
                sock.send(sendData.to_bytes(4, byteorder="big"))

def receive(sock):
    global check
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
    try:
        sender = threading.Thread(target=send, args=(client_sock,))
        receiver = threading.Thread(target=receive, args=(client_sock,))
        driver = threading.Thread(target=cardrive)

        sender.start()
        receiver.start()

        cnt = 0
        while True:
            # time.sleep(1)
            if cnt == 0:
                print("차량 주행 시작")
                driver.start()
                cnt = 1
            # if check == -1:
            #     ac.stop()  # 수정: Car -> ac
            #     print("-----------------정지-----------------")
            #     cnt = 0
            #     break
    finally:
        # 클라이언트 소켓이 닫히면 해당 IP와의 소켓 연결이 정상적으로 해제됨을 알림
        print("연결이 종료되었습니다:", client_sock.getpeername())
        client_sock.close()

def accept_clients(server_sock):
    while True:
        client_sock, addr = server_sock.accept()
        print(addr, "와 연결완료")
        threading.Thread(target=handle_client, args=(client_sock,)).start()
