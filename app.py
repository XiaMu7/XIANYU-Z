import streamlit as st
import hashlib
import json
import time
import re
import urllib.parse
from urllib.parse import urlparse, urlencode, parse_qs
import requests
import urllib3

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ===== 初始的 _m_h5_tk (直接沿用原脚本预设) =====
if 'm_h5_tk' not in st.session_state:
    st.session_state.m_h5_tk = "717336018584e9c7c54f266f5db96fca_1772912434028"

APP_KEY = "12574478"
BASE_URL = "https://acs.m.goofish.com/h5/mtop.idle.wx.user.profile.update/1.0/"
UPLOAD_URL = "https://stream-upload.goofish.com/api/upload.api"

def calc_sign(token: str, t: str, app_key: str, data_str: str) -> str:
    raw = f"{token}&{t}&{app_key}&{data_str}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()

def extract_from_request_original(request_text: str):
    """完全复刻原脚本的 extract_from_request 函数"""
    info = {
        "cookies": {},
        "headers": {},
        "params": {},
        "data": {},
        "utdid": None,
        "token": st.session_state.m_h5_tk.split('_')[0] if '_' in st.session_state.m_h5_tk else st.session_state.m_h5_tk,
        "m_h5_tk": st.session_state.m_h5_tk,
    }
    
    lines = request_text.strip().split('\n')
    if not lines: return info

    # 解析第一行获取URL参数
    first_line = lines[0]
    url_match = re.search(r'\?(.*?)(?:\s|$)', first_line)
    if url_match:
        params_str = url_match.group(1)
        params = parse_qs(params_str)
        for k, v in params.items():
            info["params"][k] = v[0] if v else ""
    
    # 解析headers
    for line in lines[1:]:
        line = line.strip()
        if ': ' in line:
            key, value = line.split(': ', 1)
            key_lower = key.lower()
            info["headers"][key_lower] = value
            
            if key_lower == 'x-smallstc':
                try:
                    smallstc = json.loads(value)
                    for k in ['cookie2', 'sgcookie', 'csg', 'unb', 'munb', 'sid']:
                        if k in smallstc: info["cookies"][k] = str(smallstc[k])
                except: pass

    # 解析data部分
    data_line = None
    for line in reversed(lines):
        if line.strip().startswith('data='):
            data_line = line.strip()
            break
    
    if data_line:
        data_str = urllib.parse.unquote(data_line[5:])
        try:
            info["data"] = json.loads(data_str)
            info["utdid"] = info["data"].get("utdid")
        except:
            utdid_match = re.search(r'utdid[":]+([^"]+)', data_str)
            if utdid_match: info["utdid"] = utdid_match.group(1)
            
    return info

def update_avatar_with_retry(image_url: str, auth_info: dict, retry_count: int = 0):
    """完全复刻原脚本的 update_avatar 逻辑（含自动更新 token 和重试）"""
    m_h5_tk = st.session_state.m_h5_tk
    token = m_h5_tk.split('_')[0] if '_' in m_h5_tk else m_h5_tk
    
    cookies = auth_info.get("cookies", {}).copy()
    cookies["_m_h5_tk"] = m_h5_tk
    cookies["_m_h5_tk_enc"] = "927a61b5898abf557861458d0ea06b6f"

    data_obj = {
        "utdid": auth_info.get("utdid"),
        "platform": "windows",
        "miniAppVersion": "9.9.9",
        "profileCode": "avatar",
        "profileImageUrl": image_url,
    }
    data_str = json.dumps(data_obj, separators=(",", ":"), ensure_ascii=False)
    t = str(int(time.time() * 1000))
    sign = calc_sign(token, t, APP_KEY, data_str)

    params = {
        "jsv": "2.4.12", "appKey": APP_KEY, "t": t, "sign": sign,
        "v": "1.0", "type": "originaljson", "accountSite": "xianyu",
        "dataType": "json", "timeout": "20000", "api": "mtop.idle.wx.user.profile.update", "_bx-m": "1",
    }

    headers = {
        "User-Agent": auth_info.get("headers", {}).get("user-agent", "Mozilla/5.0"),
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "Referer": "https://servicewechat.com/wx9882f2a891880616/74/page-frame.html",
    }
    # 继承特殊 headers
    for h in ["bx-umidtoken", "x-ticid", "mini-janus", "sgcookie", "bx-ua"]:
        if h in auth_info.get("headers", {}):
            headers[h] = auth_info["headers"][h]

    resp = requests.post(f"{BASE_URL}?{urlencode(params)}", headers=headers, cookies=cookies, data={"data": data_str}, verify=False)
    
    # --- 核心：自动提取并更新 Token ---
    token_updated = False
    if '_m_h5_tk' in resp.cookies:
        new_tk = resp.cookies['_m_h5_tk']
        if new_tk != st.session_state.m_h5_tk:
            st.session_state.m_h5_tk = new_tk
            token_updated = True
            st.write(f"🔄 Token 已过期，自动更新为: {new_tk[:15]}...")

    result = resp.json()
    
    # 自动重试逻辑
    if result.get("ret") and "FAIL_SYS_TOKEN_ILLEGAL" in str(result["ret"]) and retry_count == 0 and token_updated:
        st.write("🔄 检测到新 Token，正在进行第二次重试...")
        return update_avatar_with_retry(image_url, auth_info, retry_count=1)
    
    return result

# --- Streamlit 界面 ---
st.title("🐟 闲鱼头像助手 (原脚本逻辑移植版)")

with st.expander("当前 Token 状态"):
    st.code(st.session_state.m_h5_tk)
    if st.button("重置 Token"):
        del st.session_state.m_h5_tk
        st.rerun()

img_url = st.text_input("1. 目标图片URL", placeholder="http://...")
raw_req = st.text_area("2. 粘贴完整HTTP请求报文", height=300)

if st.button("执行更新"):
    if not img_url or not raw_req:
        st.error("请填入完整信息")
    else:
        info = extract_from_request_original(raw_req)
        if not info["utdid"]:
            st.error("未能解析出 utdid，请检查报文内容")
        else:
            with st.spinner("正在处理..."):
                # 1. 下载并上传（这步是必须的，闲鱼不直接引用外链）
                # 这里简写上传逻辑
                try:
                    # 下载
                    img_data = requests.get(img_url, verify=False).content
                    # 上传
                    files = {'file': ('a.jpg', img_data, 'image/jpeg')}
                    up_res = requests.post(UPLOAD_URL, data={"appkey":"fleamarket","bizCode":"fleamarket"}, files=files, verify=False).json()
                    final_url = up_res.get("object", {}).get("url")
                    
                    if final_url:
                        st.success(f"图片已同步至阿里服务器")
                        # 2. 调用原脚本更新逻辑
                        res = update_avatar_with_retry(final_url, info)
                        st.divider()
                        st.json(res)
                    else:
                        st.error(f"图片同步失败: {up_res}")
                except Exception as e:
                    st.error(f"运行出错: {e}")
