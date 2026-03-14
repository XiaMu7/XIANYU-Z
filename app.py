import streamlit as st
import hashlib
import json
import time
import re
import urllib.parse
from urllib.parse import urlencode, parse_qs
import requests
import urllib3

# 基础配置
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
APP_KEY = "12574478"
BASE_URL = "https://acs.m.goofish.com/h5/mtop.idle.wx.user.profile.update/1.0/"
UPLOAD_URL = "https://stream-upload.goofish.com/api/upload.api"

st.set_page_config(page_title="闲鱼头像自动化", page_icon="🐟")

def calc_sign(token: str, t: str, app_key: str, data_str: str) -> str:
    raw = f"{token}&{t}&{app_key}&{data_str}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()

def extract_from_request(request_text: str):
    """复刻原脚本的解析逻辑"""
    info = {"cookies": {}, "headers": {}, "utdid": None}
    lines = request_text.strip().split('\n')
    
    # 1. 提取 Cookies 和 Headers
    for line in lines:
        if ': ' in line:
            key, value = line.split(': ', 1)
            info["headers"][key.lower()] = value.strip()
            if key.lower() == 'x-smallstc':
                try:
                    stc = json.loads(value)
                    for k in ['cookie2', 'sgcookie', 'csg', 'unb', 'munb', 'sid']:
                        if k in stc: info["cookies"][k] = str(stc[k])
                except: pass
    
    # 2. 提取 utdid
    data_line = next((l for l in reversed(lines) if l.startswith('data=')), None)
    if data_line:
        data_str = urllib.parse.unquote(data_line[5:])
        try:
            info["utdid"] = json.loads(data_str).get("utdid")
        except:
            ut_match = re.search(r'utdid[":]+([^"]+)', data_str)
            if ut_match: info["utdid"] = ut_match.group(1)
            
    return info

def run_avatar_update(img_url, auth_info):
    s = requests.Session()
    s.verify = False
    
    # 1. 下载图片内容
    resp = s.get(img_url, timeout=15)
    resp.raise_for_status()
    
    # 2. 上传图片 (使用原脚本参数)
    files = {'file': ('a.jpg', resp.content, 'image/jpeg')}
    up_res = s.post(UPLOAD_URL, files=files, data={
        "appkey": "fleamarket", "bizCode": "fleamarket", 
        "floderId": "0", "name": "fileFromAlbum"
    }, headers={"User-Agent": auth_info["headers"].get("user-agent", "")})
    
    # 【新增】详细报错打印
    if up_res.status_code != 200:
        st.error(f"上传失败 (HTTP {up_res.status_code})")
        st.code(up_res.text[:500]) # 打印原始返回内容，排查错误原因
        return None
    
    up_json = up_res.json()
    final_url = up_json.get("object", {}).get("url")
    if not final_url: return None

    # 3. 更新接口
    t = str(int(time.time() * 1000))
    token = "717336018584e9c7c54f266f5db96fca" # 默认初始Token
    data_obj = {"utdid": auth_info["utdid"], "platform": "windows", "profileCode": "avatar", "profileImageUrl": final_url}
    data_str = json.dumps(data_obj, separators=(",", ":"))
    sign = calc_sign(token, t, APP_KEY, data_str)
    
    params = {"jsv": "2.4.12", "appKey": APP_KEY, "t": t, "sign": sign, "api": "mtop.idle.wx.user.profile.update", "dataType": "json"}
    return s.post(BASE_URL, params=params, headers=auth_info["headers"], cookies=auth_info["cookies"], data={"data": data_str}).json()

# --- 网页界面 ---
st.title("🐟 闲鱼头像自动化更新器")
img_url = st.text_input("图片 URL")
raw_req = st.text_area("粘贴抓包数据", height=300)

if st.button("提交更新"):
    if not img_url or not raw_req:
        st.error("请补充完整")
    else:
        info = extract_from_request(raw_req)
        if not info["utdid"]:
            st.error("utdid 解析失败，请检查数据完整性")
        else:
            with st.spinner("处理中..."):
                res = run_avatar_update(img_url, info)
                if res: st.json(res)
