import time as tm
import serial.tools.list_ports
import serial as ser
import threading as th
import tkinter as tk
import requests as rqst

########################################################################################################################
massageDevStatus = False                                        # The status of device
massageProcess = ""                                             # 短信处理标志
massageIndexNow = 0                                             # 现在的信息

def dataIsUnicode(sms_text_str):
  compare_str = "0123456789ABCDEF"
  for i in range(0, len(sms_text_str)):
    result = compare_str.find(sms_text_str[i], 0, len(compare_str))
    if result == -1:
      return False
  return True

def findSubStr(substr, str, i):
  count = 0
  while i > 0:
    index = str.find(substr)
    if index == -1:
      return -1
    else:
      str = str[index + 1:]                                     # 第一次出现的位置截止后的字符串
      i -= 1
      count = count + index + 1                                 # 字符串位置数累加
  return count - 1


# 设备搜索
def device_searching():
  global massageDevStatus
  global uart
  global uart_rx_len
  global uart_rx_str
  plist = list(serial.tools.list_ports.comports())              # Read the serial port list
  if len(plist) > 0:
    uart_num = len(plist)                                       # Read the serial numbers
    i = 0
  for i in range(0, uart_num, 1):
    plist_0 = list(plist[i])
    uartName = plist_0[i]
    try:
      uart = ser.Serial(uartName, 115200, timeout=60)
      uartIsOpen = uart.isOpen()                                # Judge wheather the serial port is open
      if uartIsOpen == False:
        print("Serial port is occupied!")
        continue
      uart.write("AT\r\n".encode())                             # Send AT test instruction
      tm.sleep(0.01)                                            # Waitting for about 10ms
      uart_rx_len = uart.in_waiting                             # Read the buffer in recived buffer
      uart_rx_str = str(uart.read(uart_rx_len))
      if uart_rx_str.find('OK'):                                # If the device respose character "OK"
        device_status_entry.delete(0, tk.END)
        device_status_entry.insert(0, "设备已连接")
        massageDevStatus = True
        break
    except:
      continue
  if i == uart_num:
    device_status_entry.delete(0, tk.END)
    device_status_entry.insert(0, "设备未连接")
    massageDevStatus = False
  return massageDevStatus


# 解析短信
def sms_parsing(sms_info_str):
  # 解析电话号码字符串
  phone_number_pos_start = findSubStr("\"", sms_info_str, 3) + 1
  phone_number_pos_end = findSubStr("\"", sms_info_str, 4)
  phone_number_str = sms_info_str[phone_number_pos_start:phone_number_pos_end]
  phone_number_entry.delete(0, tk.END)
  phone_number_entry.insert(0, phone_number_str)
  # 解析时间
  sms_time_index_start = findSubStr("\"", sms_info_str, 7) + 1
  sms_time_index_end = findSubStr("\"", sms_info_str, 8) - 3
  sms_time_str = sms_info_str[sms_time_index_start:sms_time_index_end]
  sms_time_str = sms_time_str.replace(',', ' ')
  massage_time_entry.delete(0, tk.END)
  massage_time_entry.insert(0, sms_time_str)
  # 解析短信内容
  sms_text_index_start = findSubStr("\\r\\n", sms_info_str, 1) + 4
  sms_text_index_end = findSubStr("\\r\\n", sms_info_str, 2) - 1
  sms_text_str = sms_info_str[sms_text_index_start:sms_text_index_end]
  result = dataIsUnicode(sms_text_str)
  massage_text.delete(1.0, tk.END)
  if result == True:
    sms_text_str_unicode = ""
    for i in range(0, int(len(sms_text_str) / 4)):
      sms_text_str_unicode = sms_text_str_unicode + '\\u' + sms_text_str[i * 4:i * 4 + 4]
    sms_text_str_utf8 = sms_text_str_unicode.encode('utf-8').decode('unicode_escape')
    massage_text.insert(tk.END, sms_text_str_utf8)
  else:
    massage_text.insert(tk.END, sms_text_str)


# 读取最新短信
def sms_read_new():
  global massageIndexNow
  sms_text_str = sms_read_text()
  sms_index = sms_get_index(sms_text_str)
  if sms_index != -1:
    sms_info_str = sms_get_whole_one(sms_text_str, sms_index)
    sms_parsing(sms_info_str)
    massageIndexNow = sms_index


# 读取上一条信息
def sms_read_last():
  global massageIndexNow
  sms_text_str = sms_read_text()
  sms_index = sms_get_index(sms_text_str)
  if sms_index != -1:
    if massageIndexNow > 1:
      massageIndexNow -= 1
    else:
      massageIndexNow = sms_index
    sms_info_str = sms_get_whole_one(sms_text_str, massageIndexNow)
    sms_parsing(sms_info_str)


# 读取下一条信息
def sms_read_next():
  global massageIndexNow
  sms_text_str = sms_read_text()
  sms_index = sms_get_index(sms_text_str)
  if sms_index != -1:
    if massageIndexNow < sms_index:
      massageIndexNow += 1
    else:
      massageIndexNow = 1
    sms_info_str = sms_get_whole_one(sms_text_str, massageIndexNow)
    sms_parsing(sms_info_str)


# 删除所有短信
def sms_delect_all():
  global massageDevStatus
  if massageDevStatus == False:
    return False
  uart.write("AT+CMGD=1,4\r\n".encode())
  tm.sleep(0.1)                                               # Waitting for about 100ms
  uart_rx_len = uart.in_waiting                               # Read the buffer in recived buffer
  uart_rx_str = str(uart.read(uart_rx_len))
  if uart_rx_str.find('OK'):                                  # If the device respose character "OK"
    return True


# 读取信息
def sms_read_text():
  uart.write("AT+CMGF=1\r\n".encode())
  tm.sleep(0.1)                                               # Waitting for about 100ms
  uart_rx_len = uart.in_waiting                               # Read the buffer in recived buffer
  uart_rx_str = str(uart.read(uart_rx_len))
  if uart_rx_str.find('OK') == -1:
    return ""
  uart.write("AT+CMGL=\"ALL\",0\r\n".encode())                # Read all sms
  for i in range(0, 200, 1):
    tm.sleep(0.1)                                             # Waitting for about 1s
    if uart_rx_len != uart.in_waiting:                        # Read the buffer in recived buffer
      uart_rx_len = uart.in_waiting
    else:
      break
  uart_rx_str = str(uart.read(uart_rx_len))
  return uart_rx_str


# 获取信息条数
def sms_get_index(sms_str):
  sms_index_pos = sms_str.rfind("+CMGL: ", 0, len(sms_str))
  if sms_index_pos != -1:
    sms_index = int(sms_str[sms_index_pos + 7:sms_index_pos + 8])
  else:
    sms_index = -1
  return sms_index


# 获取一条信息
def sms_get_whole_one(sms_str, sms_index):
  sms_one_start = findSubStr("+CMGL: ", sms_str, sms_index)
  sms_one_str = sms_str[sms_one_start: len(sms_str)]
  sms_one_end = findSubStr("\\r\\n", sms_one_str, 3)-2
  sms_one_str = sms_one_str[0: sms_one_end]
  return sms_one_str


# 信号强度更新
def rssi_update():
  global massageDevStatus
  uart.write("AT+CSQ\r\n".encode())
  tm.sleep(0.1)                                               # Waitting for about 10ms
  uart_rx_len = uart.in_waiting                               # Read the buffer in recived buffer
  uart_rx_str = str(uart.read(uart_rx_len))
  rssi_index = uart_rx_str.rfind("+CSQ: ", 0, len(uart_rx_str))
  if rssi_index != -1:
    rssi_index += 6
    rssi_str = uart_rx_str[rssi_index:rssi_index+2]
    rssi_old_str = device_rssi_entry.get()
    if rssi_str != rssi_old_str:
      device_rssi_entry.delete(0, tk.END)
      device_rssi_entry.insert(0, rssi_str)
      device_status_entry.delete(0, tk.END)
      device_status_entry.insert(0, "设备已连接")
  else:
    massageDevStatus = False

def sms_update():
  uart_rx_len = uart.in_waiting  # Read the buffer in recived buffer
  if uart_rx_len == 0:
    return
  uart_rx_str = str(uart.read(uart_rx_len))
  sms_index = uart_rx_str.rfind("+CMTI: \"SM\"", 0, len(uart_rx_str))
  if sms_index != -1:
    sms_read_new()
    sms_titile = phone_number_entry.get()
    sms_content = massage_time_entry.get() + "\r\n" +massage_text.get("1.0", tk.END)
    # 使用了SERVER酱的微信推送可以去 http://sc.ftqq.com/ 注册自己的SCKEY 替换下面的"SCKEY"
    #rqst.get("https://sc.ftqq.com/SCKEY.send?text={}&desp={}".format(sms_titile, sms_content))


# 设备正常工作处理
def device_process():
  global massageProcess
  global uart
  global uart_rx_str
  global sms_index
  global massage_text
  global sms_text_str
  global rssi_update_cnt
  if massageProcess == "DELECT SMS ALL":
    massage_text.delete(1.0, tk.END)
    phone_number_entry.delete(0, tk.END)
    massage_time_entry.delete(0, tk.END)
    sms_delect_all()
    massageProcess = ""
  elif massageProcess == "READ SMS NEW":
    sms_read_new()
    massageProcess = ""
  elif massageProcess == "READ SMS last":
    sms_read_last()
    massageProcess = ""
  elif massageProcess == "READ SMS next":
    sms_read_next()
    massageProcess = ""
  else:
    sms_update()
    # rssi_update_cnt += 1
    # if rssi_update_cnt > 50:                                  # Update every 5S
    #   rssi_update_cnt = 0
    #   rssi_update()


# 串口进程
def device_threading_process():
  global rssi_update_cnt
  rssi_update_cnt = 50
  while True:
    tm.sleep(0.1)
    if massageDevStatus == False:
      device_searching()
    else:
      device_process()


# 建立并运行串口进程
def device_threading_start():
  uart_threading = th.Thread(target=device_threading_process)
  uart_threading.setDaemon(True)
  uart_threading.start()


# 窗口
def thread_it(func, *args):
  # '''将函数打包进线程'''
  # 创建
  t = th.Thread(target=func, args=args)
  # 守护 !!!
  t.setDaemon(True)
  # 启动
  t.start()
  # 阻塞--卡死界面！
  # t.join()


# 按键“最新”所有处理
def msg_new_bt_press():
  global massageProcess
  massageProcess = "READ SMS NEW"


# 按键“上一个”所有处理
def msg_last_bt_press():
  global massageProcess
  massageProcess = "READ SMS last"


# 按键“下一个”处理
def msg_next_bt_press():
  global massageProcess
  massageProcess = "READ SMS next"


# 按键删除所有处理
def msg_delect_all_bt_press():
  global massageProcess
  massageProcess = "DELECT SMS ALL"


# 窗口初始化
def window_init():
  global window
  global massage_text
  global device_status_entry
  global phone_number_entry
  global device_rssi_entry
  global massage_time_entry
  # 窗口
  window = tk.Tk()
  window.title('短信')
  window.geometry('400x220')  # 设定窗口的大小(长 * 宽)
  # 状态
  device_status_lable = tk.Label(window, text="设备状态")
  device_status_entry = tk.Entry(window, show=None, font=('Arial', 10))
  device_status_entry.insert(0, "设备未连接")
  # 信号强度
  device_rssi_lable = tk.Label(window, text="信号强度")
  device_rssi_entry = tk.Entry(window, show=None, font=('Arial', 10))
  device_rssi_entry.insert(0, "0")
  # 电话号码
  phpne_number_lable = tk.Label(window, text="电话号码")
  phone_number_entry = tk.Entry(window, show=None, font=('Arial', 10))
  massage_time_lable = tk.Label(window, text="时间")
  massage_time_entry = tk.Entry(window, show=None, font=('Arial', 10))
  # 短信内容
  massage_lable = tk.Label(window, text="短信内容")
  massage_scroll = tk.Scrollbar()
  massage_text = tk.Text()
  massage_scroll.config(command=massage_text.yview)
  massage_text.config(yscrollcommand=massage_scroll.set)
  # 最新按钮
  new_msg_bt = tk.Button(window, text="最新", command=lambda: thread_it(msg_new_bt_press))
  # 上一条按钮
  msg_last_bt = tk.Button(window, text="上一条", command=lambda: thread_it(msg_last_bt_press))
  # 下一条按钮
  msg_next_bt = tk.Button(window, text="下一条", command=lambda: thread_it(msg_next_bt_press))
  # 删除所有按钮
  msg_delect_all_bt = tk.Button(window, text="删除所有", command=lambda: thread_it(msg_delect_all_bt_press))
  ##########################################################
  # 界面布局
  # 设备状态
  device_status_lable.place(x=10, y=10, width=50, height=15)
  device_status_entry.place(x=70, y=10, width=80, height=15)
  # 信号强度
  # device_rssi_lable.place(x=250, y=10, width=50, height=15)
  # device_rssi_entry.place(x=310, y=10, width=50, height=15)
  # 电话号码
  phpne_number_lable.place(x=10, y=30, width=50, height=15)
  phone_number_entry.place(x=70, y=30, width=110, height=15)
  # 时间
  massage_time_lable.place(x=210, y=30, width=30, height=15)
  massage_time_entry.place(x=250, y=30, width=110, height=15)
  # 信息
  massage_lable.place(x=10, y=50, width=50, height=15)
  massage_text.place(x=70, y=50, width=300, height=100)
  massage_scroll.place(x=370, y=50, width=15, height=100)
  # 按钮
  new_msg_bt.place(x=0+70, y=170, width=50, height=20)
  msg_last_bt.place(x=60+70, y=170, width=50, height=20)
  msg_next_bt.place(x=120+70, y=170, width=50, height=20)
  msg_delect_all_bt.place(x=180+70, y=170, width=60, height=20)


def window_start():
  window.mainloop()  # 主窗口循环显示


########################################################################################################################
########################################################################################################################
window_init()             # Initalize the massage window
device_threading_start()  # Start the threading of the massage device
window_start()            # Start the massage window
