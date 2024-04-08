from socket import *
import threading

"""
    시작/정지/종료 명령어를 받아서 주행을 제어하는 코드
    - 소켓 통신으로 주행 제어
    - 시작 명령어를 받으면 주행 시작
    - 정지 명령어를 받으면 주행 정지
    - 종료 명령어를 받으면 소켓 연결 종료
"""

host = 'localhost'
port = 9851

def handle_client(client_sock):
    block = 0
    check = 0

    def drive(value, value2):
        print("----------drive: 차량 주행 코드----------")

    def cardrive():
        print("----------cardrive: 차량 주행----------")

    def send(sock):
        nonlocal check, block
        while True:
            if check == 1 and block == 2: #장애물
                sendData = 6
                sock.send(sendData.to_bytes(4, byteorder="little"))
            elif check == 1 and block == 0:
                sendData = 7
                sock.send(sendData.to_bytes(4, byteorder="little"))

    def receive(sock):
        nonlocal check
        while True:
            data = sock.recv(1024)
            checkdata = data.decode("utf-8")
            if checkdata[:-1] == "시작":
                check = 1
            elif checkdata[:-1] == "종료":
                check = -1
                break
            elif checkdata[:-1] == "정지":
                check = 0
            elif int.from_bytes(data, byteorder='big') != 0:
                speed = int(checkdata[2:])

    sender = threading.Thread(target=send, args=(client_sock,))
    receiver = threading.Thread(target=receive, args=(client_sock,))
    driver = threading.Thread(target=cardrive)

    sender.start()
    receiver.start()

    cnt = 0
    while True:
        if check == 1 and cnt == 0:
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
