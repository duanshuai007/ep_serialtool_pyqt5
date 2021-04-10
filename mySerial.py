#!/usr/bin/env python
# -*- coding:utf-8 -*-

import serial
import threading
import time
import select
import sys
import queue
import serial.tools.list_ports as port_list
import operator
import crc
import socket

serial_fd = None
LoraParamter = []

def getDevList():
    return list(port_list.comports())

def getSerialFD():
  global serial_fd
  return serial_fd
  
def open(paramter_list):
    global serial_fd 
    ret = False
    
    for val in paramter_list:
      if val.startswith('name='):
        val_list = val.split('=')
        name = val_list[1]
      if val.startswith('baudrate='):
        val_list = val.split('=')
        baud = int(val_list[1], 10)
      if val.startswith('bytesize='):
        val_list = val.split('=')
        bytesize = int(val_list[1], 10)
      elif val.startswith('parity='):
        val_list = val.split('=')
        parity = val_list[1]
        if operator.eq(parity, 'NONE'):
          parity = serial.PARITY_NONE
        elif operator.eq(parity, 'ODD'):
          parity = serial.PARITY_ODD
        elif operator.eq(parity, 'EVEN'):
          parity = serial.PARITY_EVEN
      elif val.startswith('stopbits='):
        val_list = val.split('=')
        stopbits = int(val_list[1], 10)
        
    if serial_fd:
      print('serial already open')
      return
    try:
      serial_fd = serial.Serial(port=name, baudrate=baud, bytesize=bytesize, parity=parity, stopbits=stopbits, timeout=1)
      print('open serial: %s ' % serial_fd)
      ret = True
    except Exception as e:
      print('open serial failed')
      print(e.args)
    finally:
      return ret

def close():
    global serial_fd
    if not serial_fd:
      return
    serial_fd.close()
    serial_fd = None
    
def send(msgid, msgcmd, msgpar, msgidentify):
    global serial_fd
    if not serial_fd:
       return
    
    send_string = []
    send_head = []

    send_head.append((msgid >> 8) & 0xff)
    send_head.append(msgid & 0xff)
    send_head.append(msgid % 30)
    
    send_string.append(0xA5)
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
    try:
      print('serial send:')
      for val in bytes_send:
        print(hex(val), end=' ')
      print(" ")
      
      #可能是因为lora模块自身的原因，
      #如果字符之间间隔大了就会分成多帧发送，导致接收不到
      serial_fd.write(bytes_send)
    except Exception as e:
      print(e.args)
	  
def resetSerial(paramter_list):
  global serial_fd
  global serial_name
  close()
  open(paramter_list)
  #serial_fd = serial.Serial(serial_name, baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=1)
  #print(serial_fd)
  
def getParamter():
  global serial_fd
  global LoraParamter
  #setSerial()
  send = [0xc1, 0xc1, 0xc1]
  bytes_send = bytes(send)
  serial_fd.write(bytes_send)
  time.sleep(0.2)
  return LoraParamter
  
def setParamter(str_list):
  global serial_fd
  #setSerial()
  bytes_send = bytes(str_list)
  serial_fd.write(bytes_send)
  print('setParamter')
  print(bytes_send)
  
#>>> a = 'aabbccddeeff'
#>>> a_bytes = bytes.fromhex(a)   hex字符串转换为bytes
#b'\xaa\xbb\xcc\xdd\xee\xff'      bytes转换为hex字符串
#>>> aa = a_bytes.hex() 
def StartRecvice():
    global serial_fd
    p = threading.Thread(target = ReadDataThread, args = [ ])
    p.setDaemon(True)
    p.start()
    
#从串口接收数据，然后发送给主窗口
def ReadDataThread():
    #print('ReadDataThread: %s ' % serialid)
    global serial_fd
    global LoraParamter
    msglen = 0
    ch_list = []
    timeout_count = 0
    
    socketid = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ipport = ('127.0.0.1', 9876)
    socketid.connect(ipport)
    recvflag = None
    while True:
      if serial_fd:
        try:
          if serial_fd.isOpen():
              num = serial_fd.inWaiting()
              if num > 0:
                ch = serial_fd.read(1).hex()
                ch = int(ch, 16)
                #print('ch=%x' % ch)
                #print(type(ch))
                if msglen > 0:
                    ch_list.append(ch)
                    msglen = msglen + 1
                if ch == 0xa5 and msglen == 0:
                    msglen = 1
                    ch_list = [ch, ]
                    recvflag = 1
                elif ch == 0xc0:
                  #print('recv lora paramter')
                  msglen = 1
                  recvflag = 2
                  LoraParamter = []
                  ch_list = [ch, ]
                #print(msglen)
                #节点接收到服务器控制命令，长度12
                #服务器接收到节点响应信息，长度13
                if recvflag == 1:
                  if msglen == 12 or msglen == 13:
                      #print('msglen=%d' % msglen)
                      if ch == 0x5a:
                        check_crc = []
                        for i in range(msglen-3):
                          check_crc.append(ch_list[i])
                        #print(check_crc)
                        crcval = crc.calc_senddata(check_crc)
                        #print('crcval=%x' % crcval)
                        if crcval == ch_list[msglen-3] | (ch_list[msglen-2] << 8):
                          #print('crc right')
                          mId = check_crc[2] | (check_crc[3] << 8)
                          mCmd = check_crc[4]
                          if msglen == 12:
                            #解析服务器的控制命令
                            #格式:HEAD LEN/PAR ID_L ID_H CMD I4 I3 I2 I1
                            mType = 'Ctrl'
                            mIdentify = check_crc[5] | (check_crc[6] << 8) | (check_crc[7] << 16) | (check_crc[8] << 24)
                            mParamter = 0
                            #将结果信息发送给主窗口
                            sendstr = '%s-%x-%x-%x-%x' % (mType, mId, mCmd, mParamter, mIdentify)
                            sendbytes = bytes(sendstr, encoding='utf-8')  #bytes将字符串转换为bytes
                                                                          #str将bytes转换为字符串
                            socketid.send(sendbytes)
                          else :
                            #解析地锁发送来的响应信息
                            #格式:HEAD LEN ID_L ID_H CMD RESP I4 I3 I2 I1
                            mType = 'Resp'
                            mIdentify = check_crc[6] | (check_crc[7] << 8) | (check_crc[8] << 16) | (check_crc[9] << 24)
                            mResp = check_crc[5]
                            #将结果信息发送给主窗口
                            sendstr = '%s-%x-%x-%x-%x' % (mType, mId, mCmd, mResp, mIdentify)
                            sendbytes = bytes(sendstr, encoding='utf-8')
                            socketid.send(sendbytes)
                        else:
                          print('crc error')
                        msglen = 0
                        recvflag = 0
                      if msglen == 13:
                        msglen = 0
                        recvflag = 0
                  #接收地锁信息解析结束
                elif recvflag == 2:
                  if msglen == 6:
                    msglen = 0
                    recvflag = 0
                    #print('recv paramter end')
                    #print(ch_list)
                    LoraParamter.extend(ch_list)
              time.sleep(0.01)
          else:
              print('child ReadDataThread exit')
              time.sleep(0.1)
              #return
        except Exception as e:
            print(e.args)
            time.sleep(1)
      else:
        time.sleep(0.1)

if __name__ == '__main__':
    getSerialName('COM9 - system')
    getSerialBaud('115200')
    getSerialDatabits('8')
    getSerialStopbits('1')
    getSerialParity('NONE')
    open()
    StartRecvice(1)
    #serial_data_process(serial)

