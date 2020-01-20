# SIM800C_MASSAGE
使用SIM800C模块做的短信接收程序，可以解析中文短信。
微信推送使用了SERVER酱的微信推送，具体操作参考http://sc.ftqq.com/3.version。
在代码中 rqst.get("https://sc.ftqq.com/SCKEY.send?text={}&desp={}".format(sms_titile, sms_content)) 替换"SCKEY"成自己的并将注释去掉即可。
