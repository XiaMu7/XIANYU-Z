import streamlit as st
import hashlib, json, time, re, urllib.parse, requests, urllib3, base64
from urllib.parse import urlparse, urlencode, parse_qs
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 禁用SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
session = requests.Session()
session.verify = False

# --- 全局变量 ---
API = "mtop.idle.wx.user.profile.update"
APP_KEY = "12574478"
BASE_URL = "https://acs.m.goofish.com/h5/mtop.idle.wx.user.profile.update/1.0/"
UPLOAD_URL = "https://stream-upload.goofish.com/api/upload.api"
CURRENT_M_H5_TK = "717336018584e9c7c54f266f5db96fca_1772912434028"

# --- 核心逻辑函数 ---
def calc_sign(token, t, app_key, data_str):
    raw = f"{token}&{t}&{app_key}&{data_str}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()

def extract_from_request(request_text):
    info = {"cookies": {}, "headers": {}, "data": {}, "utdid": None}
    lines = request_text.strip().split('\n')
    for line in lines:
        if ': ' in line:
            key, value = line.split(': ', 1)
            info["headers"][key] = value
            if key.lower() == 'cookie':
                for pair in value.split('; '):
                    if '=' in pair:
                        k, v = pair.split('=', 1)
                        info["cookies"][k] = v
        if line.startswith('data='):
            data_str = urllib.parse.unquote(line[5:])
            try:
                data_obj = json.loads(data_str)
                info["data"] = data_obj
                info["utdid"] = data_obj.get("utdid")
            except: pass
    return info

def update_avatar(image_url, auth_info):
    global CURRENT_M_H5_TK
    cookies = auth_info.get("cookies", {}).copy()
    cookies["_m_h5_tk"] = CURRENT_M_H5_TK
    data_obj = {"utdid": auth_info.get("utdid"), "platform": "mac", "profileCode": "avatar", "profileImageUrl": image_url}
    data_str = json.dumps(data_obj, separators=(",", ":"), ensure_ascii=False)
    t = str(int(time.time() * 1000))
    token = CURRENT_M_H5_TK.split('_')[0]
    sign = calc_sign(token, t, APP_KEY, data_str)
    params = {"jsv": "2.4.12", "appKey": APP_KEY, "t": t, "sign": sign, "v": "1.0", "api": API}
    response = session.post(f"{BASE_URL}?{urlencode(params)}", cookies=cookies, data={"data": data_str}, verify=False)
    return response.json()

def upload_to_xianyu(file_url, auth_info):
    img_resp = requests.get(file_url, verify=False)
    files = {"file": ("avatar.jpg", img_resp.content, "image/jpeg")}
    data = {"appkey": "fleamarket", "bizCode": "fleamarket"}
    response = session.post(UPLOAD_URL, files=files, data=data, cookies=auth_info["cookies"], verify=False)
    return response.json().get("object", {}).get("url")

# --- 网页界面 (恢复到最外层缩进) ---
st.set_page_config(page_title="闲鱼头像助手", page_icon="🐟")
st.title("🐟 闲鱼头像自动更新")

img_url = st.text_input("请输入图片URL:")
req_text = st.text_area("请粘贴完整的HTTP请求信息:", height=200)

if st.button("🚀 开始同步头像"):
    if not img_url or not req_text:
        st.error("请确保输入内容完整！")
    else:
        with st.status("正在处理...", expanded=True) as status:
            try:
                st.write("正在解析认证信息...")
                auth = extract_from_request(req_text)
                st.write("正在上传图片到闲鱼...")
                final_url = upload_to_xianyu(img_url, auth)
                st.write(f"图片已上传: {final_url}")
                st.write("正在调用API更新头像...")
                res = update_avatar(final_url, auth)
                st.json(res)
                if "SUCCESS" in str(res.get("ret", "")):
                    st.success("头像更新成功！")
                    st.balloons()
                else:
                    st.error("更新失败，请检查返回结果")
            except Exception as e:
                st.error(f"发生错误: {str(e)}")