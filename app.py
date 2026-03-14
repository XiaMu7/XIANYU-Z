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

APP_KEY = "12574478"
BASE_URL = "https://acs.m.goofish.com/h5/mtop.idle.wx.user.profile.update/1.0/"
UPLOAD_URL = "https://stream-upload.goofish.com/api/upload.api"

st.set_page_config(page_title="闲鱼头像助手", page_icon="🐟")

def calc_sign(token: str, t: str, app_key: str, data_str: str) -> str:
    raw = f"{token}&{t}&{app_key}&{data_str}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()

def original_extract_logic(request_text: str):
    """移植原脚本的 extract_from_request 核心逻辑"""
    info = {
        "cookies": {},
        "headers": {},
        "params": {},
        "data": {},
        "utdid": None,
        "m_h5_tk": ""
    }
    
    lines = request_text.strip().split('\n')
    if not lines: return info

    # 1. 解析第一行获取 URL 参数 (jsv, appKey 等)
    first_line = lines[0]
    url_match = re.search(r'\?(.*?)(?:\s|$)', first_line)
    if url_match:
        params_str = url_match.group(1)
        params = parse_qs(params_str)
        for k, v in params.items():
            info["params"][k] = v[0] if v else ""

    # 2. 解析 Headers
    for line in lines[1:]:
        line = line.strip()
        if ': ' in line:
            key, value = line.split(': ', 1)
            key_lower = key.lower()
            info["headers"][key_lower] = value # 统一存为小写 key 方便后续调用
            
            # 处理 Cookie 字符串提取 _m_h5_tk
            if key_lower == 'cookie':
                tk_match = re.search(r'_m_h5_tk=([a-z0-9_]+)', value)
                if tk_match: info["m_h5_tk"] = tk_match.group(1)

            # 深度解析 x-smallstc
            if key_lower == 'x-smallstc':
                try:
                    smallstc = json.loads(value)
                    target_keys = ['cookie2', 'sgcookie', 'csg', 'unb', 'munb', 'sid']
                    for tk in target_keys:
                        if tk in smallstc:
                            info["cookies"][tk] = str(smallstc[tk])
                except: pass

    # 3. 解析 Data (提取 utdid)
    # 查找以 data= 开头的行
    data_line = None
    for line in reversed(lines):
        if line.strip().startswith('data='):
            data_line = line.strip()
            break
    
    if data_line:
        data_str = data_line[5:] # 去掉 "data="
        data_str = urllib.parse.unquote(data_str)
        try:
            info["data"] = json.loads(data_str)
            info["utdid"] = info["data"].get("utdid")
        except:
            # 正则备选方案
            utdid_match = re.search(r'utdid[":]+([^"]+)', data_str)
            if utdid_match: info["utdid"] = utdid_match.group(1)

    return info

def run_task(img_url, auth_info):
    session = requests.Session()
    session.verify = False
    
    # 下载图片
    try:
        img_res = session.get(img_url, timeout=20)
        img_res.raise_for_status()
    except Exception as e:
        st.error(f"图片下载失败: {e}")
        return

    # 上传图片
    st.info("正在上传图片至闲鱼服务器...")
    files = {'file': ('avatar.jpg', img_res.content, 'image/jpeg')}
    up_payload = {"appkey": "fleamarket", "bizCode": "fleamarket", "floderId": "0", "name": "fileFromAlbum"}
    
    # 继承原始 Header 进行上传
    up_headers = {
        "User-Agent": auth_info["headers"].get("user-agent", ""),
        "Referer": "https://servicewechat.com/"
    }
    
    up_res = session.post(UPLOAD_URL, data=up_payload, files=files, headers=up_headers)
    up_json = up_res.json()
    
    xianyu_img_url = up_json.get("object", {}).get("url")
    if not xianyu_img_url:
        st.error(f"上传失败，请检查数据有效性: {up_json}")
        return

    # 更新头像
    st.info(f"上传成功！获得链接: {xianyu_img_url}")
    t = str(int(time.time() * 1000))
    token = auth_info["m_h5_tk"].split('_')[0] if '_' in auth_info["m_h5_tk"] else ""
    
    profile_data = {
        "utdid": auth_info["utdid"],
        "platform": "windows",
        "miniAppVersion": "9.9.9",
        "profileCode": "avatar",
        "profileImageUrl": xianyu_img_url
    }
    data_json = json.dumps(profile_data, separators=(",", ":"), ensure_ascii=False)
    sign = calc_sign(token, t, APP_KEY, data_json)
    
    params = {
        "jsv": "2.4.12", "appKey": APP_KEY, "t": t, "sign": sign,
        "v": "1.0", "type": "originaljson", "accountSite": "xianyu",
        "dataType": "json", "api": "mtop.idle.wx.user.profile.update"
    }
    
    update_headers = {
        "content-type": "application/x-www-form-urlencoded",
        "user-agent": auth_info["headers"].get("user-agent", ""),
        "bx-umidtoken": auth_info["headers"].get("bx-umidtoken", ""),
        "x-ticid": auth_info["headers"].get("x-ticid", ""),
        "mini-janus": auth_info["headers"].get("mini-janus", ""),
    }
    
    resp = session.post(BASE_URL, params=params, headers=update_headers, cookies=auth_info["cookies"], data={"data": data_json})
    return resp.json()

# --- UI 界面 ---
st.title("🐟 闲鱼头像自动更新 (专业版)")
st.caption("使用原脚本解析逻辑，适配 Windows 微信小程序抓包数据")

target_url = st.text_input("1. 输入你想要设置的新头像地址", placeholder="http://xxx.com/a.jpg")
raw_data = st.text_area("2. 粘贴抓包获取的完整 HTTP 请求报文", height=350, help="请确保包含从 POST 第一行直到末尾 data={} 的所有内容")

if st.button("开始执行"):
    if not target_url or not raw_data:
        st.warning("请填入完整信息")
    else:
        info = original_extract_logic(raw_data)
        
        # 调试信息展示（仅在报错时检查）
        if not info["utdid"] or not info["m_h5_tk"]:
            st.error("解析失败！未能找到关键参数。")
            with st.expander("点击查看解析出的数据状态"):
                st.write("utdid:", info["utdid"])
                st.write("_m_h5_tk:", info["m_h5_tk"])
                st.write("Headers数量:", len(info["headers"]))
        else:
            with st.spinner("程序运行中..."):
                final_res = run_task(target_url, info)
                if final_res:
                    st.divider()
                    st.json(final_res)
                    if "SUCCESS" in str(final_res.get("ret", "")):
                        st.balloons()
                        st.success("头像更新成功！请刷新闲鱼查看。")
