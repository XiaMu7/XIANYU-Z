import streamlit as st
import time
import hashlib
import json
import re
import requests

# 1. 禁用 SSL 警告
requests.packages.urllib3.disable_warnings()

st.title("🐟 闲鱼头像强制更新器")

# 2. 界面输入区
request_text = st.text_area("粘贴抓包的 Raw 请求 (确保包含 x-smallstc 和 data):", height=200)
image_url = st.text_input("输入图片链接:")

# 3. 核心逻辑
if st.button("立即执行"):
    stc_match = re.search(r'x-smallstc: (\{.*?\})', request_text)
    data_match = re.search(r'data=%7B%22utdid%22%3A%22(.*?)%22', request_text)
    
    if not stc_match or not data_match:
        st.error("解析失败：请确保粘贴了包含 x-smallstc 和 data 的完整原始请求。")
    else:
        try:
            stc_data = json.loads(stc_match.group(1))
            cookie2 = stc_data.get("cookie2")
            utdid = data_match.group(1)

            # 签名逻辑
            token = cookie2.split('_')[0]
            t = str(int(time.time() * 1000))
            app_key = "12574478"
            data_str = json.dumps({"utdid": utdid, "profileImageUrl": image_url, "profileCode": "avatar", "platform": "windows"}, separators=(",", ":"))
            sign = hashlib.md5(f"{token}&{t}&{app_key}&{data_str}".encode()).hexdigest()

            url = f"https://acs.m.goofish.com/h5/mtop.idle.wx.user.profile.update/1.0/?jsv=2.4.12&appKey={app_key}&t={t}&sign={sign}&api=mtop.idle.wx.user.profile.update&v=1.0&dataType=json"
            
            cookies = {"cookie2": cookie2, "_m_h5_tk": token}
            headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://servicewechat.com/"}
            
            res = requests.post(url, data={"data": data_str}, cookies=cookies, headers=headers, verify=False)
            st.write("服务器返回结果:", res.json())
        except Exception as e:
            st.error(f"处理发生错误: {str(e)}")
