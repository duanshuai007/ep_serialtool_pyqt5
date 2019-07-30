# `ep_serialtool_pyqt5`

### Lora地锁串口调试工具

> 该工具是windows版本下的工具  
> Python版本3.7  
> 图形工具使用PyQt5  


> 可以自己生成exe执行文件，也可以直接使用。exe文件在dist目录下。


### 文件简介
> serialtool.py 该文件是主文件，执行工程时调用 python3 serialtool.py即可。  
> 以`ui_`做开头的文件是通过`pyuic.exe -o ui_xxxx.py ui_xxxx.ui`所生成的界面文件  
> loraConfig.py 是配置lora的界面功能文件，对应点击配置lora按钮后弹出来的配置界面。  
> lora_serial.py 是lora串口功能文件。主要处理lora如何收发数据。  
> crc.py 是lora发送接收数据中需要使用的crc校验功能的模块文件。  

### 通过 `***.ui` 生成 `***.py`
> `pyuic.exe -o ui_xxxx.py ui_xxxx.ui`


### 生成exe文件
> 在根目录执行`pyinstaller -F serialtool.py`,exe文件最后会生成在dist目录中。  
> 需要事先安装pyinstaller模块，并将其路径添加到环境变量中。

### 地锁协议
> 因为这个小程序是把自身作为server来使用的(虽然代码中有考虑作为end point的情况,但并没有完善相关代码)  
> 所以这里的协议是针对server所能接收和发送的来讲解。  
> 控制命令(CMD)
>> HEAD(1) LEN(1) ID(2) CMD(1) IDENTIFY(4) CRC(2) TAIL(1)  

> 响应信息(RESP)  
>> HEAD(1) LEN(1) ID(2) CMD(1) RESP(1) IDENTIFY(4) CRC(2) TAIL(1)  

>> HEAD = 0XA5, TAIL = 0X5A   
>> LEN 在发送时，该字段不参与校验，所以该值只有在需要设置设备参数(CMD = 9,11,16)时才有意义。  
>> 在接收时，该值都等于长度13.  
>> ID 占两个字节，低位在前，高位在后。IDENTIFY占4个字节，低位在前，高位在后。CRC占2个字节，低位在前。