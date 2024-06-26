import threading
from socket import *
from select import *
import time

"""_summary_
스프링 부트 서버와 소켓 통신을 통해 RC카를 제어하는 코드
코드 상에서만 소켓 통신하는 코드
RC카와 연결은 X
"""
# RC카 서버의 IP 주소와 포트 번호
host = 'localhost'  # 예: '192.168.0.100'
port = 9851  # 예: 8080

block = 0
check = 0

def drive(value, value2):
    print("----------drive: 차량 주행 코드----------")
def cardrive():
    print("----------cardrive: 차량 주행----------")
def send(sock):
    global check, block
    while True:
        if check == 1 and block == 2: #장애물
            #print("장애물")
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
            # Car.setSpeed(0)
            check = 0
            print(checkdata[:-1])
        elif int.from_bytes(data, byteorder='big') != 0:
            speed = int(checkdata[2:])
            # Car.setSpeed(speed)
            print("속도 설정")
            print("속도", speed)


try:
    server_sock = socket(AF_INET, SOCK_STREAM)
    server_sock.bind((host,port))
    server_sock.listen(10)
    print("연결을 기다리는 중")
    client_sock, addr = server_sock.accept()
    print(addr, "와 연결완료")
    
    sender = threading.Thread(target = send, args = (client_sock,))
    receiver = threading.Thread(target = receive, args = (client_sock,))
    driver = threading.Thread(target = cardrive)

    sender.start()
    receiver.start()
    
    cnt = 0
    while True:
        time.sleep(1)
        pass
        if check == 1 and cnt == 0:
            driver.start()
            cnt = 1
        if check == -1:
            # Car.stop()
            print("-----------------정지-----------------")
            cnt = 0
            break
    client_sock.close()
    server_sock.close()

except error as e:
    print(e)
    print("연결 오류")

if 'server_sock' in locals():
    server_sock.close()
