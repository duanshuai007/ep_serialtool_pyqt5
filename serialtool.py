#!/usr/bin/env python
#-*- coding:utf-8 -*-
import sys
import logging
import queue
import threading
import time
import os
import json
import operator
import random
import copy

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QFileDialog, QWidget, QMessageBox, QHeaderView, QTableWidgetItem, QAbstractItemView
from PyQt5.QtCore import QFileInfo, QBasicTimer, Qt
from PyQt5.QtGui import QColor, QFont, QBrush

from ui_serialtool import Ui_SerialTool

from lora_serial import LoraSerial
from loraConfig import WindowConfig

'''
Main Window Class
'''    
class Window(QtWidgets.QWidget, Ui_SerialTool):
    '''Save Already exists Serial Port Name'''
    SerialPortList = ''
    loraSerial = None
    rQueue = ''
    hexSelect = False
    SerialRecvCount = 0
    SerialSendCount = 0
    devList = []
    
    cmdDict = {
        1 : '电机抬起',
        2 : '电机落下',
        3 : '电机状态',
        4 : '蜂鸣器开',
        5 : '蜂鸣器关',
        6 : '蜂鸣器状态',
        7 : '电池电量',
        8 : '停车状态',
        9 : '设安全距离',
        10 : '读安全距离',
        11 : '设超声周期',
        12 : '读超声周期',
        13 : '设备复位',
        14 : '读超声距离',
        15 : '读俩状态',
        16 : '设心跳周期',
        17 : '读心跳周期',
        101: '心跳信息',
        110: '收到响应',
    }
    
    motorStatusDict = {
        1 : '落下',
        2 : '前倾',
        3 : '竖直',
        4 : '后倾',
        5 : '有障碍',
        6 : '超声错误',
        99 : '正在执行',
    }
    
    beepStatusDict = {
        1 : '开',
        0 : '关',
    }
    haveCarStatusDict = {
        0 : '无车',
        1 : '有车',
    }
    devStatusDict = {
        "lasttime": {
            'col' : 0,
            'value' : ''
        },
        "dev_id" : {
            'col' : 1,
            'value' : '',
        },
        "dev_status" : {
            'col' : 2,
            'value' : '',
        },
        "dev_cmd" : {
            'col' : 3,
            'value' : '',
        },
        "beep" : {
            'col' : 4,
            'value' : '',
        },
        "battery" : {
            'col' : 5,
            'value' : '',
        },
        "haveCar" : {
            'col' : 6,
            'value' : '',
        },
        "ultra" : {
            'col' : 7,
            'value' : '',
        },
        "heart" : {
            'col' : 8,
            'value' : '',
        },
    }
    
    newParDict = {
        "name":"",
        "baud":0,
        "databits":0,
        "parity":"",
        "stopbits":0
    }
    
    oldParDict = {
        "name":"",
        "baud":0,
        "databits":0,
        "parity":"",
        "stopbits":0
    }
    
    weekDict = {
        "Mon" : "星期一",
        "Tue" : "星期二",
        "Wed" : "星期三",
        "Thu" : "星期四",
        "Fri" : "星期五",
        "Sat" : "星期六",
        "Sun" : "星期日",
    }
    timeStamp = 0
    
    test_count = 0
    
    def __init__(self):
        super(Window, self).__init__()
        self.setupUi(self)
        #self.setFixedSize(960, 560)

        self.rQueue = queue.Queue(20)
        self.win_config = WindowConfig(self.rQueue)
        '''自动分配列宽度'''
        self.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tableWidget.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        '''列宽度不可通过界面鼠标调整'''
        self.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        '''disable editable'''
        self.tableWidget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        '''select line'''
        self.tableWidget.setSelectionBehavior(QAbstractItemView.SelectRows)
        '''hide table col head'''
        self.tableWidget.verticalHeader().setVisible(False)
        #self.tableWidget.horizontalHeader().setVisible(False)
        self.tableWidget.setColumnWidth(0, 65)
        self.tableWidget.setColumnWidth(1, 60)
        self.tableWidget.setColumnWidth(2, 100)
        self.tableWidget.setColumnWidth(3, 100)
        self.tableWidget.setColumnWidth(4, 70)
        self.tableWidget.setColumnWidth(5, 70)
        self.tableWidget.setColumnWidth(6, 70)
        self.tableWidget.setColumnWidth(7, 70)
        self.tableWidget.setColumnWidth(8, 70)
        
        self.loraSerial = LoraSerial(self.rQueue)

        self.pushButton_open.clicked.connect(self.serialOpenButtonFunction)
        self.pushButton_config.clicked.connect(self.loraConfigButtonFunction)
        self.pushButton_dev_send.clicked.connect(self.loraSendButtonFunction)
        self.pushButton_clearcount.clicked.connect(self.clearCountFunction)
        
        self.pushButton_config.setEnabled(False)
        self.pushButton_dev_send.setEnabled(False)
        
        self.comboBox_serial_port.currentTextChanged.connect(self.serialPortSelectedFunction)
        self.comboBox_serial_baud.currentTextChanged.connect(self.serialBaudSelectedFunction)
        self.comboBox_serial_databits.currentTextChanged.connect(self.serialDatabitsSelectedFunction)
        self.comboBox_serial_parity.currentTextChanged.connect(self.serialParitySelectedFunction)
        self.comboBox_serial_stopbits.currentTextChanged.connect(self.serialStopbitsSelectedFunction)
        self.checkBox_hexselect.stateChanged.connect(self.serialdataShowFormat)
        
        self.newParDict["baud"] = "115200"
        self.comboBox_serial_baud.setCurrentText(self.newParDict["baud"])
        self.newParDict["databits"] = "8"
        self.comboBox_serial_databits.setCurrentText(self.newParDict["databits"])
        self.newParDict["parity"] = "NONE"
        self.comboBox_serial_parity.setCurrentText(self.newParDict["parity"])
        self.newParDict["stopbits"] = "1"
        self.comboBox_serial_stopbits.setCurrentText(self.newParDict["stopbits"])
        
        self.pushButton_test.clicked.connect(self.testhandler)

        self.lcd_time.setDigitCount(8)
        self.lcd_time.setSegmentStyle(QtWidgets.QLCDNumber.Flat)
        self.lcd_time.setMode(QtWidgets.QLCDNumber.Dec)

        self.timer = QBasicTimer()
        self.timer.start(10, self)
        self.recv_queue = queue.Queue(10)
        pass

    def testhandler(self):
        #a5 0c 90 00 0b ff ff ff ff f3 5e 5a
        #self.tableWidget.setGeometry(QtCore.QRect(260, 10, 800, 600))
        bytelist = [0xA5, 0x0C, 0x04, 0x00, 0x01, 0x01, 0xFF, 0xFF, 0xFF, 0xFF, 0xF3, 0x5E, 0x5A]
        bytelist[2] = bytelist[2] + self.test_count
        bytelist[4] = random.randint(1, 17)
        if bytelist[4] == 1:
            value = [0, 1, 2, 4, 5, 6, 99]
            bytelist[5] = random.randint(0, len(value))
        elif bytelist[4] == 2:
            value = [0, 2, 3, 4, 5, 6, 99]
            bytelist[5] = random.randint(0, len(value))
        elif bytelist[4] == 3:
            bytelist[5] = random.randint(1, 4)
        elif bytelist[4] in [4, 5, 6, 8, 9, 11, 16]:
            bytelist[5] = random.randint(0, 1)
        elif bytelist[4] in [7, 10, 12, 14, 17]:
            bytelist[5] = random.randint(1, 100)
        
        msglist = ['RESP', bytelist]
        logging.info("count=%d" % self.test_count)
        logging.info(bytelist)
        self.LoraDataAnalysisAndShow(msglist)
        self.test_count = self.test_count + random.randint(0,1)
        
    def closeEvent(self, event):
        #logging.info("MainWindow close")
        self.loraSerial.closeSerial()

    def clearCountFunction(self):
        self.loraSerial.clearCount()
        
    def serialdataShowFormat(self, num):
        if num > 0:
            self.hexSelect = False
            self.checkBox_hexselect.setText("十进制显示")
        else:
            self.hexSelect = True
            self.checkBox_hexselect.setText("十六进制显示")
        
    def serialPortSelectedFunction(self, msg):
        if not msg:
            return
        ''''example: COM9 - Silicon LabsCP210x USB to UART Bridge (COM9)
        '''
        msglist = msg.split('-')
        self.newParDict["name"] = msglist[0]
        pass

    def serialBaudSelectedFunction(self, msg):
        self.newParDict["baud"] = msg

    def serialDatabitsSelectedFunction(self, msg):
        self.newParDict["databits"] = msg
        
    def serialParitySelectedFunction(self, msg):
        self.newParDict["parity"] = msg
        
    def serialStopbitsSelectedFunction(self, msg):
        self.newParDict["stopbits"] = msg
  
    '''
    Open Serial Button Func
    '''
    def serialOpenButtonFunction(self):
        #logging.info("open serial button pressed")
        if self.loraSerial.isOpen() == False:
            '''open serial'''
            if self.loraSerial.openSerial(self.newParDict) == True:
                self.pushButton_config.setEnabled(True)
                self.pushButton_dev_send.setEnabled(True)
                self.pushButton_open.setText("关闭")
            pass
        else:
            '''close serial'''
            self.loraSerial.closeSerial()
            self.pushButton_config.setEnabled(False)
            self.pushButton_dev_send.setEnabled(False)
            self.pushButton_open.setText("打开")
            pass
        pass

    def loraConfigButtonFunction(self):
        logging.info("loraConfigButtonFunction")
        '''
        when enter config window
        we must close the serial and reopen serial 
        as 9600 baud 8 databits 1 stopbits NONE parity
        '''
        self.oldParDict["name"] = self.newParDict["name"]
        self.oldParDict["parity"] = self.newParDict["parity"]
        self.oldParDict["baud"] = self.newParDict["baud"]
        self.oldParDict["stopbits"] = self.newParDict["stopbits"]
        self.oldParDict["databits"] = self.newParDict["databits"]
        self.loraSerial.closeSerial()
        
        self.newParDict["parity"] = 'NONE'
        self.newParDict["baud"] = '9600'
        self.newParDict["databits"] = '8'
        self.newParDict["stopbits"] = '1'
        if self.loraSerial.openSerial(self.newParDict) == False:
            logging.error("config lora serial 9600 8N1 failed")
            return
        self.win_config.start(self.loraSerial)
        pass
        
    def loraSendButtonFunction(self):
        data = {
            "id" : '',
            "cmd" : '',
            "paramter" : '',
            "identify" : '',
        }
        mId = self.lineEdit_dev_id.text()
        mCmd = self.lineEdit_dev_cmd.text()
        mPar = self.lineEdit_dev_par.text()
        mIdentify = self.lineEdit_dev_identify.text()
        if not mId or not mCmd: 
            QMessageBox.warning(self,"Warning","设备ID和CMD不能为空",QMessageBox.Ok)
            return
        if mId.startswith("0x"):
            data["id"] = str(int(mId, 16))
        else:
            data["id"] = mId
        if mCmd.startswith("0x"):
            data["cmd"] = str(int(mCmd, 16))
        else:
            data["cmd"] = mCmd
        if mPar:
            if mPar.startswith("0x"):
                data["paramter"] = str(int(mPar, 16))
            else:
                data["paramter"] = mPar
        else:
            if data["cmd"] in ["9", "11", "16"]:
                QMessageBox.warning(self,"Warning","CMD等于9/11/16时，参数不能为空",QMessageBox.Ok)
                return
        if mIdentify:
            if mIdentify.startswith("0x"):
                data["identify"] = str(int(mIdentify, 16))
            else:
                data["identify"] = mIdentify
        else:
            data["identify"] = str(4294967295)
        try:
            logging.info("send data")
            logging.info(data)
            self.loraSerial.lorasend(data)
        except Exception as e:
            logging.error(e.args)
        pass

    '''下载按钮使能禁止'''
    def setDownloadButtonEnable(self):
        text = self.textEdit.toPlainText()
        if not text:
            self.btn_startdownload.setEnabled(False)
        else:
            self.btn_startdownload.setEnabled(True)
        pass

    def clickedListWidget(self):
        logging.info("ListWidget click")
        pass
    
    def LoraDataDirectlyShow(self, bytelist):
        msg = ''
        for dat in bytelist:
            if self.hexSelect == False:
                msg = msg + "{:0>2x} ".format(dat)
            else:
                msg = msg + "{:0>3d} ".format(dat)
        hexmsgshow = "%s # %s" % (time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), msg)
        item = QtWidgets.QListWidgetItem(hexmsgshow)
        count = self.listWidget_hexshow.count()
        if count >= 6:
            self.listWidget_hexshow.takeItem(0)
        self.listWidget_hexshow.addItem(item)
       
    def tableWidgetInsert(self, tmpMsgDict):
        logging.info(tmpMsgDict)
        rowcount = self.tableWidget.rowCount()
        self.tableWidget.insertRow(rowcount)
        time_item = QTableWidgetItem(tmpMsgDict["lasttime"]["value"])
        time_item.setTextAlignment(Qt.AlignCenter)
        devID_item = QTableWidgetItem(tmpMsgDict["dev_id"]["value"])
        devID_item.setTextAlignment(Qt.AlignCenter)
        devStat_item = QTableWidgetItem(tmpMsgDict["dev_status"]["value"])
        devStat_item.setTextAlignment(Qt.AlignCenter)
        #devStat_item.setFont(QFont('Times', 9))
        devCMD_item = QTableWidgetItem(tmpMsgDict["dev_cmd"]["value"])
        devCMD_item.setTextAlignment(Qt.AlignCenter)
        #devCMD_item.setFont(QFont('Times', 9))
        beep_item = QTableWidgetItem(tmpMsgDict["beep"]["value"])
        beep_item.setTextAlignment(Qt.AlignCenter)
        battery_item = QTableWidgetItem(tmpMsgDict["battery"]["value"])
        battery_item.setTextAlignment(Qt.AlignCenter)
        havecar_item = QTableWidgetItem(tmpMsgDict["haveCar"]["value"])
        havecar_item.setTextAlignment(Qt.AlignCenter)
        ultra_item = QTableWidgetItem(tmpMsgDict["ultra"]["value"])
        ultra_item.setTextAlignment(Qt.AlignCenter)
        heart_item = QTableWidgetItem(tmpMsgDict["heart"]["value"])
        heart_item.setTextAlignment(Qt.AlignCenter)
        self.tableWidget.setItem(rowcount, 0, time_item)
        self.tableWidget.setItem(rowcount, 1, devID_item)
        self.tableWidget.setItem(rowcount, 2, devStat_item)
        self.tableWidget.setItem(rowcount, 3, devCMD_item)
        self.tableWidget.setItem(rowcount, 4, beep_item)
        self.tableWidget.setItem(rowcount, 5, battery_item)
        self.tableWidget.setItem(rowcount, 6, havecar_item)
        self.tableWidget.setItem(rowcount, 7, ultra_item)
        self.tableWidget.setItem(rowcount, 8, heart_item)
        pass
    
    def tableWidgetUpdate(self, MsgDict):
        '''更新对应行的内容'''
        item = QTableWidgetItem(MsgDict["value"])
        item.setTextAlignment(Qt.AlignCenter)
        self.tableWidget.setItem(MsgDict['row'], MsgDict['col'], item)
        timeitem = QTableWidgetItem(MsgDict["time"])
        timeitem.setTextAlignment(Qt.AlignCenter)
        self.tableWidget.setItem(MsgDict['row'], 0, timeitem)
        cmditem = QTableWidgetItem(MsgDict["cmd"])
        cmditem.setTextAlignment(Qt.AlignCenter)
        self.tableWidget.setItem(MsgDict['row'], 3, cmditem)
        pass
    
    def tableWidgetDelete(self, devid):
        pass
    
    def LoraDataAnalysisAndShow(self, recvList):
        #a5-0 0c-1 90-2 00-3 06-4 ff-5 ff-6 ff-7 ff-8 de-9 9f-10 5a-11
        logging.info("LoraDataAnalysisAndShow recv:")
        logging.info(recvList)
        msgtype = recvList[0]
        bytelist = recvList[1]
        logging.info(msgtype)
        logging.info(bytelist)
        deviceID = (bytelist[2] | (bytelist[3] << 8))
        deviceCMD = bytelist[4]
        rowcount = self.tableWidget.rowCount()
        
        text = '{:d}'.format(deviceID)
        items = self.tableWidget.findItems(text, Qt.MatchExactly)
        if items:
            '''FIND SAME DEVID ITEM, THEN UPDATE ITEM MESSAGE'''
            item = items[0]
            row = item.row()
            #col = item.column()
            #msg = item.text()
            #logging.info("find same id item: row = %d col=%d" % (row,col))
            #item.setSelected(True)
            #item.setForeground(QBrush(QColor(255,0,0)))
            msgDict = {
                'row' : row,
                'col' : '',
                'cmd' : self.cmdDict[deviceCMD],
                'value' : '',
                'time' : time.strftime("%H:%M:%S", time.localtime())
            }
            if msgtype == 'RESP':
                deviceRESP = bytelist[5]
                if deviceCMD in [1,2,4,5,9,11,16]:
                    msgDict['col'] = self.devStatusDict["dev_status"]["col"]
                    if deviceRESP == 0:
                        msgDict["value"] = "成功"
                    else:
                        if deviceCMD in [1, 2]:
                            msgDict["value"] = "{}{}".format("err:", self.motorStatusDict[deviceRESP])
                        else:
                            msgDict["value"] = "失败"
                elif deviceCMD == 3:
                    msgDict['col'] = self.devStatusDict["dev_status"]["col"]
                    msgDict["value"] = self.motorStatusDict[deviceRESP]
                elif deviceCMD == 6:
                    msgDict['col'] = self.devStatusDict["beep"]["col"]
                    msgDict["value"] = self.beepStatusDict[deviceRESP]
                elif deviceCMD == 7:
                    msgDict['col'] = self.devStatusDict["battery"]["col"]
                    msgDict["value"] = "{:d}%".format(deviceRESP)
                elif deviceCMD == 8:
                    msgDict['col'] = self.devStatusDict["haveCar"]["col"]
                    msgDict["value"] = self.haveCarStatusDict[deviceRESP]
                elif deviceCMD == 10:
                    msgDict['col'] = self.devStatusDict["ultra"]["col"]
                    msgDict["value"] = "R|S:{:d}cm".format(deviceRESP)
                elif deviceCMD == 12:
                    msgDict['col'] = self.devStatusDict["ultra"]["col"]
                    msgDict["value"] = "R|C:{:d}s".format(deviceRESP)
                elif deviceCMD == 13:
                    msgDict['col'] = self.devStatusDict["dev_status"]["col"]
                    msgDict["value"] = "复位..."
                elif deviceCMD == 14:
                    msgDict['col'] = self.devStatusDict["ultra"]["col"]
                    msgDict["value"] = "R|D:{:d}cm".format(deviceRESP)
                elif deviceCMD == 15:
                    '''高四位表示有车无车，低四位表示地锁状态'''
                    h4bit = (deviceRESP >> 4) & 0x0f
                    l4bit = deviceRESP & 0x0f
                    msgDict["value"] = self.haveCarStatusDict[h4bit]
                    msgDict['col'] = self.devStatusDict["haveCar"]["col"]
                    self.tableWidgetUpdate(msgDict)
                    msgDict["value"] = self.motorStatusDict[l4bit]
                    msgDict['col'] = self.devStatusDict["dev_status"]["col"]
                elif deviceCMD == 17:
                    msgDict["value"] = "{:d}s".format(deviceRESP)
                    msgDict['col'] = self.devStatusDict["heart"]["col"]
                elif deviceCMD == 101:
                    msgDict["value"] = self.cmdDict[deviceCMD]
                    msgDict['col'] = self.devStatusDict["dev_cmd"]["col"]
                    self.tableWidgetUpdate(msgDict)
                    msgDict["value"] = "{:d}%".format(deviceRESP)
                    msgDict['col'] = self.devStatusDict["battery"]["col"]
            else:
                '''如果接收到控制命令，更新控制命令的消息'''
                msgDict['col'] = self.devStatusDict["dev_cmd"]["col"]
                msgDict['value'] = self.cmdDict[deviceCMD]
            self.tableWidgetUpdate(msgDict)
            del msgDict
        else:
            '''NOT FIND SAME DEVID ITEM, ADD NEW ITEM INTO TABLEWIDGET'''
            logging.info("not find item")
            #tmpMsgDict = self.devStatusDict.copy()
            
            tmpMsgDict = copy.deepcopy(self.devStatusDict)
            tmpMsgDict["dev_id"]["value"] = str(deviceID)
            try:
                tmpMsgDict["lasttime"]["value"] = time.strftime("%H:%M:%S", time.localtime())
                tmpMsgDict["dev_cmd"]["value"] = self.cmdDict[deviceCMD]
                if msgtype == 'RESP':
                    deviceRESP = bytelist[5]
                    if deviceCMD in [1,2,4,5,9,11,16]:
                        if deviceRESP == 0:
                            tmpMsgDict["dev_status"]["value"] = "成功"
                        else:
                            if deviceCMD in [1, 2]:
                                tmpMsgDict["dev_status"]["value"] = "{}{}".format("err:", self.motorStatusDict[deviceRESP])
                            else:
                                tmpMsgDict["dev_status"]["value"] = "失败"
                    elif deviceCMD == 3:
                        tmpMsgDict["dev_status"]["value"] = self.motorStatusDict[deviceRESP]
                    elif deviceCMD == 6:
                        tmpMsgDict["beep"]["value"] = self.beepStatusDict[deviceRESP]
                    elif deviceCMD == 7:
                        tmpMsgDict["battery"]["value"] = "{:d}%".format(deviceRESP)
                    elif deviceCMD == 8:
                        tmpMsgDict["haveCar"]["value"] = self.haveCarStatusDict[deviceRESP]
                    elif deviceCMD == 10:
                        tmpMsgDict["ultra"]["value"] = "R|S:{:d}cm".format(deviceRESP)
                    elif deviceCMD == 12:
                        tmpMsgDict["ultra"]["value"] = "R|C:{:d}s".format(deviceRESP)
                    elif deviceCMD == 13:
                        tmpMsgDict["dev_status"]["value"] = "复位..."
                    elif deviceCMD == 14:
                        tmpMsgDict["ultra"]["value"] = "R|D:{:d}cm".format(deviceRESP)
                    elif deviceCMD == 15:
                        '''高四位表示有车无车，低四位表示地锁状态'''
                        h4bit = (deviceRESP >> 4) & 0x0f
                        l4bit = deviceRESP & 0x0f
                        tmpMsgDict["haveCar"]["value"] = self.haveCarStatusDict[h4bit]
                        tmpMsgDict["dev_status"]["value"] = self.motorStatusDict[l4bit]
                    elif deviceCMD == 17:
                        tmpMsgDict["heart"]["value"] = "{:d}s".format(deviceRESP)
                    elif deviceCMD == 101:
                        tmpMsgDict["battery"]["value"] = "{:d}%".format(deviceRESP)
                #logging.info("ready goto tableWidgetInsert")
                self.tableWidgetInsert(tmpMsgDict)
                del tmpMsgDict
            except Exception as e:
                del tmpMsgDict
                logging.error("cmdDict not has the key")
                logging.error(e.args)

    def timerEvent(self, event):
        #logging.info("time event ofcus")
        if not self.rQueue.empty():
            msg = self.rQueue.get()
            try:
                if msg["type"] == "update device":
                    '''update serial port list'''
                    commstrlist = msg["content"]
                    tmpPortDevList = []
                    for val in commstrlist:
                        tmpPortDevList.append(str(val))
                    if not operator.eq(tmpPortDevList, self.SerialPortList):
                        self.SerialPortList = tmpPortDevList
                        self.comboBox_serial_port.clear()
                        for val in tmpPortDevList:
                            self.comboBox_serial_port.addItem(val)
                elif msg["type"] == "recv":
                    '''lora has recvive data from other lora module'''
                    recvdataList = msg["content"]
                    logging.info("recv:")
                    logging.info(recvdataList)
                    self.LoraDataDirectlyShow(recvdataList[1])
                    self.LoraDataAnalysisAndShow(recvdataList)
                    pass
                elif msg["type"] == "serial paramter":
                    '''when user in config page write or read paramters, reconfig serial'''
                    logging.info("config windows close, recv new serial paramters")
                    self.newParDict["parity"] = msg["content"]["parity"]
                    self.newParDict["baud"] = msg["content"]["baud"]
                    self.newParDict["databits"] = msg["content"]["databits"]
                    self.newParDict["stopbits"] = msg["content"]["stopbits"]
                    if not operator.eq(self.newParDict, self.oldParDict):
                        self.loraSerial.closeSerial()
                        self.comboBox_serial_baud.setCurrentText(self.newParDict["baud"])
                        self.comboBox_serial_databits.setCurrentText(self.newParDict["databits"])
                        self.comboBox_serial_parity.setCurrentText(self.newParDict["parity"])
                        self.comboBox_serial_stopbits.setCurrentText(self.newParDict["stopbits"])
                        self.loraSerial.openSerial(self.newParDict)
                    pass
                elif msg["type"] == "SerialPara Not Change":
                    self.loraSerial.closeSerial()
                    self.comboBox_serial_baud.setCurrentText(self.oldParDict["baud"])
                    self.comboBox_serial_databits.setCurrentText(self.oldParDict["databits"])
                    self.comboBox_serial_parity.setCurrentText(self.oldParDict["parity"])
                    self.comboBox_serial_stopbits.setCurrentText(self.oldParDict["stopbits"])
                    self.loraSerial.openSerial(self.oldParDict)
                    self.newParDict["name"] = self.oldParDict["name"]
                    self.newParDict["parity"] = self.oldParDict["parity"]
                    self.newParDict["baud"] = self.oldParDict["baud"]
                    self.newParDict["stopbits"] = self.oldParDict["stopbits"]
                    self.newParDict["databits"] = self.oldParDict["databits"]

            except Exception as e:
                logging.error("timer event error")
                logging.error(e.args)
        rlist = self.loraSerial.getSerialDataCount()
        if len(rlist) == 2:
            self.label_sendnum.setText(str(rlist[0]))
            self.label_recvnum.setText(str(rlist[1]))
        timeStamp = int(time.time())
        if timeStamp != self.timeStamp:
            self.timeStamp = timeStamp
            timestr = time.strftime("%Y-%m-%d %H:%M:%S %a", time.localtime())
            timelist = timestr.split(' ')
            self.lcd_time.display(timelist[1])
            date = timelist[0]
            datelist = date.split('-')
            datestr = '{}年{}月{}日 {}'.format(datelist[0], datelist[1], datelist[2], self.weekDict[timelist[2]])
            self.label_date.setText(datestr)
        pass

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG,format='%(asctime)s %(levelname)s:%(filename)s[line:%(lineno)d]: %(message)s',datefmt='%Y-%m-%d %H:%M:%S')
    #logging.basicConfig(filename="mydebug.log", level=logging.DEBUG,format='%(asctime)s %(levelname)s:%(filename)s[line:%(lineno)d]: %(message)s',datefmt='%Y-%m-%d %H:%M:%S')
    app = QtWidgets.QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec_())