import streamlit as st
import hashlib
import json
import mimetypes
import time
import re
import urllib.parse
from urllib.parse import urlparse, urlencode, parse_qs
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 常量配置
APP_KEY = "12574478"
BASE_URL = "https://acs.m.goofish.com/h5/mtop.idle.wx.user.profile.update/1.0/"
UPLOAD_URL = "https://stream-upload.goofish.com/api/upload.api"

st.set_page_config(page_title="闲鱼头像助手", page_icon="🐟")

def calc_sign(token: str, t: str, app_key: str, data_str: str) -> str:
    raw = f"{token}&{t}&{app_key}&{data_str}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()

def extract_info(request_text: str):
    """解析用户粘贴的原始请求报文"""
    info = {"cookies": {}, "headers": {}, "params": {}, "data": {}, "utdid": None}
    
    lines = request_text.strip().split('\n')
    if not lines: return None

    # 解析Headers
    for line in lines:
        if ': ' in line:
            key, value = line.split(': ', 1)
            info["headers"][key.strip()] = value.strip()
            if key.lower() == 'x-smallstc':
                try:
                    stc = json.loads(value)
                    for k in ['cookie2', 'sgcookie', 'csg', 'unb', 'munb', 'sid']:
                        if k in stc: info["cookies"][k] = str(stc[k])
                except: pass

    # 解析Data (utdid)
    data_match = re.search(r'data=(%7B.*%7D)', request_text)
    if data_match:
        try:
            decoded_data = json.loads(urllib.parse.unquote(data_match.group(1)))
            info["data"] = decoded_data
            info["utdid"] = decoded_data.get("utdid")
        except: pass
    
    # 尝试从Cookie中提取 _m_h5_tk
    cookie_header = info["headers"].get("cookie", "")
    tk_match = re.search(r'_m_h5_tk=([a-z0-9_]+)', cookie_header)
    info["m_h5_tk"] = tk_match.group(1) if tk_match else ""
    
    return info

def process_update(target_img_url, auth_info):
    session = requests.Session()
    session.verify = False
    
    # 1. 下载原始图片
    st.info("正在从目标地址下载图片...")
    img_res = session.get(target_img_url, timeout=15)
    img_res.raise_for_status()
    
    # 2. 上传至闲鱼服务器
    st.info("正在同步至闲鱼图床...")
    files = {'file': ('avatar.jpg', img_res.content, 'image/jpeg')}
    upload_data = {"appkey": "fleamarket", "bizCode": "fleamarket", "floderId": "0"}
    
    up_res = session.post(UPLOAD_URL, data=upload_data, files=files, headers={
        "User-Agent": auth_info["headers"].get("user-agent", ""),
        "Referer": "https://servicewechat.com/"
    })
    
    final_img_url = up_res.json().get("object", {}).get("url")
    if not final_img_url:
        st.error(f"同步失败: {up_res.text}")
        return
    
    st.success(f"同步成功: {final_img_url}")

    # 3. 发送更新头像指令
    st.info("正在更新个人资料...")
    t = str(int(time.time() * 1000))
    token = auth_info["m_h5_tk"].split('_')[0] if '_' in auth_info["m_h5_tk"] else ""
    
    post_data_obj = {
        "utdid": auth_info["utdid"],
        "platform": "windows",
        "miniAppVersion": "9.9.9",
        "profileCode": "avatar",
        "profileImageUrl": final_img_url
    }
    data_str = json.dumps(post_data_obj, separators=(",", ":"))
    sign = calc_sign(token, t, APP_KEY, data_str)
    
    params = {
        "jsv": "2.4.12", "appKey": APP_KEY, "t": t, "sign": sign,
        "v": "1.0", "type": "originaljson", "accountSite": "xianyu",
        "api": "mtop.idle.wx.user.profile.update"
    }
    
    headers = {
        "content-type": "application/x-www-form-urlencoded",
        "user-agent": auth_info["headers"].get("user-agent", ""),
        "bx-umidtoken": auth_info["headers"].get("bx-umidtoken", ""),
        "x-ticid": auth_info["headers"].get("x-ticid", ""),
    }
    
    cookies = auth_info["cookies"]
    cookies["_m_h5_tk"] = auth_info["m_h5_tk"]

    final_res = session.post(BASE_URL, params=params, headers=headers, cookies=cookies, data={"data": data_str})
    return final_res.json()

# Streamlit UI
st.title("🐟 闲鱼头像一键更新工具")
st.markdown("通过微信小程序抓包的数据，快速更新你的闲鱼头像。")

with st.sidebar:
    st.header("使用帮助")
    st.write("1. 在电脑微信打开闲鱼小程序")
    st.write("2. 使用抓包工具获取修改头像的 POST 请求")
    st.write("3. 复制完整的 **Headers** 和 **Data** 粘贴到右侧")

img_input = st.text_input("1. 目标头像图片 URL", placeholder="https://example.com/my_new_avatar.jpg")
raw_request = st.text_area("2. 粘贴完整 HTTP 请求报文 (包含 Headers 和 Data)", height=300)

if st.button("🚀 开始更新"):
    if not img_input or not raw_request:
        st.warning("请填写完整信息")
    else:
        try:
            info = extract_info(raw_request)
            if not info["utdid"] or not info["m_h5_tk"]:
                st.error("无法从请求中解析出 utdid 或 _m_h5_tk，请检查粘贴内容是否完整。")
            else:
                with st.spinner("执行中..."):
                    result = process_update(img_input, info)
                    st.divider()
                    st.json(result)
                    if "SUCCESS" in str(result.get("ret", "")):
                        st.balloons()
                        st.success("头像更新成功！")
        except Exception as e:
            st.error(f"发生错误: {str(e)}")
