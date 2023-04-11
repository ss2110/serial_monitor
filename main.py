import queue
import signal
import socket
import sys
import threading

import os
import datetime
import serial
from PyQt5 import uic
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import *
from serial.tools import list_ports

LOCAL_HOST = socket.gethostbyname(socket.getfqdn())  # Local IP

# code transform example
# tempStr = "10 11 12 13 14 15 16"
# str_list = tempStr.split()
# print(str_list)
# for item in str_list:
#     print("{0:02X} ".format(int(item,10)), "=> int : {0:03d} ".format(int(item, 10)))

form_class = uic.loadUiType(
                            '../UserUI/MyUI.ui')[0]  # pycharm
                            # 'd:/sam/Python_Prj_VScode/UserUI/MyUI.ui')[0] #VS code - notebook
                            # 'd:/0.sclee_work/1.sam/Python_Prj_VScode/UserUI/MyUI.ui')[0] #VS code - office
line = []  # 라인 단위로 데이터 가져올 리스트 변수 - 터미널
line2 = []  # 라인 단위로 데이터 가져올 리스트 변수 - 디스플레이
line3 = '1234'  # 송신용 변수
line4 = []
line5 = ''
line6 = []
port = 'COM4'  # 시리얼 포트
baud = 115200  # 시리얼 보레이트
exitThread = False  # 쓰레드 종료용 변수
bufferAppendFlag = True
lock = threading.Lock()
openFlag = False
ReadThreadStopFlag = False
SerialOpenFlag = False
StartTimerFlag = False
PreItem = 0
TCP_Start = False
StopTCPCommFlag = False
display_list = []
portNumber = 0
NoClientFlag = False
tcpServerQue = queue.Queue()

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

NoEndlFlag = False
NoEndlCount = 0

FirstSendFlag = True

def handler(signum, frame):
    global exitThread
    exitThread = True


def handler2(signum, frame):
    global StopTCPCommFlag
    StopTCPCommFlag = True


def readThread(ser):
    global line
    global line2
    global line3
    global exitThread
    global bufferAppendFlag

    while not exitThread:
        lock.acquire()
        try:
            for c in ser.read():
                if bufferAppendFlag:
                    # line.append(c)
                    line2.append(c)
                    # if c == 0x0A or c == 0x03:
                    #     for item in line:
                    #         print('%02X' % item, end=' ')
                    #     print('')
                    #     del line[:]
        except:
            exitThread = True

        if not line3 == '':
            try:
                ser.write(line3)
                # print(line3)
            except:
                print('SEND ERROR\n')
            finally:
                line3 = ''
        lock.release()


def ReadTcpData(client_socket):
    global TCP_Start
    global StopTCPCommFlag
    global line6
    global tcpServerQue

    while not StopTCPCommFlag:
        lock.acquire()
        try:
            data = client_socket.recv(10240)
            if not len(data) == 0:
                for item in data:
                    tcpServerQue.put(item)
                # for item in data:
                #     print('%02X' % item, end=' ')
                # print('')
        except:
            StopTCPCommFlag = True
            # print('TCP receive ERROR')
        lock.release()
    # print('TCP Client Thread Stopped..')
    TCP_Start = False

    data = '\nServer [DISCONNECTED]'
    line6.append(data)


def TCPServer(server_socket):
    global TCP_Start
    global line4
    global line5
    global client_socket
    global StopTCPCommFlag
    global line6
    global NoClientFlag
    global tcpServerQue

    NoClientFlag = True

    server_socket.listen(5)
    client_socket, addr = server_socket.accept()

    data = '\n[CONNECTED] from {}:{}'.format(addr[0], addr[1])
    line6.append(data)

    # print('[CONNECTED] from {}:{}'.format(addr[0], addr[1]))
    TCP_Start = True

    while not StopTCPCommFlag:
        lock.acquire()
        try:
            data = client_socket.recv(10240)
            if not len(data) == 0:
                for item in data:
                    tcpServerQue.put(item)
                # for item in data:
                #     print('%02X' % item, end=' ')
                # print('')
        except:
            StopTCPCommFlag = True
            # print('TCP receive ERROR')
        lock.release()
    # print('TCP Server Thread Stopped..')
    client_socket.close()
    server_socket.close()
    TCP_Start = False

    data = '\nClient [DISCONNECTED]'
    line6.append(data)
    NoClientFlag = False


class MyWindow(QMainWindow, form_class):
    global exitThread
    global SerialOpenFlag
    global StartTimerFlag
    global line3
    global line4
    global ReadThreadStopFlag
    global openFlag
    global LOCAL_HOST
    global TCP_Start
    global client_socket
    global server_socket
    global StopTCPCommFlag
    global line5
    global display_list
    global line6
    global thread_TCP_receive
    global portNumber
    global NoClientFlag
    global tcpServerQue
    global NoEndlFlag
    global NoEndlCount
    global timeElaspedCount
    global PreItem

    # client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def __init__(self):
        global SerialOpenFlag
        global StartTimerFlag
        global line3
        global TCP_Start
        global portNumber
        global NoEndlFlag
        global NoEndlCount
        global timeElaspedCount

        super().__init__()
        self.setupUi(self)

        self.pushButton1.setText("[STOP] Display")
        self.pushButton1.clicked.connect(self.DisplayStartStop)

        self.pushButton2.setText("[CLOSE]\nPort Search")
        self.pushButton2.clicked.connect(self.SerialClose)

        self.pushButton3.setText("[CLEAR] Display")
        self.pushButton3.clicked.connect(self.DisplayClear)

        self.btn_OpenCloseComm.clicked.connect(self.SerialOpen)
        self.btn_Send.clicked.connect(self.SerialSend)
        self.btn_FileSave.clicked.connect(self.FileSave)

        self.SendTextEdit.setPlainText('Start Serial Monitor! superman7105@naver.com')

        self.timer = QTimer(self)
        self.timer.setInterval(10)
        self.timer.timeout.connect(self.timeout)
        self.timer.start()
        self.StartTimerFlag = True

        self.SendIntervalNumber.setText('1000')

        self.timer2 = QTimer(self)
        self.timer2.setInterval(1000)
        self.timer2.timeout.connect(self.RepeativeSendFn)
        self.timer2.start()

        self.comport_list = []
        self.port_lists = list_ports.comports()
        for i in range(len(self.port_lists)):
            self.comport_list.append(self.port_lists[i][0])
        self.comport_list.sort()
        # for i in range(len(self.comport_list)):
        #     print(self.comport_list[i])

        for i in range(len(self.comport_list)):
            self.combo_com_x.addItem(self.comport_list[i])

        SerialOpenFlag = False
        StartTimerFlag = True

        line3 = ''

        width = 991 + 35
        height = 511 + 140
        self.setFixedSize(width, height)
        self.setWindowTitle('Serial Monitor (Data-8bit, Stop-1bit, Parity-None) - [OFF]LINE - ' + LOCAL_HOST)
        self.combo_baudrate.setCurrentIndex(5)
        self.combo_endl.setCurrentIndex(4)
        self.combo_send_type.setCurrentIndex(2)

        self.TCP_ServerName.setText(LOCAL_HOST)
        TCP_Start = False

        self.cb_TCP_Send.setChecked(False)
        self.TCP_PortNumber.setText('8888')
        portNumber = 8888

        NoEndlFlag = True
        NoEndlCount = 0

        self.cb_SaveLogPeriodic.setChecked(True)
        timeElaspedCount = 0

        try:
            if os.path.exists('log'):
                for file in os.scandir('./log/'):
                    os.remove(file.path)
        except:
            print('LOG FILE Delete ERROR')

    def RepeativeSendFn(self):
        try:
            RepeativeSendTimeValue = int(self.SendIntervalNumber.text(), 10)
        except:
            print('Repeative Send Time Input Error')
            RepeativeSendTimeValue = 1000

        self.timer2.setInterval(RepeativeSendTimeValue)
        if self.cbRepeativeSend.isChecked():
            self.SerialSend()

    def DisplayStartStop(self):  # Display START/STOP
        if self.StartTimerFlag:
            self.StartTimerFlag = False
            self.pushButton1.setText("[START] Display")
        else:
            if not self.StartTimerFlag:
                self.StartTimerFlag = True
                self.pushButton1.setText("[STOP] Display")

    def SerialClose(self):  # COMx CLOSE
        global exitThread
        global SerialOpenFlag
        global openFlag
        global client_socket
        global server_socket
        global TCP_Start
        global StopTCPCommFlag
        global thread_TCP_receive
        global NoClientFlag

        if openFlag:
            exitThread = True
            try:
                thread.join()
            except:
                print('Exception : thread.join')
            SerialOpenFlag = False
            self.setWindowTitle('Serial Monitor (Data-8bit, Stop-1bit, Parity-None) - [OFF]LINE - ' + LOCAL_HOST)

        # combo_com_x Refresh
        self.combo_com_x.clear()
        comport_list = []
        port_lists = list_ports.comports()
        for i in range(len(port_lists)):
            comport_list.append(port_lists[i][0])
        comport_list.sort()
        # for i in range(len(comport_list)):
        #     print(comport_list[i])
        for i in range(len(comport_list)):
            self.combo_com_x.addItem(comport_list[i])

        if TCP_Start:
            StopTCPCommFlag = True
            TCP_Start = False
            client_socket.close()
            server_socket.close()
            try:
                thread_TCP_receive.join()
            except:
                print('Exception : thread_TCP_receive.join')
            # self.plainTextEdit1.appendPlainText('TCP Server [DISCONNECTED]\n')
            self.setWindowTitle(
                'Serial Monitor (TCP Server [DISCONNECTED])')

        if NoClientFlag:
            # print('No Client')
            StopTCPCommFlag = True
            client_socket2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket2.connect((LOCAL_HOST, portNumber))
            client_socket2.send(b'')
            self.setWindowTitle(
                'Serial Monitor (TCP Server [STOPPED])')

    def DisplayClear(self):  # Display Clear
        self.plainTextEdit1.clear()

    def timeout(self):
        global exitThread
        global ReadThreadStopFlag
        global SerialOpenFlag
        global PreItem
        global line4
        global display_list
        global line6
        global tcpServerQue
        global NoEndlFlag
        global NoEndlCount
        global timeElaspedCount
        try:
            timeElaspedCount += 1
            if timeElaspedCount >= 60000: # 10 minutes
                timeElaspedCount = 0
                if self.cb_SaveLogPeriodic.isChecked():
                    self.FileSave()
                    self.DisplayClear()
                else:
                    self.DisplayClear()

            if not len(line6) == 0:
                for item in line6:
                    for i in item:
                        self.plainTextEdit1.moveCursor(11)
                        self.plainTextEdit1.insertPlainText(
                            '%c' % i)
                    self.plainTextEdit1.appendPlainText('')
                del line6[:]
            if not self.StartTimerFlag:
                while not tcpServerQue.empty():
                    tcpServerQue.get()
            else:
                if not tcpServerQue.empty():
                    while not tcpServerQue.empty():
                        item = tcpServerQue.get()
                        # print(type(item))
                        if self.combo_endl.currentText() == '0x03 endl 0x02':
                            if PreItem == 0x03:
                                if item == 0x02:
                                    self.plainTextEdit1.appendPlainText('')
                                    NoEndlFlag = False
                        if self.combo_display_type.currentText() == 'HEX':
                            self.plainTextEdit1.moveCursor(11)
                            self.plainTextEdit1.insertPlainText(
                                "{0:02X} ".format(item))
                        if self.combo_display_type.currentText() == 'DEC':
                            self.plainTextEdit1.moveCursor(11)
                            self.plainTextEdit1.insertPlainText(
                                "{0:03d} ".format(item))
                        if self.combo_display_type.currentText() == 'ASCII':
                            if not item == 0x0A:
                                self.plainTextEdit1.moveCursor(11)
                                self.plainTextEdit1.insertPlainText(
                                    '%c' % item)
                        try:
                            if self.chk_UserLF.isChecked():
                                if (
                                        self.combo_display_type.currentText() == 'HEX' or
                                        self.combo_display_type.currentText() == 'DEC') and item == int(
                                    self.lineEdit_UserLF.text(), 16) & 0xFF:
                                    self.plainTextEdit1.moveCursor(11)
                                    self.plainTextEdit1.appendPlainText('')
                                    NoEndlFlag = False
                            else:
                                if (
                                        self.combo_display_type.currentText() == 'HEX' or
                                        self.combo_display_type.currentText() == 'DEC') and self.combo_endl.currentText() == 'CRLF':
                                    if PreItem == 0x0D and item == 0x0A:
                                        self.plainTextEdit1.moveCursor(11)
                                        self.plainTextEdit1.appendPlainText('')
                                        NoEndlFlag = False
                                else:
                                    if not self.combo_endl.currentText() == '0x03 endl 0x02':
                                        if (
                                                self.combo_display_type.currentText() == 'HEX' or
                                                self.combo_display_type.currentText() == 'DEC') and item == int(
                                            self.combo_endl.currentText(), 16) & 0xFF:
                                            self.plainTextEdit1.moveCursor(11)
                                            self.plainTextEdit1.appendPlainText('')
                                            NoEndlFlag = False
                        except:
                            self.chk_UserLF.setChecked(False)
                            self.lineEdit_UserLF.setText('')
                            print('INPUT ERROR\n')
                            QMessageBox.question(self, 'Input Error - Line Feed', 'HEX (00~FF)\nDEC (000~255)',
                                                 QMessageBox.Ok, QMessageBox.Ok)
                        PreItem = item

                        COUNT_MAX = 400
                        if not NoEndlFlag:
                            NoEndlCount = 0
                        if NoEndlFlag:
                            NoEndlCount += 1
                            if NoEndlCount > COUNT_MAX:
                                NoEndlCount = 0
                                self.plainTextEdit1.appendPlainText('')
                        NoEndlFlag = True

                    self.plainTextEdit1.moveCursor(11)

            if exitThread and not ReadThreadStopFlag:
                ReadThreadStopFlag = True
                del line2[:]
                self.plainTextEdit1.appendPlainText('\nCOM PORT [CLOSED]')
                self.setWindowTitle('Serial Monitor (Data-8bit, Stop-1bit, Parity-None) - [OFF]LINE - ' + LOCAL_HOST)
                SerialOpenFlag = False
            sender = self.sender()
            if not self.StartTimerFlag:
                del line2[:]
            if id(sender) == id(self.timer):
                for item in line2:
                    if self.combo_endl.currentText() == '0x03 endl 0x02':
                        if PreItem == 0x03:
                            if item == 0x02:
                                self.plainTextEdit1.appendPlainText('')
                    if self.combo_display_type.currentText() == 'HEX':
                        self.plainTextEdit1.moveCursor(11)
                        self.plainTextEdit1.insertPlainText(
                            "{0:02X} ".format(item))
                    if self.combo_display_type.currentText() == 'DEC':
                        self.plainTextEdit1.moveCursor(11)
                        self.plainTextEdit1.insertPlainText(
                            "{0:03d} ".format(item))
                    if self.combo_display_type.currentText() == 'ASCII':
                        if not item == 0x0A:
                            self.plainTextEdit1.moveCursor(11)
                            self.plainTextEdit1.insertPlainText(
                                '%c' % item)
                    try:
                        if self.chk_UserLF.isChecked():
                            if (
                                    self.combo_display_type.currentText() == 'HEX' or
                                    self.combo_display_type.currentText() == 'DEC') and item == int(self.lineEdit_UserLF.text(), 16) & 0xFF:
                                self.plainTextEdit1.moveCursor(11)
                                self.plainTextEdit1.appendPlainText('')
                        else:
                            if (
                                    self.combo_display_type.currentText() == 'HEX' or
                                    self.combo_display_type.currentText() == 'DEC') and self.combo_endl.currentText() == 'CRLF':
                                if  PreItem == 0x0D and item == 0x0A:
                                    self.plainTextEdit1.moveCursor(11)
                                    self.plainTextEdit1.appendPlainText('')
                            else:
                                if not self.combo_endl.currentText() == '0x03 endl 0x02':
                                    if (
                                        self.combo_display_type.currentText() == 'HEX' or
                                        self.combo_display_type.currentText() == 'DEC') and item == int(self.combo_endl.currentText(), 16) & 0xFF:
                                        self.plainTextEdit1.moveCursor(11)
                                        self.plainTextEdit1.appendPlainText('')
                    except:
                        self.chk_UserLF.setChecked(False)
                        self.lineEdit_UserLF.setText('')
                        print('INPUT ERROR\n')
                        QMessageBox.question(self, 'Input Error - Line Feed', 'HEX (00~FF)\nDEC (000~255)',
                                             QMessageBox.Ok, QMessageBox.Ok)
                    PreItem = item
                del line[:]
                del line2[:]
                self.plainTextEdit1.moveCursor(11)
        except:
            print("TIMEOUT ERROR")

    def SerialOpen(self):
        global SerialOpenFlag
        global thread
        global exitThread
        global port
        global baud
        global ReadThreadStopFlag
        global openFlag
        global StopTCPCommFlag
        global TCP_Start
        global client_socket
        global LOCAL_HOST
        global server_socket
        global thread_TCP_receive
        global portNumber

        if self.cb_TCP_Send.isChecked():
            try:
                portNumber = int(self.TCP_PortNumber.text(), 10)
                # print(portNumber)
            except:
                print('PORT# Error')
            try:
                if self.combo_ServerClientSelect.currentText() == 'CLIENT':
                    StopTCPCommFlag = False
                    if not (TCP_Start):
                        self.plainTextEdit1.appendPlainText('')
                        TCP_Start = True
                        LOCAL_HOST = self.TCP_ServerName.text()
                        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        client_socket.settimeout(1)
                        client_socket.connect((LOCAL_HOST, portNumber))
                        client_socket.settimeout(None)
                        self.plainTextEdit1.insertPlainText('TCP Server [CONNECTED]\n')

                        thread_TCP_receive = threading.Thread(target=ReadTcpData, args=(client_socket,))
                        thread_TCP_receive.deamon = True
                        thread_TCP_receive.start()

                        self.setWindowTitle(
                            'Serial Monitor (TCP Server [CONNECTED])\n')
                if self.combo_ServerClientSelect.currentText() == 'SERVER':
                    if not NoClientFlag:
                        StopTCPCommFlag = False
                        if not (TCP_Start):
                            self.plainTextEdit1.appendPlainText('')
                            self.setWindowTitle(
                                'Serial Monitor (TCP Server [STARTED])\n')
                            self.plainTextEdit1.insertPlainText('Server [START]')
                            self.plainTextEdit1.appendPlainText('[WAIT]Client...\n')
                            LOCAL_HOST = self.TCP_ServerName.text()
                            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            server_socket.bind(('', portNumber))
                            thread_TCP_receive = threading.Thread(target=TCPServer, args=(server_socket,))
                            thread_TCP_receive.deamon = True
                            thread_TCP_receive.start()

            except:
                print('TCP OPEN ERROR')
                StopTCPCommFlag = True
                TCP_Start = False
        else:
            if not SerialOpenFlag:
                if TCP_Start:
                    return
                exitThread = False
                port = self.combo_com_x.currentText()
                baud = int(self.combo_baudrate.currentText())
                lock.acquire()
                try:
                    ser = serial.Serial(port, baud, timeout=0)
                    SerialOpenFlag = True
                    ReadThreadStopFlag = False
                    openFlag = True
                except:
                    print('COMx OPEN ERROR\n')
                    SerialOpenFlag = False
                    ReadThreadStopFlag = True
                    openFlag = False
                if SerialOpenFlag:
                    thread = threading.Thread(target=readThread, args=(ser,))
                    thread.deamon = True
                    thread.start()
                    self.plainTextEdit1.appendPlainText('\nCOM PORT [OPENED]\n')
                    self.setWindowTitle(
                        'Serial Monitor (Data-8bit, Stop-1bit, Parity-None) - [ON]LINE - ' + port + ' - ' + str(
                            baud) + 'bps')
                lock.release()

    def SerialSend(self):
        global line3
        global line5
        global SerialOpenFlag
        global client_socket
        global LOCAL_HOST
        global TCP_Start
        global StopTCPCommFlag
        global thread_TCP_receive
        global PreItem
        if SerialOpenFlag:
            try:
                self.plainTextEdit1.appendPlainText('')
                line3 = line3 + self.SendTextEdit.toPlainText()
                if self.combo_send_type.currentText() == 'HEX':
                    line3 = line3.split()
                    for item in line3:
                        self.plainTextEdit1.insertPlainText(
                            "{0:02X} ".format(int(item, 16)))
                    for i in range(len(line3)):
                        line3[i] = int(line3[i], 16) & 0xFF

                if self.combo_send_type.currentText() == 'DEC':
                    line3 = line3.split()
                    for item in line3:
                        self.plainTextEdit1.insertPlainText(
                            "{0:03d} ".format(int(item, 10)))
                    for i in range(len(line3)):
                        line3[i] = int(line3[i], 10) & 0xFF

                if self.combo_send_type.currentText() == 'ASCII':
                    self.plainTextEdit1.appendPlainText(line3)
                    line3 = line3.encode()

                PreItem = 0x03

            except:
                print('INPUT ERROR\n')
                QMessageBox.question(self, 'Input Error - Send Text', 'HEX (00~FF)\nDEC (000~255)',
                                     QMessageBox.Ok, QMessageBox.Ok)
        
        if self.cb_TCP_Send.isChecked():
            try:
                if (TCP_Start):
                    try:
                        line5 = line5 + self.SendTextEdit.toPlainText()
                        if self.combo_send_type.currentText() == 'HEX':
                            line5 = line5.split()
                            for item in line5:
                                self.plainTextEdit1.insertPlainText(
                                    "{0:02X} ".format(int(item, 16)))
                            self.plainTextEdit1.appendPlainText('')
                            for i in range(len(line5)):
                                line5[i] = int(line5[i], 16) & 0xFF
                            data = bytes(line5)
                            # print(type(data))
                            client_socket.send(data)

                        if self.combo_send_type.currentText() == 'DEC':
                            line5 = line5.split()
                            for item in line5:
                                self.plainTextEdit1.insertPlainText(
                                    "{0:03d} ".format(int(item, 10)))
                            for i in range(len(line5)):
                                line5[i] = int(line5[i], 10) & 0xFF
                            self.plainTextEdit1.appendPlainText('')
                            data = bytes(line5)
                            # print(type(data))
                            client_socket.send(data)

                        if self.combo_send_type.currentText() == 'ASCII':
                            self.plainTextEdit1.appendPlainText(line5)
                            line5 = line5.encode()+b'\n'
                            client_socket.send(line5)
                            # print(type(line5))

                    except:
                        print('INPUT ERROR\n')
                        QMessageBox.question(self, 'Input Error - Send Text', 'HEX (00~FF)\nDEC (000~255)',
                                             QMessageBox.Ok, QMessageBox.Ok)
                    line5 = ''
            except:
                print('TCP SEND ERROR')
                TCP_Start = False  

    def FileSave(self):
        global userDateTime
        userDateTime = datetime.datetime.now()
        filename = userDateTime.strftime('%Y%m%d_%H%M%S'+'.txt')
        print(filename)
        try:
            if not os.path.exists('log'):
                os.makedirs('log')
            file = open('./log/' + filename, 'w')
            str = self.plainTextEdit1.toPlainText()
            file.write(str)
            file.close()
        except:
            print('File Save ERROR')


if __name__ == "__main__":
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGINT, handler2)

    app = QApplication(sys.argv)
    myWindow = MyWindow()
    myWindow.show()

    # before UI Execution

    app.exec_()

    # after UI execution

    exitThread = True
    StopTCPCommFlag = True

    try:
        if TCP_Start:
            client_socket.close()
            # thread_TCP_receive.join()
        if NoClientFlag:
            client_socket.connect((LOCAL_HOST, portNumber))
            client_socket.close()
    except:
        print('CLOSING ERROR')


