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

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QFileDialog, QWidget, QMessageBox
from PyQt5.QtCore import QFileInfo, QBasicTimer
from PyQt5.QtGui import QColor

from ui_config import Ui_Config

from lora_serial import LoraSerial

'''
Config Window Class
'''
class WindowConfig(QtWidgets.QDialog, Ui_Config):
    
    byteList = []
    serialFd = None
    isSetPar = False
    isGetPar = False
    sQueue = None
    
    LoraConfigPar = {
        "baud":{
            "1200": (0 << 3),
            "2400": (1 << 3),
            "4800": (2 << 3),
            "9600": (3 << 3),
            "19200": (4 << 3),
            "38400": (5 << 3),
            "57600": (6 << 3),
            "115200": (7 << 3),
        },
        "speedinair" : {
            "0.3Kbps" : 0,
            "1.2Kbps" : 1,
            "2.4Kbps" : 2,
            "4.8Kbps" : 3,
            "9.6Kbps" : 4,
            "19.2Kbps" : 5,
        },
        "errCheck":{
            "0" : (0),
            "1" : (1 << 2),
        },
        "wakeUpTime":{
            "250ms" : (0 << 3),
            "500ms" : (1 << 3),
            "750ms" : (2 << 3),
            "1000ms" : (3 << 3),
            "1250ms" : (4 << 3),
            "1500ms" : (5 << 3),
            "1750ms" : (6 << 3),
            "2000ms" : (7 << 3),
        },
        "parity":{
            "8N1" : (0 << 6),
            "8O1" : (1 << 6),
            "8E1" : (2 << 6),
        },
        "senddb":{
            "20dBm" : (0),
            "17dBm" : (1),
            "14dBm" : (2),
            "10dBm" : (3),
        },
        "mode":{
            "0" : (0 << 7), #pass through
            "1" : (1 << 7), #point to point
        },
        "io":{
            "0" : (0 << 6), #push pull
            "1" : (1 << 6), #open drain
        },
    }
    
    parJson = {
        "baud":0,
        "speedinair":'',
        "errCheck":'',
        "wakeUpTime":'',
        "parity":'',
        "senddb":'',
        "mode":'',
        "io":'',
        "channel":'',
        "address":'',
    }
    
    jsonMsg = {
        "type" : "serial paramter",
        "content" : {
            "baud":'',
            "databits":'',
            "parity":'',
            "stopbits":'',
        }
    }
    
    def __init__(self, main_rqueue):
        super(WindowConfig, self).__init__()
        self.setupUi(self)
        self.setFixedSize(420, 270)
        self.sQueue = main_rqueue
        '''string type'''
        self.comboBox_config_baud.currentTextChanged.connect(self.baudSelectedFunction)
        self.comboBox_config_speedinair.currentTextChanged.connect(self.speedinairSelectedFunction)
        self.comboBox_config_wakeuptime.currentTextChanged.connect(self.wakeupTimeSelectedFunction)
        self.comboBox_config_parity.currentTextChanged.connect(self.paritySelectedFunction)
        self.comboBox_config_senddb.currentTextChanged.connect(self.senddbSelectedFunction)
        '''int type'''
        self.comboBox_config_errcheck.currentIndexChanged.connect(self.errCheckSelectedFunction)
        self.comboBox_config_mode.currentIndexChanged.connect(self.modeSelectedFunction)
        self.comboBox_config_io.currentIndexChanged.connect(self.ioSelectedFunction)

        self.parJson["baud"] = self.comboBox_config_baud.currentText()
        self.parJson["speedinair"] = self.comboBox_config_speedinair.currentText()
        self.parJson["wakeUpTime"] = self.comboBox_config_wakeuptime.currentText()
        self.parJson["parity"] = self.comboBox_config_parity.currentText()
        self.parJson["senddb"] = self.comboBox_config_senddb.currentText()
        self.parJson["errCheck"] = str(self.comboBox_config_errcheck.currentIndex())
        self.parJson["mode"] = str(self.comboBox_config_mode.currentIndex())
        self.parJson["io"] = str(self.comboBox_config_io.currentIndex())

        self.pushButton_writepar.clicked.connect(self.writeParFunction)
        self.pushButton_readpar.clicked.connect(self.readParFunction)

    def closeEvent(self, event):
        #logging.info("close event")
        if self.isGetPar or self.isSetPar:
            self.jsonMsg["type"] = "serial paramter"
            self.jsonMsg["content"]["baud"] = self.parJson["baud"]
            self.jsonMsg["content"]["databits"] = '8'
            self.jsonMsg["content"]["stopbits"] = '1'
            parity = self.parJson["parity"]
            if parity == "8N1":
                self.jsonMsg["content"]["parity"] = 'NONE'
            elif parity == "8E1":
                self.jsonMsg["content"]["parity"] = 'EVEN'
            elif parity == "8O1":
                self.jsonMsg["content"]["parity"] = 'ODD'
            #self.sQueue.put(self.jsonMsg)
        else:
            self.jsonMsg["type"] = "SerialPara Not Change"
        logging.info("===Config win closeEvent:")
        logging.info(self.jsonMsg)
        self.sQueue.put(self.jsonMsg)
        self.isGetPar = False
        self.isSetPar = False

    def baudSelectedFunction(self, msg):
        self.parJson["baud"] = msg
        pass

    def speedinairSelectedFunction(self, msg):
        self.parJson["speedinair"] = msg
        pass
        
    def errCheckSelectedFunction(self, num):
        self.parJson["errCheck"] = str(num)
        pass
    
    def wakeupTimeSelectedFunction(self, msg):
        self.parJson["wakeUpTime"] = msg
        pass
        
    def paritySelectedFunction(self, msg):
        self.parJson["parity"] = msg
        pass
        
    def senddbSelectedFunction(self, msg):
        self.parJson["senddb"] = msg
        pass
        
    def modeSelectedFunction(self, num):
        self.parJson["mode"] = str(num)
        pass
        
    def ioSelectedFunction(self, num):
        self.parJson["io"] = str(num)
        pass
    
    def writeParFunction(self):
        self.byteList.clear()
        self.byteList.append(0xC0)

        addrstr = self.lineEdit_config_loraaddress.text()
        if not addrstr:
            QMessageBox.warning(self,"Warning","模块地址不能为空",QMessageBox.Ok)
            logging.error("lora address must be 0 - 0xffff")
            return

        channelstr = self.lineEdit_config_channel.text()
        if not channelstr:
            QMessageBox.warning(self,"Warning","模块信道不能为空",QMessageBox.Ok)
            logging.error("lora channel must be 0-31")
            return

        addr = 0
        channel = 0
        logging.info("address: %s, channel: %s" % (addrstr, channelstr))
        '''address'''
        if addrstr.startswith('0x'):
            addr = int(addrstr, 16)
        else:
            addr = int(addrstr, 10)
        '''channel'''
        if channelstr.startswith('0x'):
            channel = int(channelstr, 16)
        else:
            channel = int(channelstr, 10)

        self.byteList.append((addr & 0xff00) >> 8)
        self.byteList.append((addr & 0x00ff))
        
        speed_byte = 0
        speed_byte |= self.LoraConfigPar["parity"][self.parJson["parity"]]
        speed_byte |= self.LoraConfigPar["baud"][self.parJson["baud"]]
        speed_byte |= self.LoraConfigPar["speedinair"][self.parJson["speedinair"]]
        self.byteList.append(speed_byte)
        
        self.byteList.append(channel)

        optionbyte = 0
        optionbyte |= self.LoraConfigPar["mode"][self.parJson["mode"]]
        optionbyte |= self.LoraConfigPar["io"][self.parJson["io"]]
        optionbyte |= self.LoraConfigPar["wakeUpTime"][self.parJson["wakeUpTime"]]
        optionbyte |= self.LoraConfigPar["errCheck"][self.parJson["errCheck"]]
        optionbyte |= self.LoraConfigPar["senddb"][self.parJson["senddb"]]
        self.byteList.append(optionbyte)

        logging.info(self.byteList)
        ret = self.serialFd.setParamter(self.byteList)
        if operator.eq(ret, self.byteList):
            self.isSetPar = True
            QMessageBox.warning(self,"Success","Lora参数写入成功",QMessageBox.Ok)
        else:
            QMessageBox.warning(self,"Failed","Lora参数写入失败",QMessageBox.Ok)
        pass
    
    def readParFunction(self):
        ret = self.serialFd.getParamter()
        logging.info("readParFunction")
        logging.info(ret)
        if len(ret) == 6:
            QMessageBox.warning(self,"OK","Lora参数读取成功",QMessageBox.Ok)
            self.isGetPar = True
            self.lineEdit_config_loraaddress.setText(str(ret[1] << 8 | ret[2]))
            self.lineEdit_config_channel.setText(str(ret[4]))
            speed = ret[3]
            option = ret[5]

            pari = (speed & 0xc0) >> 6
            self.comboBox_config_parity.setCurrentIndex(pari)
            self.parJson["parity"] = self.comboBox_config_parity.currentText()

            baud = (speed & 0x38) >> 3
            self.comboBox_config_baud.setCurrentIndex(baud)
            self.parJson["baud"] = self.comboBox_config_baud.currentText()

            speedinair = (speed & 0x07)
            self.comboBox_config_speedinair.setCurrentIndex(speedinair)
            self.parJson["speedinair"] = self.comboBox_config_speedinair.currentText()

            transmode = (option & 0x80) >> 7
            self.comboBox_config_mode.setCurrentIndex(transmode)
            self.parJson["mode"] = str(self.comboBox_config_mode.currentIndex())
            
            iomode = (option & 0x40) >> 6
            self.comboBox_config_io.setCurrentIndex(iomode)
            self.parJson["io"] = str(self.comboBox_config_io.currentIndex())
            
            wutime = (option & 0x38) >> 3
            self.comboBox_config_wakeuptime.setCurrentIndex(wutime)
            self.parJson["wakeuptime"] = self.comboBox_config_wakeuptime.currentText()
            
            fec = (option & 0x04) >> 2
            self.comboBox_config_errcheck.setCurrentIndex(fec)
            self.parJson["errCheck"] = str(self.comboBox_config_errcheck.currentIndex())
            
            senddb = (option & 0x03)
            self.comboBox_config_senddb.setCurrentIndex(senddb)
            self.parJson["senddb"] = self.comboBox_config_senddb.currentText()
        else:
            QMessageBox.warning(self,"OK","Lora参数读取失败",QMessageBox.Ok)
        pass
        
    def start(self, serial_handler):
        self.serialFd = serial_handler
        self.show()
   