#!/usr/bin/env python
#-*- coding:utf-8 -*-

import tkinter as tk
from tkinter import ttk
import mySerial
import warnmsgbox
import re

class LoraConfig(object):
  def __init__(self):
    self.RootWidth = 0
    self.RootHeight = 0
    self.Root_xoffset = 0
    self.Root_yoffset = 0
    
    self.root = None
    self.baud = ''
    self.parity = ''
    self.speed = ''
    self.senddb = ''
    self.crc = ''
    self.sendmode = ''
    self.wakeuptime = ''
    self.iomode = ''
    self.addr = 0
    self.channel = 0
    self.serial = 0
    self.warn = warnmsgbox.WarnBox()
    self.rootwindow_serialparamter_list = []
  
  def config(self, scrrenid, paramter_list):
    print('serial_lora_conf')
    #保存主窗口串口参数
    self.rootwindow_serialparamter_list.extend(paramter_list)
    print(self.rootwindow_serialparamter_list)
    #生成新的串口参数配置串口 
    paramter = ['baudrate=9600', 'parity=NONE', 'bytesize=8', 'stopbits=1']
    for val in paramter_list:
      if val.startswith('name='):
        paramter.append(val)
    mySerial.resetSerial(paramter)
    self.serial = mySerial.getSerialFD()
    print(self.serial)
    
    #设置新窗口在主窗口的中间
    scrrenid.update()
    width = 460
    height = 160
    self.Root_xoffset = scrrenid.winfo_x()
    self.Root_yoffset = scrrenid.winfo_y()
    win_width = ((self.RootWidth - width) / 2) + self.Root_xoffset
    win_height = ((self.RootHeight - height) / 2) + self.Root_yoffset
    size_str = '%dx%d+%d+%d' % (width, height, win_width, win_height)

    self.root = tk.Toplevel(scrrenid)
    self.root.geometry(size_str)
    self.root.resizable(width=False, height=False)
    #设置右上角的X功能
    self.root.protocol("WM_DELETE_WINDOW", lambda arg=self.root: self.FuncButtonCancel(arg))
    #设置窗口始终在最上层
    self.root.wm_attributes("-topmost", 1)
    self.root.title("Lora Config")

    self.warn = warnmsgbox.WarnBox()

    combox_baud = [1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200]
    combox_parity = ['8N1', '8O1', '8E1']
    combox_speed = ['0.3Kbps', '1.2Kbps', '2.4Kbps', '4.8Kbps', '9.6Kbps', '19.2Kbps']
    combox_senddb = ['20dBm', '17dBm', '14dBm', '10dBm']
    combox_crc = ['关闭', '打开']
    combox_sendmode = ['透传', '定点']
    combox_wakeuptime = ['250ms', '500ms', '750ms', '1000ms', '1250ms', '1500ms', '1750ms', '2000ms']
    combox_iomode = ['开漏', '推挽']
    
    self.baud_label = tk.Label(self.root, text='波特率')
    self.baud_combox = ttk.Combobox(self.root, values=combox_baud)
    self.baud_combox.bind("<<ComboboxSelected>>", self.select_baud)
    
    self.parity_label = tk.Label(self.root, text='校验位')
    self.parity_combox = ttk.Combobox(self.root, values=combox_parity)
    self.parity_combox.bind("<<ComboboxSelected>>", self.select_parity)
    
    self.speed_label = tk.Label(self.root, text='空中速率')
    self.speed_combox = ttk.Combobox(self.root, values=combox_speed)
    self.speed_combox.bind("<<ComboboxSelected>>", self.select_speed)
    
    self.senddb_label = tk.Label(self.root, text='发射功率')
    self.senddb_combox = ttk.Combobox(self.root, values=combox_senddb)
    self.senddb_combox.bind("<<ComboboxSelected>>", self.select_senddb)
    
    self.crc_label = tk.Label(self.root, text='前向纠错')
    self.crc_combox = ttk.Combobox(self.root, values=combox_crc)
    self.crc_combox.bind("<<ComboboxSelected>>", self.select_crc)
    
    self.sendmode_label = tk.Label(self.root, text='传输方式')
    self.sendmode_combox = ttk.Combobox(self.root, values=combox_sendmode)
    self.sendmode_combox.bind("<<ComboboxSelected>>", self.select_sendmode)
    
    self.waketime_label = tk.Label(self.root, text='唤醒时间')
    self.waketime_combox = ttk.Combobox(self.root, values=combox_wakeuptime)
    self.waketime_combox.bind("<<ComboboxSelected>>", self.select_wakeuptime)
    
    self.iomode_label = tk.Label(self.root, text='IO驱动')
    self.iomode_combox = ttk.Combobox(self.root, values=combox_iomode)
    self.iomode_combox.bind("<<ComboboxSelected>>", self.select_iomode)
    
    test_cmd = self.root.register(self.test_input_is_digit)
    self.addr_label = tk.Label(self.root, text='地址')
    self.addr_string = tk.StringVar()
    self.addr_entry = tk.Entry(self.root, textvariable=self.addr_string, validate='key', validatecommand=(test_cmd, '%P'))
    
    self.channel_label = tk.Label(self.root, text='信道')
    self.channel_string = tk.StringVar()
    self.channel_entry = tk.Entry(self.root, textvariable=self.channel_string, validate='key', validatecommand=(test_cmd, '%P'))
    
    self.writebutton = tk.Button(self.root, command=self.func_write, text='写入参数')
    self.readbutton = tk.Button(self.root, command=self.func_read, text='读取参数')
    
    self.baud_label.grid(row=0, column=0, padx=1, pady=1)
    self.baud_combox.grid(row=0, column=1, padx=1, pady=1)
    self.baud_combox.current(0)   
    self.parity_label.grid(row=0, column=2, padx=1, pady=1)
    self.parity_combox.grid(row=0, column=3, padx=1, pady=1)
    self.parity_combox.current(0)
    
    self.speed_label.grid(row=1, column=0, padx=1, pady=1)
    self.speed_combox.grid(row=1, column=1, padx=1, pady=1)
    self.speed_combox.current(0) 
    self.senddb_label.grid(row=1, column=2, padx=1, pady=1)
    self.senddb_combox.grid(row=1, column=3, padx=1, pady=1)
    self.senddb_combox.current(0) 
    
    self.crc_label.grid(row=2, column=0, padx=1, pady=1)
    self.crc_combox.grid(row=2, column=1, padx=1, pady=1)
    self.crc_combox.current(0) 
    self.sendmode_label.grid(row=2, column=2, padx=1, pady=1)
    self.sendmode_combox.grid(row=2, column=3, padx=1, pady=1)
    self.sendmode_combox.current(0) 
    
    self.waketime_label.grid(row=3, column=0, padx=1, pady=1)
    self.waketime_combox.grid(row=3, column=1, padx=1, pady=1)
    self.waketime_combox.current(0) 
    
    self.iomode_label.grid(row=3, column=2, padx=1, pady=1)
    self.iomode_combox.grid(row=3, column=3, padx=1, pady=1)
    self.iomode_combox.current(0) 
    
    self.addr_label.grid(row=4, column=0, padx=1, pady=1)
    self.addr_entry.grid(row=4, column=1, padx=1, pady=1)
    self.channel_label.grid(row=4, column=2, padx=1, pady=1)
    self.channel_entry.grid(row=4, column=3, padx=1, pady=1)
    
    self.writebutton.grid(row=5, column=0, padx=1, pady=1, columnspan=2)
    self.readbutton.grid(row=5, column=2, padx=1, pady=1, columnspan=2)
    
    self.select_baud(0)
    self.select_parity(0)
    self.select_speed(0)
    self.select_senddb(0)
    self.select_crc(0)
    self.select_sendmode(0)
    self.select_wakeuptime(0)
    self.select_iomode(0)

  def select_baud(self, args):
    self.baud = self.baud_combox.current()
  def select_parity(self, args):
    self.parity = self.parity_combox.current()
  def select_speed(self, args):
    self.speed = self.speed_combox.current()
  def select_senddb(self, args):
    self.senddb = self.senddb_combox.current()
  def select_crc(self, args):
    self.crc = self.crc_combox.current()
  def select_sendmode(self, args):
    self.sendmode = self.sendmode_combox.current()
  def select_wakeuptime(self, args):
    self.wakeuptime = self.waketime_combox.current()
  def select_iomode(self, args):
    self.iomode = self.iomode_combox.current()
                
  def func_write(self):
    print('write')
    send_str = []
    send_str.append(0xC0)
    addrstr = self.addr_entry.get()
    if addrstr.startswith('0x'):
      addr = int(addrstr, 16)
    else:
      addr = int(addrstr, 10)
    send_str.append((addr & 0xff00) >> 8)
    send_str.append((addr & 0x00ff))
    
    print('******')
    print(self.baud)
    print(self.parity)
    print(self.speed)
    print(self.senddb)
    print(self.crc)
    print(self.sendmode)
    print(self.wakeuptime)
    print(self.iomode)
    print('******')
    
    speed_byte = 0
    
    if self.parity == 0:    #'8N1':
      speed_byte |= (0 << 6)
    elif self.parity == 1:  #'8O1':
      speed_byte |= (1 << 6)
    elif self.parity == 2:  #'8E1'
      speed_byte |= (2 << 6)
    
    if self.baud == 0:    #'1200':
      speed_byte |= (0 << 3)
    elif self.baud == 1:  #'2400':
      speed_byte |= (1 << 3)
    elif self.baud == 2:  #'4800':
      speed_byte |= (2 << 3)
    elif self.baud == 3:  #'9600':
      speed_byte |= (3 << 3)
    elif self.baud == 4:  #'19200':
      speed_byte |= (4 << 3)
    elif self.baud == 5:  #'38400':
      speed_byte |= (5 << 3)
    elif self.baud == 6:  #'57600':
      speed_byte |= (6 << 3)
    elif self.baud == 7:  #'115200':
      speed_byte |= (7 << 3)
      
    if self.speed == 0:   #'0.3Kbps':
      speed_byte |= (0)
    elif self.speed == 1: #'1.2Kbps':
      speed_byte |= 1
    elif self.speed == 2: #'2.4Kbps':
      speed_byte |= 2
    elif self.speed == 3: #'4.8Kbps':
      speed_byte |= 3
    elif self.speed == 4: #'9.6Kbps':
      speed_byte |= 4
    elif self.speed == 5: #'19.2Kbps':
      speed_byte |= 5
      
    send_str.append(speed_byte)
    chanstr = self.channel_entry.get()
    if chanstr.startswith('0x'):
      chan = int(chanstr, 16)
    else:
      chan = int(chanstr, 10)
    send_str.append(chan)
    
    optionbyte = 0
    if self.sendmode == 1:  #'定点':
      optionbyte |= (1 << 7)
    elif self.sendmode == 0:  #'透传'
      optionbyte |= (0 << 7)
    
    if self.iomode == 1:    #'推挽':
      optionbyte |= (1 << 6)
    elif self.iomode == 0:  #'开漏'
      optionbyte |= (0 << 6)
      
    if self.wakeuptime == 0:    #'250ms':
      optionbyte |= (0 << 3)
    elif self.wakeuptime == 1:  #'500ms':
      optionbyte |= (1 << 3)
    elif self.wakeuptime == 2:  #'750ms':
      optionbyte |= (2 << 3)
    elif self.wakeuptime == 3:  #'1000ms':
      optionbyte |= (3 << 3)
    elif self.wakeuptime == 4:  #'1250ms':
      optionbyte |= (4 << 3)
    elif self.wakeuptime == 5:  #'1500ms':
      optionbyte |= (5 << 3)
    elif self.wakeuptime == 6:  #'1750ms':
      optionbyte |= (6 << 3)
    elif self.wakeuptime == 7:  #'2000ms':
      optionbyte |= (7 << 3)
    
    if self.crc == 1:           #'打开':
      optionbyte |= (1 << 2)
    if self.senddb == 0:        #'20dBm':
      optionbyte |= (0)
    elif self.senddb == 1:      #'17dBm':
      optionbyte |= 1
    elif self.senddb == 2:      #'14dBm':
      optionbyte |= 2
    elif self.senddb == 3:      #'10dBm':
      optionbyte |= 3
      
    send_str.append(optionbyte)
    print(send_str)
    mySerial.setParamter(send_str)
  
  def func_read(self):
    #print('read')
    parlist = mySerial.getParamter()
    if not parlist:
      self.warn.ShowMessageBox(self.root, "未读取到有效数据")
      return
    #print(parlist)
    addr = hex((parlist[1] << 8) | parlist[2])
    #print(addr)
    #msg = '0x%04x' % addr
    self.addr_string.set(addr)
    
    speed = parlist[3]
    chan = parlist[4]
    option = parlist[5]
    
    pari = (speed & 0xc0) >> 6
    self.parity_combox.current(pari)
    self.parity = self.parity_combox.current()
    
    baud = (speed & 0x38) >> 3
    self.baud_combox.current(baud)
    self.baud = self.baud_combox.current()
    
    speedair = (speed & 0x07)
    self.speed_combox.current(speedair)
    self.speed = self.speed_combox.current()
    
    self.channel_string.set(hex(chan))
    
    transmode = (option & 0x80) >> 7
    self.sendmode_combox.current(transmode)
    self.sendmode = self.sendmode_combox.current()
    
    iomode = (option & 0x40) >> 6
    self.iomode_combox.current(iomode)
    self.iomode = self.iomode_combox.current()
    
    wutime = (option & 0x38) >> 3
    self.waketime_combox.current(wutime)
    self.wakeuptime = self.waketime_combox.current()
    
    fec = (option & 0x04) >> 2
    self.crc_combox.current(fec)
    self.crc = self.crc_combox.current()
    
    senddb = (option & 0x03)
    self.senddb_combox.current(senddb)
    self.senddb = self.senddb_combox.current()
    
    
    
  def FuncButtonCancel(self, screenid):
    mySerial.resetSerial(self.rootwindow_serialparamter_list)
    screenid.destroy()
    
  def SetRootSize(self, width, height, xoffset, yoffset):
    self.RootWidth = width
    self.RootHeight = height
    self.Root_xoffset = xoffset
    self.Root_yoffset = yoffset
    
  def test_input_is_digit(self, content):
    # 如果不加上==""的话，就会发现删不完。总会剩下一个数字
    rule = r"^[0-9]+\.?[0-9]?$"
    ret = re.match(rule, content)
    if ret or content == "":
      return True
    else:
      #检测复合0x1 0x12345678 格式的字符串,十六进制
      rule = r"^0x[0-9a-fA-F]*$"
      ret = re.match(rule, content)
      if ret or content == "":
        return True
      else:
        self.warn.ShowMessageBox(self.root, '只能够输入数字')
        return False
