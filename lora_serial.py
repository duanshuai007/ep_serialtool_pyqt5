#!/usr/bin/env python
# -*- coding:utf-8 -*-

import serial
import threading
import time
import select
import sys
import queue
import serial.tools.list_ports
import operator
import crc
import socket
import logging
import json

class LoraSerial():
    isSerialOpen = False
    '''serial handler'''
    serialFd = None
    '''main thread recv queue: recv serial send messae'''
    sQueue = ''
    '''serial recvice data buffer'''
    rBuffer = []
    LoraParamter = []
    
    json_message_format = {
        "type":"",
        "content":"",
    }
    
    RecvCount = 0
    SendCount = 0
    
    def __init__(self, main_rququq):
        
        self.sQueue = main_rququq
        thread = threading.Thread(target=self.serialThread, args=[])
        thread.setDaemon(True)
        thread.start()
        pass
    
    def getSerialDataCount(self):
        return [self.SendCount, self.RecvCount]

    def clearCount(self):
        self.SendCount = 0
        self.RecvCount = 0

    def serialThread(self):
        while True:
            if self.serialFd:
                try:
                    if self.isSerialOpen == True:
                        num = self.serialFd.inWaiting()
                        if num > 0:
                            #logging.info("serial recv: %d bytes" % num)
                            ch = self.serialFd.read(1).hex()
                            ch = int(ch, 16)
                            self.rBuffer.append(ch)
                            self.RecvCount = self.RecvCount + 1
                            #logging.info(self.rBuffer)
                except Exception as e:
                    logging.error("serial read error")
                    logging.error(e.args)
            else:
                '''check new serial deivce '''
                devlist = list(serial.tools.list_ports.comports())
                #msglist = ''
                #for val in devlist:
                #    msglist = msglist + '{%s},'.format(str(val))
                self.sQueue.put(self.generateJsonMsg("update device", devlist))
                pass
            
            if self.rBuffer:
                '''data analyze'''
                head = self.rBuffer[0]
                if head == 0xA5:
                    num = len(self.rBuffer)
                    if ( num == 12 or num == 13 ) and self.rBuffer[num - 1] == 0x5A:
                        #logging.info("recv lora data")
                        #logging.info(self.rBuffer)
                        check_crc = []
                        for i in range(num - 3):
                            check_crc.append(self.rBuffer[i])
                        crcval = crc.calc_senddata(check_crc)
                        #logging.info('crcval=%x' % crcval)
                        if crcval == (self.rBuffer[num - 3] | (self.rBuffer[num - 2] << 8)):
                            #logging.info("crc check OK")
                            for i in range(num - 3, num):
                                check_crc.append(self.rBuffer[i])
                            del self.rBuffer[0:num]
                            #content = ",".join(str(i) for i in check_crc)
                            msgtype = ''
                            if num == 12:
                                msgtype = 'CTRL'
                            else:
                                msgtype = 'RESP'
                            self.sQueue.put(self.generateJsonMsg("recv", [msgtype, check_crc]))
                        else:
                            self.rBuffer.pop(0)
                        pass
                    pass
                elif head == 0xC0:
                    if len(self.rBuffer) == 6:
                        logging.info("recv paramter")
                        self.LoraParamter = []
                        for i in range(6):
                            self.LoraParamter.append(self.rBuffer.pop(0))
                    pass
                else:
                    '''head data error, pop data from position 0'''
                    self.rBuffer.pop(0)
            time.sleep(0.01)

    def generateJsonMsg(self, msgtype, msgcontent):
        self.json_message_format["type"] = msgtype
        self.json_message_format["content"] = msgcontent
        #msg = json.dumps(self.json_message_format)
        #logging.info("json msg:%s" % msg)
        return self.json_message_format

    def openSerial(self, parDict):
        name = parDict["name"]
        baud = int(parDict["baud"], 10)
        databits = int(parDict["databits"], 10)
        stopbits = int(parDict["stopbits"], 10)
        parity = parDict["parity"]
        if operator.eq(parity, 'NONE'):
            parity = serial.PARITY_NONE
        elif operator.eq(parity, 'ODD'):
            parity = serial.PARITY_ODD
        elif operator.eq(parity, 'EVEN'):
            parity = serial.PARITY_EVEN
        try:
            self.serialFd = serial.Serial(port=name, baudrate=baud, bytesize=databits, parity=parity, stopbits=stopbits, timeout=1)
            self.isSerialOpen = True
            logging.info('open serial: %s ' % self.serialFd)
            return True
        except Exception as e:
            logging.info('open serial failed')
            logging.info(e.args)
            return False

    def closeSerial(self):
        if self.serialFd:
            self.isSerialOpen = False
            self.serialFd.close()
        pass

    def isOpen(self):
        return self.isSerialOpen

    def lorasend(self, msgdict):
        msgid = int(msgdict["id"], 10)
        msgcmd = int(msgdict["cmd"], 10)
        msgpar = msgdict["paramter"]
        if msgpar:
            msgpar = int(msgpar, 10)
        else:
            msgpar = -1
        msgidentify = int(msgdict["identify"], 10)
        #logging.info("lora send message: id:%d cmd:%d par:%d identify:%d" % (msgid, msgcmd, msgpar, msgidentify))
        
        send_string = []
        send_head = []

        send_head.append((msgid >> 8) & 0xff)
        send_head.append(msgid & 0xff)
        send_head.append(msgid % 30)
        
        send_string.append(0xA5)
        '''
        when cmd in 9(set ultra safe distance),11(set timer check cycle),16(set heart time cycle) 
        the par is need.
        '''
        if msgcmd in [9, 11, 16]:
            send_string.append(msgpar)
        else:
            send_string.append(0x0C)
        send_string.append(msgid & 0xff)
        send_string.append((msgid >> 8) & 0xff)
        send_string.append(msgcmd)
        send_string.append(msgidentify & 0xff)
        send_string.append((msgidentify >> 8) & 0xff)
        send_string.append((msgidentify >> 16) & 0xff)
        send_string.append((msgidentify >> 24) & 0xff)
        
        send_head.extend(send_string)
        
        crc_val = crc.calc_senddata(send_string)
        #print(hex(crc_val))
        send_head.append(crc_val & 0xff)
        send_head.append((crc_val >> 8) & 0xff)
        send_head.append(0x5A)
        
        bytes_send = bytes(send_head)
        logging.info("send bytes:")
        logging.info(bytes_send)
        try:
            #可能是因为lora模块自身的原因，
            #如果字符之间间隔大了就会分成多帧发送，导致接收不到
            self.serialFd.write(bytes_send)
            self.SendCount = self.SendCount + len(bytes_send)
        except Exception as e:
            logging.error(e.args)

    def getParamter(self):
        senddat = [0xc1, 0xc1, 0xc1]
        bytes_send = bytes(senddat)
        self.serialFd.write(bytes_send)
        time.sleep(0.2)
        return self.LoraParamter

    def setParamter(self, parList):
        bytes_send = bytes(parList)
        self.serialFd.write(bytes_send)
        time.sleep(0.2)
        return self.LoraParamter
        #logging.info(bytes_send)

if __name__ == '__main__':
    pass

