# streamlit_xianyu_avatar.py
import streamlit as st
import hashlib
import json
import mimetypes
import time
import re
import urllib.parse
from pathlib import Path
from urllib.parse import urlparse, urlencode, parse_qs
import os
import base64
from typing import Optional, Tuple, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 常量定义
API = "mtop.idle.wx.user.profile.update"
APP_KEY = "12574478"
BASE_URL = "https://acs.m.goofish.com/h5/mtop.idle.wx.user.profile.update/1.0/"
UPLOAD_URL = "https://stream-upload.goofish.com/api/upload.api"

# 页面配置
st.set_page_config(
    page_title="闲鱼头像自动更新工具",
    page_icon="🖼️",
    layout="centered"
)

# 初始化session状态
if 'session' not in st.session_state:
    st.session_state.session = requests.Session()
    st.session_state.session.verify = False
    # 配置重试策略
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    st.session_state.session.mount("http://", adapter)
    st.session_state.session.mount("https://", adapter)

if 'current_m_h5_tk' not in st.session_state:
    st.session_state.current_m_h5_tk = "717336018584e9c7c54f266f5db96fca_1772912434028"

if 'auth_info' not in st.session_state:
    st.session_state.auth_info = {
        "cookies": {},
        "headers": {},
        "params": {},
        "data": {},
        "utdid": None,
        "token": None,
        "m_h5_tk": None
    }

def create_session_with_retries() -> requests.Session:
    """创建支持重试的会话"""
    session = requests.Session()
    session.verify = False
    retry = Retry(
        total=3,
        read=3,
        connect=3,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def check_url_accessibility(url: str, timeout: int = 10) -> Tuple[bool, int, str]:
    """快速检查URL的可访问性"""
    try:
        response = requests.head(url, timeout=timeout, allow_redirects=True, verify=False)
        return True, response.status_code, response.reason
    except Exception as e:
        return False, 0, str(e)

def extract_auth_from_url(url: str) -> Dict[str, str]:
    """从URL中提取可能的认证信息"""
    auth_info = {}
    parsed = urlparse(url)
    
    if parsed.username and parsed.password:
        auth_info['username'] = parsed.username
        auth_info['password'] = parsed.password
        auth_str = f"{parsed.username}:{parsed.password}"
        auth_info['basic_auth'] = base64.b64encode(auth_str.encode()).decode()
    
    return auth_info

def handle_401_with_auth(url: str, timeout: int = 30) -> Optional[Tuple[bytes, str, str]]:
    """专门处理401错误的函数"""
    st.warning("🔄 检测到401授权错误，尝试使用认证信息...")
    
    parsed_url = urlparse(url)
    file_name = os.path.basename(parsed_url.path)
    if not file_name or '.' not in file_name:
        file_name = f"image_{int(time.time())}.jpg"
    
    # 在Streamlit中通过界面选择认证方式
    auth_method = st.radio(
        "选择认证方式",
        ["Bearer Token", "Cookie", "Referer", "跳过认证"],
        key="auth_method"
    )
    
    auth_attempts = []
    
    if auth_method == "Bearer Token":
        token = st.text_input("请输入Bearer Token", type="password", key="bearer_token")
        if token:
            auth_attempts.append({
                'name': 'Bearer Token',
                'headers': {
                    'Authorization': f"Bearer {token}",
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            })
    
    elif auth_method == "Cookie":
        cookie_str = st.text_area("请输入Cookie (key=value; key2=value2)", key="cookie_str")
        if cookie_str:
            auth_attempts.append({
                'name': 'Cookie Auth',
                'headers': {
                    'Cookie': cookie_str,
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            })
    
    elif auth_method == "Referer":
        common_referers = [
            f"https://{parsed_url.netloc}/",
            "https://www.google.com/",
            "https://www.baidu.com/",
        ]
        for referer in common_referers:
            auth_attempts.append({
                'name': f'Referer: {referer}',
                'headers': {
                    'Referer': referer,
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            })
    
    if auth_method == "跳过认证" or not auth_attempts:
        return None
    
    # 尝试所有认证方式
    download_session = create_session_with_retries()
    
    for attempt in auth_attempts:
        try:
            st.info(f"尝试认证方式: {attempt['name']}")
            
            response = download_session.get(
                url,
                timeout=timeout,
                verify=False,
                headers=attempt['headers'],
                allow_redirects=True
            )
            
            if response.status_code == 200:
                content = response.content
                if len(content) > 0:
                    content_type = response.headers.get('Content-Type', '')
                    mime = content_type.split(';')[0].strip()
                    if not mime or mime == 'application/octet-stream':
                        guessed = mimetypes.guess_type(file_name)[0]
                        mime = guessed or 'image/jpeg'
                    
                    st.success(f"✅ 认证成功！使用 {attempt['name']}")
                    st.info(f"文件大小: {len(content)} bytes")
                    st.info(f"MIME类型: {mime}")
                    
                    return content, file_name, mime
            else:
                st.error(f"❌ 失败: HTTP {response.status_code}")
                
        except Exception as e:
            st.error(f"❌ 失败: {str(e)[:100]}")
            continue
    
    return None

def download_image_with_fallback(url: str, timeout: int = 30) -> Tuple[bytes, str, str]:
    """下载图片，支持多种URL类型和SSL降级策略"""
    with st.spinner("正在处理图片URL..."):
        st.info(f"开始处理图片URL: {url}")
        
        # 首先检查URL是否可访问
        st.info("检查URL可访问性...")
        accessible, status_code, reason = check_url_accessibility(url)
        
        if status_code == 401:
            st.warning(f"⚠️ URL返回 401 Authorization Required")
            auth_result = handle_401_with_auth(url, timeout)
            if auth_result:
                return auth_result
        
        # 创建临时会话
        download_session = create_session_with_retries()
        
        # 常见的浏览器User-Agent
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
        ]
        
        # 解析URL
        parsed_url = urlparse(url)
        file_name = os.path.basename(parsed_url.path)
        if not file_name or '.' not in file_name:
            file_name = f"image_{int(time.time())}.jpg"
        
        # 尝试不同的下载策略
        strategies = [
            {"verify": True, "headers": {"User-Agent": user_agents[0]}, "name": "标准验证"},
            {"verify": False, "headers": {"User-Agent": user_agents[0]}, "name": "跳过SSL"},
            {"verify": False, "headers": {"User-Agent": user_agents[2]}, "name": "移动端UA"},
            {"verify": False, "headers": {
                "User-Agent": user_agents[0],
                "Referer": f"https://{parsed_url.netloc}/"
            }, "name": "添加Referer"},
            {"verify": False, "headers": {
                "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36 MicroMessenger/7.0.18",
                "Referer": "https://servicewechat.com/"
            }, "name": "微信UA"},
        ]
        
        progress_bar = st.progress(0)
        for i, strategy in enumerate(strategies, 1):
            try:
                progress_bar.progress(i / len(strategies))
                st.info(f"尝试下载策略 {i}/{len(strategies)}: {strategy['name']}")
                
                headers = strategy["headers"].copy()
                
                response = download_session.get(
                    url,
                    timeout=timeout,
                    verify=strategy["verify"],
                    headers=headers,
                    allow_redirects=True,
                    stream=True
                )
                
                if response.status_code == 401:
                    st.warning(f"⚠️ 返回 401 需要授权，尝试其他策略...")
                    continue
                    
                response.raise_for_status()
                
                # 检查内容类型
                content_type = response.headers.get('Content-Type', '').lower()
                if content_type and not any(img_type in content_type for img_type in ['image/', 'application/octet-stream']):
                    st.warning(f"⚠️ 警告: 可能不是图片文件 (Content-Type: {content_type})")
                
                # 读取内容
                content = response.content
                
                if len(content) == 0:
                    st.warning(f"⚠️ 下载的文件为空")
                    continue
                
                # 获取MIME类型
                mime = content_type.split(';')[0].strip()
                if not mime or mime == 'application/octet-stream':
                    guessed = mimetypes.guess_type(file_name)[0]
                    if guessed:
                        mime = guessed
                    else:
                        mime = 'image/jpeg' if file_name.lower().endswith(('.jpg', '.jpeg')) else 'image/png'
                
                st.success(f"✅ 下载成功 (策略 {i})")
                st.info(f"文件大小: {len(content)} bytes")
                st.info(f"MIME类型: {mime}")
                st.info(f"文件名: {file_name}")
                
                progress_bar.empty()
                return content, file_name, mime
                
            except Exception as e:
                st.error(f"❌ 错误: {str(e)[:100]}...")
                continue
        
        progress_bar.empty()
        
        # 所有策略都失败
        error_msg = "所有下载策略都失败"
        st.error(f"❌ {error_msg}")
        raise RuntimeError(error_msg)

def extract_from_request(request_text: str) -> dict:
    """从HTTP请求文本中提取所有必要信息"""
    info = {
        "cookies": {},
        "headers": {},
        "params": {},
        "data": {},
        "utdid": None,
        "token": st.session_state.current_m_h5_tk.split('_')[0] if '_' in st.session_state.current_m_h5_tk else st.session_state.current_m_h5_tk,
        "m_h5_tk": st.session_state.current_m_h5_tk,
    }
    
    lines = request_text.strip().split('\n')
    
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
        if not line or line.startswith('{') or line.startswith('h2'):
            continue
            
        if ': ' in line:
            key, value = line.split(': ', 1)
            key_lower = key.lower()
            
            info["headers"][key] = value
            
            # 特殊header处理
            if key_lower == 'x-smallstc':
                try:
                    smallstc = json.loads(value)
                    
                    if 'cookie2' in smallstc:
                        info["cookies"]['cookie2'] = str(smallstc['cookie2'])
                    if 'sgcookie' in smallstc:
                        info["cookies"]['sgcookie'] = str(smallstc['sgcookie'])
                        info["headers"]['sgcookie'] = str(smallstc['sgcookie'])
                    if 'csg' in smallstc:
                        info["cookies"]['csg'] = str(smallstc['csg'])
                    if 'unb' in smallstc:
                        info["cookies"]['unb'] = str(smallstc['unb'])
                    if 'munb' in smallstc:
                        info["cookies"]['munb'] = str(smallstc['munb'])
                    if 'sid' in smallstc:
                        info["cookies"]['sid'] = str(smallstc['sid'])
                        
                except json.JSONDecodeError:
                    pass
    
    # 解析data部分
    data_line = None
    for line in reversed(lines):
        if line.strip().startswith('data='):
            data_line = line.strip()
            break
    
    if data_line:
        data_str = data_line[5:]
        data_str = urllib.parse.unquote(data_str)
        try:
            info["data"] = json.loads(data_str)
            info["utdid"] = info["data"].get("utdid")
            st.info(f"从data提取的utdid: {info['utdid']}")
        except json.JSONDecodeError:
            utdid_match = re.search(r'utdid[":]+([^"]+)', data_str)
            if utdid_match:
                info["utdid"] = utdid_match.group(1)
                st.info(f"从data正则提取的utdid: {info['utdid']}")
    
    return info

def calc_sign(token: str, t: str, app_key: str, data_str: str) -> str:
    """计算签名"""
    raw = f"{token}&{t}&{app_key}&{data_str}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()

def update_avatar(image_url: str, auth_info: dict, retry_count: int = 0) -> dict:
    """更新头像"""
    # 构建cookies
    cookies = auth_info.get("cookies", {}).copy()
    
    # 使用当前的 _m_h5_tk
    m_h5_tk = st.session_state.current_m_h5_tk
    token = m_h5_tk.split('_')[0] if '_' in m_h5_tk else m_h5_tk
    
    # 添加到cookies
    cookies["_m_h5_tk"] = m_h5_tk
    cookies["_m_h5_tk_enc"] = "927a61b5898abf557861458d0ea06b6f"
    
    # 获取utdid
    utdid = auth_info.get("utdid")
    if not utdid:
        raise ValueError("Missing utdid")

    data_obj = {
        "utdid": utdid,
        "platform": "mac",
        "miniAppVersion": "9.9.9",
        "profileCode": "avatar",
        "profileImageUrl": image_url,
    }
    data_str = json.dumps(data_obj, separators=(",", ":"), ensure_ascii=False)

    t = str(int(time.time() * 1000))
    sign = calc_sign(token, t, APP_KEY, data_str)

    params = {
        "jsv": "2.4.12",
        "appKey": APP_KEY,
        "t": t,
        "sign": sign,
        "v": "1.0",
        "type": "originaljson",
        "accountSite": "xianyu",
        "dataType": "json",
        "timeout": "20000",
        "api": API,
        "_bx-m": "1",
    }

    # 合并headers
    headers = {
        "User-Agent": auth_info.get("headers", {}).get("user-agent", 
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/126.0.0.0"
        ),
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "Referer": "https://servicewechat.com/wx9882f2a891880616/74/page-frame.html",
    }
    
    # 添加特殊headers
    special_headers = ["bx-umidtoken", "x-ticid", "x-tap", "mini-janus", "sgcookie", "bx-ua"]
    for h in special_headers:
        if h in auth_info.get("headers", {}):
            headers[h] = auth_info["headers"][h]

    st.info(f"发送请求到: {BASE_URL}")
    st.info(f"使用的token: {token}")

    # 发送请求
    response = st.session_state.session.post(
        f"{BASE_URL}?{urlencode(params)}",
        headers=headers,
        cookies=cookies,
        data={"data": data_str},
        timeout=20,
        verify=False
    )
    
    st.info(f"响应状态码: {response.status_code}")
    
    # 自动提取新的 _m_h5_tk
    token_updated = False
    if '_m_h5_tk' in response.cookies:
        new_m_h5_tk = response.cookies['_m_h5_tk']
        if new_m_h5_tk != st.session_state.current_m_h5_tk:
            st.success(f"发现新的 _m_h5_tk: {new_m_h5_tk}")
            st.success(f"自动更新当前token")
            st.session_state.current_m_h5_tk = new_m_h5_tk
            auth_info['m_h5_tk'] = new_m_h5_tk
            auth_info['token'] = new_m_h5_tk.split('_')[0] if '_' in new_m_h5_tk else new_m_h5_tk
            token_updated = True
    
    result = response.json()
    
    # 如果返回非法令牌且没有重试过，并且token被更新了，则自动重试一次
    if result.get("ret") and "FAIL_SYS_TOKEN_ILLEGAL" in str(result["ret"]) and retry_count == 0 and token_updated:
        st.warning("🔄 检测到新token，自动重试一次...")
        time.sleep(1)
        return update_avatar(image_url, auth_info, retry_count=1)
    
    return result

def upload_bytes(file_name: str, file_bytes: bytes, mime: str, auth_info: dict) -> str:
    """上传文件到闲鱼服务器"""
    cookies = auth_info.get("cookies", {}).copy()
    
    # 使用最新的 _m_h5_tk
    cookies["_m_h5_tk"] = st.session_state.current_m_h5_tk
    
    files = {
        "file": (file_name, file_bytes, mime),
    }
    data = {
        "content-type": "multipart/form-data",
        "appkey": "fleamarket",
        "bizCode": "fleamarket",
        "floderId": "0",
        "name": "fileFromAlbum",
    }
    params = {
        "floderId": "0",
        "appkey": "fleamarket",
        "_input_charset": "utf-8",
    }
    
    headers = {
        "User-Agent": auth_info.get("headers", {}).get("user-agent",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/126.0.0.0"
        ),
        "Accept": "*/*",
        "Referer": "https://servicewechat.com/wx9882f2a891880616/74/page-frame.html",
    }
    
    # 添加必要的headers
    for h in ["bx-umidtoken", "x-ticid", "mini-janus", "sgcookie"]:
        if h in auth_info.get("headers", {}):
            headers[h] = auth_info["headers"][h]

    st.info(f"上传文件到: {UPLOAD_URL}")
    
    response = st.session_state.session.post(
        UPLOAD_URL,
        params=params,
        headers=headers,
        cookies=cookies,
        data=data,
        files=files,
        timeout=30,
        verify=False
    )
    response.raise_for_status()
    body = response.json()
    if not body.get("success"):
        raise RuntimeError(f"Upload failed: {body}")
    image_url = body.get("object", {}).get("url")
    if not image_url:
        raise RuntimeError(f"Upload response missing object.url: {body}")
    return image_url

def upload_from_url(file_url: str, auth_info: dict) -> str:
    """从URL下载图片并上传到闲鱼"""
    st.info(f"开始处理图片URL: {file_url}")
    
    try:
        content, file_name, mime = download_image_with_fallback(file_url)
        
        st.info("开始上传到闲鱼服务器...")
        final_url = upload_bytes(file_name, content, mime, auth_info)
        st.success(f"✅ 上传成功！")
        st.info(f"最终URL: {final_url}")
        
        return final_url
        
    except Exception as e:
        st.error(f"❌ 图片处理失败: {e}")
        raise

def main():
    st.title("🖼️ 闲鱼头像自动更新工具")
    st.markdown("---")
    
    # 步骤1：输入图片URL
    st.header("第一步：请输入要设置为头像的图片URL")
    st.info("支持各种格式：gif, jpg, png, webp 等")
    
    image_url = st.text_input(
        "图片URL",
        placeholder="https://example.com/image.gif",
        help="可使用 https://www.superbed.cn/ 图床获取图片链接"
    )
    
    if image_url and not image_url.startswith(('http://', 'https://')):
        st.warning("警告：URL格式可能不正确，请确保以 http:// 或 https:// 开头")
    
    st.markdown("---")
    
    # 步骤2：选择输入方式
    st.header("第二步：请提供认证信息")
    
    input_method = st.radio(
        "选择输入方式",
        ["粘贴完整的HTTP请求（推荐）", "手动输入关键信息"],
        key="input_method"
    )
    
    if input_method == "粘贴完整的HTTP请求（推荐）":
        st.info("示例请求URL开头:")
        st.code("https://acs.m.goofish.com/h5/mtop.idle.wx.user.profile.update/1.0/2.0/?jsv=2.4.12&appKey=12574478&...")
        
        request_text = st.text_area(
            "请粘贴完整的HTTP请求（包含headers和data）",
            height=300,
            placeholder="粘贴完整的HTTP请求内容..."
        )
        
        if st.button("解析请求", type="primary"):
            if request_text:
                with st.spinner("正在解析请求..."):
                    st.session_state.auth_info = extract_from_request(request_text)
                    st.success("✅ 请求解析成功！")
                    
                    # 显示提取的信息
                    with st.expander("查看提取的信息"):
                        st.json(st.session_state.auth_info)
    
    else:  # 手动输入
        with st.form("manual_input_form"):
            st.subheader("请输入关键信息")
            
            utdid = st.text_input("utdid (从data中获取)", help="必需")
            
            col1, col2 = st.columns(2)
            with col1:
                cookie2 = st.text_input("cookie2")
                sgcookie = st.text_input("sgcookie")
                csg = st.text_input("csg")
            with col2:
                unb = st.text_input("unb")
                munb = st.text_input("munb")
                bx_umidtoken = st.text_input("bx-umidtoken")
            
            col3, col4 = st.columns(2)
            with col3:
                x_ticid = st.text_input("x-ticid")
            with col4:
                mini_janus = st.text_input("mini-janus")
                bx_ua = st.text_input("bx-ua")
            
            submitted = st.form_submit_button("保存信息", type="primary")
            
            if submitted:
                if not utdid:
                    st.error("错误：utdid不能为空")
                else:
                    st.session_state.auth_info = {
                        "cookies": {},
                        "headers": {},
                        "params": {},
                        "data": {},
                        "utdid": utdid,
                        "token": st.session_state.current_m_h5_tk.split('_')[0] if '_' in st.session_state.current_m_h5_tk else st.session_state.current_m_h5_tk,
                        "m_h5_tk": st.session_state.current_m_h5_tk,
                    }
                    
                    # 添加cookie信息
                    if cookie2:
                        st.session_state.auth_info["cookies"]["cookie2"] = cookie2
                    if sgcookie:
                        st.session_state.auth_info["cookies"]["sgcookie"] = sgcookie
                        st.session_state.auth_info["headers"]["sgcookie"] = sgcookie
                    if csg:
                        st.session_state.auth_info["cookies"]["csg"] = csg
                    if unb:
                        st.session_state.auth_info["cookies"]["unb"] = unb
                    if munb:
                        st.session_state.auth_info["cookies"]["munb"] = munb
                    
                    # 添加header信息
                    if bx_umidtoken:
                        st.session_state.auth_info["headers"]["bx-umidtoken"] = bx_umidtoken
                    if x_ticid:
                        st.session_state.auth_info["headers"]["x-ticid"] = x_ticid
                    if mini_janus:
                        st.session_state.auth_info["headers"]["mini-janus"] = mini_janus
                    if bx_ua:
                        st.session_state.auth_info["headers"]["bx-ua"] = bx_ua
                    
                    st.success("✅ 信息保存成功！")
    
    st.markdown("---")
    
    # 步骤3：执行更新
    st.header("第三步：执行头像更新")
    
    if st.button("🚀 开始更新头像", type="primary", use_container_width=True):
        if not image_url:
            st.error("错误：请先输入图片URL")
            return
        
        if not st.session_state.auth_info.get("utdid"):
            st.error("错误：未能获取到utdid，请确保正确输入了认证信息")
            return
        
        try:
            # 下载并上传图片
            with st.spinner("正在处理图片..."):
                final_url = upload_from_url(image_url, st.session_state.auth_info)
            
            # 更新头像
            with st.spinner("正在更新头像信息..."):
                result = update_avatar(final_url, st.session_state.auth_info)
            
            st.markdown("---")
            st.header("处理结果")
            
            # 显示结果
            st.json(result)
            
            if result.get("ret") and "SUCCESS" in str(result["ret"]):
                st.success("✅ 头像更新成功！")
                st.balloons()
            else:
                st.warning("⚠️ 头像更新可能失败，请检查返回信息")
                
        except Exception as e:
            st.error(f"❌ 错误: {str(e)}")
            with st.expander("查看详细错误信息"):
                st.exception(e)
    
    # 显示当前token状态
    with st.sidebar:
        st.subheader("当前状态")
        st.info(f"当前 _m_h5_tk: {st.session_state.current_m_h5_tk[:20]}...")
        
        if st.button("重置 Session"):
            st.session_state.current_m_h5_tk = "717336018584e9c7c54f266f5db96fca_1772912434028"
            st.session_state.auth_info = {
                "cookies": {},
                "headers": {},
                "params": {},
                "data": {},
                "utdid": None,
                "token": None,
                "m_h5_tk": None
            }
            st.success("Session已重置")
            st.rerun()

if __name__ == "__main__":
    main()
