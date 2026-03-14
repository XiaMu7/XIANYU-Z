# app.py
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
from datetime import datetime
import pandas as pd
import random

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
    layout="wide",
    initial_sidebar_state="expanded"
)

# 初始化session状态
if 'session' not in st.session_state:
    st.session_state.session = requests.Session()
    st.session_state.session.verify = False
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

if 'upload_history' not in st.session_state:
    st.session_state.upload_history = []

if 'preview_url' not in st.session_state:
    st.session_state.preview_url = None

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if 'bg_color' not in st.session_state:
    st.session_state.bg_color = "#ffffff"  # 默认白色背景

if 'show_success_popup' not in st.session_state:
    st.session_state.show_success_popup = False

if 'gradient_colors' not in st.session_state:
    # 预设一些漂亮的渐变颜色组合
    st.session_state.gradient_colors = [
        ["#667eea", "#764ba2"],  # 紫蓝
        ["#ff6b6b", "#feca57"],  # 红黄
        ["#48c6ef", "#6f86d6"],  # 蓝紫
        ["#f093fb", "#f5576c"],  # 粉红
        ["#4facfe", "#00f2fe"],  # 蓝青
        ["#43e97b", "#38f9d7"],  # 绿青
        ["#fa709a", "#fee140"],  # 粉黄
        ["#30cfd0", "#330867"],  # 蓝深蓝
    ]
    st.session_state.current_gradient = random.choice(st.session_state.gradient_colors)

if 'copy_success' not in st.session_state:
    st.session_state.copy_success = False
    st.session_state.copied_text = ""

# 自定义CSS美化
st.markdown("""
<style>
    /* 全局样式 */
    .stApp {
        background: v-bind(bg_color);
        transition: background-color 0.5s ease;
    }
    
    /* 主容器样式 - 动态渐变版 */
    .main-header {
        background: linear-gradient(135deg, var(--gradient-start), var(--gradient-end));
        padding: 2.5rem;
        border-radius: 30px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 20px 40px rgba(0,0,0,0.2);
        position: relative;
        overflow: hidden;
        animation: headerPulse 4s ease-in-out infinite;
        transition: background 1s ease;
    }
    
    @keyframes headerPulse {
        0%, 100% { transform: scale(1); box-shadow: 0 20px 40px rgba(0,0,0,0.2); }
        50% { transform: scale(1.01); box-shadow: 0 25px 50px rgba(0,0,0,0.25); }
    }
    
    .main-header::before {
        content: '';
        position: absolute;
        top: -50%;
        right: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.15) 0%, transparent 70%);
        animation: rotate 25s linear infinite;
    }
    
    @keyframes rotate {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
    
    .main-header h1 {
        font-size: 3.2rem;
        font-weight: 800;
        margin-bottom: 0.8rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        position: relative;
        z-index: 1;
        background: linear-gradient(to right, #ffffff, #f8f9fa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        display: inline-block;
        letter-spacing: 1px;
    }
    
    .main-header p {
        font-size: 1.3rem;
        opacity: 0.95;
        position: relative;
        z-index: 1;
        letter-spacing: 1px;
        font-weight: 300;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
        background: rgba(255,255,255,0.15);
        padding: 0.5rem 1.5rem;
        border-radius: 50px;
        display: inline-block;
        backdrop-filter: blur(5px);
    }
    
    .header-decoration {
        position: absolute;
        bottom: 0;
        left: 0;
        width: 100%;
        height: 3px;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.6), transparent);
        animation: scan 3s linear infinite;
    }
    
    @keyframes scan {
        0% { transform: translateX(-100%); }
        100% { transform: translateX(100%); }
    }
    
    /* 登录卡片样式 */
    .login-card {
        background: white;
        padding: 2.5rem;
        border-radius: 25px;
        box-shadow: 0 15px 50px rgba(102, 126, 234, 0.2);
        max-width: 450px;
        margin: 3rem auto;
        text-align: center;
        animation: fadeInUp 0.6s ease;
        border: 1px solid rgba(255,255,255,0.3);
    }
    
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .login-title {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
    }
    
    .login-subtitle {
        color: #666;
        margin-bottom: 2rem;
        font-size: 1.1rem;
    }
    
    .question-box {
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        padding: 1.2rem;
        border-radius: 15px;
        margin: 1.5rem 0;
        font-size: 1.3rem;
        font-weight: 500;
        box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
    }
    
    /* 弹窗样式 */
    .success-popup {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: white;
        padding: 2.5rem;
        border-radius: 30px;
        box-shadow: 0 30px 70px rgba(0,0,0,0.3);
        z-index: 9999;
        text-align: center;
        animation: popIn 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        border: 3px solid #667eea;
    }
    
    .popup-content {
        font-size: 6rem;
        line-height: 1;
        margin-bottom: 1rem;
        animation: bounce 0.5s ease infinite alternate;
    }
    
    @keyframes bounce {
        from { transform: scale(1); }
        to { transform: scale(1.1); }
    }
    
    .popup-text {
        font-size: 1.3rem;
        color: #333;
        font-weight: 600;
    }
    
    .popup-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0,0,0,0.5);
        z-index: 9998;
        animation: fadeIn 0.3s ease;
    }
    
    @keyframes popIn {
        from {
            opacity: 0;
            transform: translate(-50%, -50%) scale(0.5);
        }
        to {
            opacity: 1;
            transform: translate(-50%, -50%) scale(1);
        }
    }
    
    /* 卡片样式 */
    .step-card {
        background: white;
        padding: 1.8rem;
        border-radius: 25px;
        box-shadow: 0 8px 25px rgba(0,0,0,0.08);
        margin-bottom: 1.8rem;
        border: 1px solid rgba(102, 126, 234, 0.1);
        transition: all 0.3s ease;
    }
    
    .step-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 35px rgba(102, 126, 234, 0.15);
        border-color: rgba(102, 126, 234, 0.3);
    }
    
    .step-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: #333;
        margin-bottom: 1.2rem;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    .step-title .step-number {
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        width: 38px;
        height: 38px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.2rem;
        font-weight: 600;
        box-shadow: 0 5px 10px rgba(102, 126, 234, 0.3);
    }
    
    /* 预览卡片样式 */
    .preview-card {
        background: linear-gradient(135deg, #f8f9fa, #e9ecef);
        padding: 1.8rem;
        border-radius: 25px;
        text-align: center;
        margin-bottom: 1rem;
        border: 1px solid rgba(102, 126, 234, 0.1);
    }
    
    .preview-image {
        width: 200px;
        height: 200px;
        border-radius: 50%;
        object-fit: cover;
        border: 5px solid white;
        box-shadow: 0 15px 35px rgba(102, 126, 234, 0.3);
        margin: 0 auto 1.2rem auto;
        transition: all 0.3s ease;
    }
    
    .preview-image:hover {
        transform: scale(1.08);
        box-shadow: 0 20px 40px rgba(102, 126, 234, 0.4);
    }
    
    /* 按钮样式 */
    .stButton > button {
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        border: none;
        padding: 0.8rem 2rem;
        border-radius: 50px;
        font-weight: 600;
        font-size: 1.1rem;
        transition: all 0.3s ease;
        width: 100%;
        box-shadow: 0 8px 20px rgba(102, 126, 234, 0.3);
        border: 1px solid rgba(255,255,255,0.2);
    }
    
    .stButton > button:hover {
        transform: translateY(-3px);
        box-shadow: 0 12px 30px rgba(102, 126, 234, 0.5);
    }
    
    /* 复制按钮样式 */
    .copy-btn {
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        border: none;
        padding: 0.4rem 1.2rem;
        border-radius: 30px;
        font-size: 0.9rem;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.3s ease;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        margin-left: 12px;
        box-shadow: 0 4px 10px rgba(102, 126, 234, 0.3);
        border: 1px solid rgba(255,255,255,0.2);
        white-space: nowrap;
    }
    
    .copy-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 15px rgba(102, 126, 234, 0.4);
    }
    
    .copy-btn.copied {
        background: linear-gradient(135deg, #84fab0, #8fd3f4);
        color: #333;
    }
    
    /* 提示框样式 - 美化版 */
    .tip-box {
        background: linear-gradient(135deg, #f8faff, #f0f3ff);
        padding: 1.2rem;
        border-radius: 20px;
        border-left: 6px solid #667eea;
        margin: 1.2rem 0;
        animation: slideInRight 0.4s ease;
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.1);
    }
    
    @keyframes slideInRight {
        from {
            opacity: 0;
            transform: translateX(-20px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    .tip-title {
        font-weight: 700;
        color: #667eea;
        margin-bottom: 0.8rem;
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 1.1rem;
    }
    
    .tip-title span {
        background: rgba(102, 126, 234, 0.1);
        padding: 0.3rem 0.8rem;
        border-radius: 30px;
    }
    
    .tip-content {
        color: #555;
        font-size: 0.95rem;
        margin-bottom: 0.5rem;
        font-weight: 500;
    }
    
    /* URL容器样式 - 美化版 */
    .url-container {
        display: flex;
        align-items: center;
        background: white;
        padding: 0.6rem 1rem;
        border-radius: 16px;
        border: 2px solid #eef2ff;
        margin: 0.8rem 0;
        transition: all 0.3s ease;
        box-shadow: 0 2px 8px rgba(0,0,0,0.02);
    }
    
    .url-container:hover {
        border-color: #667eea;
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.15);
    }
    
    .url-text {
        flex: 1;
        font-family: 'Courier New', monospace;
        font-size: 0.95rem;
        color: #2c3e50;
        word-break: break-all;
        padding: 0.3rem 0;
        letter-spacing: 0.3px;
        background: #f8faff;
        padding: 0.4rem 0.8rem;
        border-radius: 12px;
    }
    
    /* 成功消息样式 */
    .success-message {
        background: linear-gradient(135deg, #84fab0, #8fd3f4);
        padding: 1.2rem;
        border-radius: 20px;
        color: white;
        text-align: center;
        animation: slideInDown 0.5s ease;
        font-weight: 600;
        font-size: 1.1rem;
        box-shadow: 0 10px 25px rgba(132, 250, 176, 0.3);
    }
    
    @keyframes slideInDown {
        from {
            opacity: 0;
            transform: translateY(-20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    /* 进度条样式 */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #667eea, #764ba2) !important;
        border-radius: 10px;
    }
    
    /* 标签页样式 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
        background: white;
        padding: 0.6rem;
        border-radius: 60px;
        box-shadow: 0 5px 20px rgba(102, 126, 234, 0.15);
        margin-bottom: 1.5rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 50px;
        padding: 0.6rem 2rem;
        font-weight: 600;
        color: #666;
        transition: all 0.3s ease;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea, #764ba2) !important;
        color: white !important;
    }
    
    /* 信息框样式 */
    .info-box {
        background: linear-gradient(135deg, #f8faff, #f0f3ff);
        padding: 1.5rem;
        border-radius: 20px;
        border-left: 6px solid #667eea;
        margin: 1rem 0;
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.1);
    }
    
    /* 统计卡片 */
    .stat-card {
        background: white;
        padding: 1.5rem;
        border-radius: 25px;
        text-align: center;
        box-shadow: 0 8px 20px rgba(0,0,0,0.05);
        transition: all 0.3s ease;
        border: 1px solid rgba(102, 126, 234, 0.1);
    }
    
    .stat-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 30px rgba(102, 126, 234, 0.15);
    }
    
    .stat-number {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        line-height: 1.2;
    }
    
    .stat-label {
        color: #666;
        font-size: 0.95rem;
        margin-top: 0.5rem;
        font-weight: 500;
    }
    
    /* 输入框样式 */
    .stTextInput > div > div > input {
        border-radius: 16px;
        border: 2px solid #eef2ff;
        padding: 0.8rem 1rem;
        font-size: 1rem;
        transition: all 0.3s ease;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    /* 文本区域样式 */
    .stTextArea > div > div > textarea {
        border-radius: 16px;
        border: 2px solid #eef2ff;
        transition: all 0.3s ease;
    }
    
    .stTextArea > div > div > textarea:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    /* 单选按钮样式 */
    .stRadio > div {
        background: #f8faff;
        padding: 0.8rem;
        border-radius: 50px;
        border: 1px solid #eef2ff;
    }
    
    /* 侧边栏样式 */
    .css-1d391kg {
        background: linear-gradient(135deg, #f8faff, #f0f3ff);
    }
</style>
""", unsafe_allow_html=True)

# 创建会话函数
def create_session_with_retries() -> requests.Session:
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
    try:
        response = requests.head(url, timeout=timeout, allow_redirects=True, verify=False)
        return True, response.status_code, response.reason
    except Exception as e:
        return False, 0, str(e)

def extract_auth_from_url(url: str) -> Dict[str, str]:
    auth_info = {}
    parsed = urlparse(url)
    
    if parsed.username and parsed.password:
        auth_info['username'] = parsed.username
        auth_info['password'] = parsed.password
        auth_str = f"{parsed.username}:{parsed.password}"
        auth_info['basic_auth'] = base64.b64encode(auth_str.encode()).decode()
    
    return auth_info

def handle_401_with_auth(url: str, timeout: int = 30) -> Optional[Tuple[bytes, str, str]]:
    st.warning("🔄 检测到401授权错误，尝试使用认证信息...")
    
    parsed_url = urlparse(url)
    file_name = os.path.basename(parsed_url.path)
    if not file_name or '.' not in file_name:
        file_name = f"image_{int(time.time())}.jpg"
    
    with st.expander("🔐 认证设置", expanded=True):
        auth_method = st.radio(
            "选择认证方式",
            ["Bearer Token", "Cookie", "Referer", "跳过认证"],
            key="auth_method_401",
            horizontal=True
        )
    
    auth_attempts = []
    
    if auth_method == "Bearer Token":
        token = st.text_input("请输入Bearer Token", type="password", key="bearer_token_401")
        if token:
            auth_attempts.append({
                'name': 'Bearer Token',
                'headers': {
                    'Authorization': f"Bearer {token}",
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            })
    
    elif auth_method == "Cookie":
        cookie_str = st.text_area("请输入Cookie (key=value; key2=value2)", key="cookie_str_401", height=100)
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
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("文件大小", f"{len(content)/1024:.1f} KB")
                    with col2:
                        st.metric("MIME类型", mime)
                    with col3:
                        st.metric("文件名", file_name[:20] + "..." if len(file_name) > 20 else file_name)
                    
                    return content, file_name, mime
            else:
                st.error(f"❌ 失败: HTTP {response.status_code}")
                
        except Exception as e:
            st.error(f"❌ 失败: {str(e)[:100]}")
            continue
    
    return None

def download_image_with_fallback(url: str, timeout: int = 30) -> Tuple[bytes, str, str]:
    with st.status("🔄 正在处理图片...", expanded=True) as status:
        st.write(f"开始处理图片URL: {url}")
        
        accessible, status_code, reason = check_url_accessibility(url)
        
        if status_code == 401:
            st.write("⚠️ URL返回 401 Authorization Required")
            auth_result = handle_401_with_auth(url, timeout)
            if auth_result:
                status.update(label="✅ 图片处理成功", state="complete")
                return auth_result
        
        download_session = create_session_with_retries()
        
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
        ]
        
        parsed_url = urlparse(url)
        file_name = os.path.basename(parsed_url.path)
        if not file_name or '.' not in file_name:
            file_name = f"image_{int(time.time())}.jpg"
        
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
                st.write(f"尝试下载策略 {i}/{len(strategies)}: {strategy['name']}")
                
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
                    st.write(f"⚠️ 返回 401 需要授权，尝试其他策略...")
                    continue
                    
                response.raise_for_status()
                
                content_type = response.headers.get('Content-Type', '').lower()
                if content_type and not any(img_type in content_type for img_type in ['image/', 'application/octet-stream']):
                    st.write(f"⚠️ 警告: 可能不是图片文件 (Content-Type: {content_type})")
                
                content = response.content
                
                if len(content) == 0:
                    st.write(f"⚠️ 下载的文件为空")
                    continue
                
                mime = content_type.split(';')[0].strip()
                if not mime or mime == 'application/octet-stream':
                    guessed = mimetypes.guess_type(file_name)[0]
                    if guessed:
                        mime = guessed
                    else:
                        mime = 'image/jpeg' if file_name.lower().endswith(('.jpg', '.jpeg')) else 'image/png'
                
                st.success(f"✅ 下载成功 (策略 {i})")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("文件大小", f"{len(content)/1024:.1f} KB")
                with col2:
                    st.metric("MIME类型", mime)
                with col3:
                    st.metric("文件名", file_name[:20] + "..." if len(file_name) > 20 else file_name)
                
                progress_bar.empty()
                status.update(label="✅ 图片处理成功", state="complete")
                return content, file_name, mime
                
            except Exception as e:
                st.error(f"❌ 错误: {str(e)[:100]}...")
                continue
        
        progress_bar.empty()
        error_msg = "所有下载策略都失败"
        st.error(f"❌ {error_msg}")
        status.update(label="❌ 图片处理失败", state="error")
        raise RuntimeError(error_msg)

def extract_from_request(request_text: str) -> dict:
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
    
    first_line = lines[0]
    url_match = re.search(r'\?(.*?)(?:\s|$)', first_line)
    if url_match:
        params_str = url_match.group(1)
        params = parse_qs(params_str)
        for k, v in params.items():
            info["params"][k] = v[0] if v else ""
    
    for line in lines[1:]:
        line = line.strip()
        if not line or line.startswith('{') or line.startswith('h2'):
            continue
            
        if ': ' in line:
            key, value = line.split(': ', 1)
            key_lower = key.lower()
            
            info["headers"][key] = value
            
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
        except json.JSONDecodeError:
            utdid_match = re.search(r'utdid[":]+([^"]+)', data_str)
            if utdid_match:
                info["utdid"] = utdid_match.group(1)
    
    return info

def calc_sign(token: str, t: str, app_key: str, data_str: str) -> str:
    raw = f"{token}&{t}&{app_key}&{data_str}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()

def update_avatar(image_url: str, auth_info: dict, retry_count: int = 0) -> dict:
    cookies = auth_info.get("cookies", {}).copy()
    
    m_h5_tk = st.session_state.current_m_h5_tk
    token = m_h5_tk.split('_')[0] if '_' in m_h5_tk else m_h5_tk
    
    cookies["_m_h5_tk"] = m_h5_tk
    cookies["_m_h5_tk_enc"] = "927a61b5898abf557861458d0ea06b6f"
    
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

    headers = {
        "User-Agent": auth_info.get("headers", {}).get("user-agent", 
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/126.0.0.0"
        ),
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "Referer": "https://servicewechat.com/wx9882f2a891880616/74/page-frame.html",
    }
    
    special_headers = ["bx-umidtoken", "x-ticid", "x-tap", "mini-janus", "sgcookie", "bx-ua"]
    for h in special_headers:
        if h in auth_info.get("headers", {}):
            headers[h] = auth_info["headers"][h]

    response = st.session_state.session.post(
        f"{BASE_URL}?{urlencode(params)}",
        headers=headers,
        cookies=cookies,
        data={"data": data_str},
        timeout=20,
        verify=False
    )
    
    token_updated = False
    if '_m_h5_tk' in response.cookies:
        new_m_h5_tk = response.cookies['_m_h5_tk']
        if new_m_h5_tk != st.session_state.current_m_h5_tk:
            st.session_state.current_m_h5_tk = new_m_h5_tk
            auth_info['m_h5_tk'] = new_m_h5_tk
            auth_info['token'] = new_m_h5_tk.split('_')[0] if '_' in new_m_h5_tk else new_m_h5_tk
            token_updated = True
    
    result = response.json()
    
    if result.get("ret") and "FAIL_SYS_TOKEN_ILLEGAL" in str(result["ret"]) and retry_count == 0 and token_updated:
        time.sleep(1)
        return update_avatar(image_url, auth_info, retry_count=1)
    
    return result

def upload_bytes(file_name: str, file_bytes: bytes, mime: str, auth_info: dict) -> str:
    cookies = auth_info.get("cookies", {}).copy()
    
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
    
    for h in ["bx-umidtoken", "x-ticid", "mini-janus", "sgcookie"]:
        if h in auth_info.get("headers", {}):
            headers[h] = auth_info["headers"][h]

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
    content, file_name, mime = download_image_with_fallback(file_url)
    
    with st.status("📤 正在上传到闲鱼服务器...", expanded=True) as status:
        final_url = upload_bytes(file_name, content, mime, auth_info)
        status.update(label="✅ 上传成功！", state="complete")
    
    # 保存到历史记录
    st.session_state.upload_history.append({
        "时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "原始URL": file_url[:50] + "..." if len(file_url) > 50 else file_url,
        "最终URL": final_url,
        "文件名": file_name,
        "大小": f"{len(content)/1024:.1f} KB"
    })
    
    return final_url

# 登录页面
def show_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div class="login-card">
            <div class="login-title">🔐 访问验证</div>
            <div class="login-subtitle">请输入正确答案继续</div>
            <div class="question-box">
                🤔 世界上谁最帅？
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        answer = st.text_input("你的答案", type="password", placeholder="请输入答案...")
        
        if st.button("确认进入", use_container_width=True):
            if answer.strip().lower() == "夏目":
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("❌ 答案错误，请重试！")

# 显示成功弹窗
def show_success_popup():
    if st.session_state.show_success_popup:
        st.markdown("""
        <div class="popup-overlay" onclick="document.querySelector('.success-popup').style.display='none'"></div>
        <div class="success-popup">
            <div class="popup-content">✅️</div>
            <div class="popup-text">头像更新成功！</div>
        </div>
        """, unsafe_allow_html=True)
        
        # 3秒后自动关闭弹窗
        time.sleep(3)
        st.session_state.show_success_popup = False
        st.rerun()

# 主界面
def main_app():
    # 显示成功弹窗
    show_success_popup()
    
    # 背景颜色选择器
    with st.sidebar:
        st.markdown("### 🎨 界面设置")
        
        # 颜色选择器
        st.session_state.bg_color = st.color_picker(
            "选择背景颜色",
            value=st.session_state.bg_color,
            help="点击选择您喜欢的背景颜色"
        )
        
        # 渐变切换按钮
        if st.button("🎨 随机切换渐变", use_container_width=True):
            st.session_state.current_gradient = random.choice(st.session_state.gradient_colors)
            st.rerun()
        
        # 应用CSS变量
        st.markdown(f"""
        <style>
            .stApp {{
                background-color: {st.session_state.bg_color} !important;
            }}
            .main-header {{
                --gradient-start: {st.session_state.current_gradient[0]};
                --gradient-end: {st.session_state.current_gradient[1]};
            }}
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("### 📊 统计信息")
        st.metric("总上传次数", len(st.session_state.upload_history))
        if st.session_state.upload_history:
            total_size = sum(float(item["大小"].replace(" KB", "")) for item in st.session_state.upload_history)
            st.metric("总上传大小", f"{total_size:.1f} KB")
    
    # 主界面内容 - 动态渐变版头部
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(f"""
        <div class="main-header">
            <h1>🖼️ 闲鱼头像自动更新工具</h1>
            <p>✨ 轻松更换你的闲鱼头像，支持各种图片格式 ✨</p>
            <div class="header-decoration"></div>
        </div>
        """, unsafe_allow_html=True)

    # 创建标签页
    tab1, tab2, tab3 = st.tabs(["📝 头像更新", "📊 历史记录", "⚙️ 设置"])

    with tab1:
        # 创建两列布局
        left_col, right_col = st.columns([3, 2])
        
        with left_col:
            # 第一步：图片URL
            st.markdown("""
            <div class="step-card">
                <div class="step-title">
                    <span class="step-number">1</span>
                    输入图片URL
                </div>
            """, unsafe_allow_html=True)
            
            image_url = st.text_input(
                "图片URL",
                placeholder="https://example.com/image.gif",
                help="支持各种格式：gif, jpg, png, webp 等",
                key="image_url_input",
                on_change=lambda: st.session_state.update(
                    preview_url=st.session_state.image_url_input if st.session_state.image_url_input else None
                )
            )
            
            if image_url:
                if not image_url.startswith(('http://', 'https://')):
                    st.warning("⚠️ URL格式可能不正确，请确保以 http:// 或 https:// 开头")
                
                if st.button("🔍 预览图片", key="preview_btn", use_container_width=True):
                    st.session_state.preview_url = image_url
            
            # 图床链接提示 - 带复制按钮
            st.markdown("""
            <div class="tip-box">
                <div class="tip-title">
                    <span>📌 推荐图床</span>
                </div>
                <div class="tip-content">
                    推荐使用 Superbed 图床获取图片链接：
                </div>
            """, unsafe_allow_html=True)
            
            # 使用Streamlit的列布局创建带复制按钮的URL显示
            col1, col2 = st.columns([4, 1])
            with col1:
                st.code("https://www.superbed.cn/", language="text")
            with col2:
                if st.button("📋 复制", key="copy_superbed", use_container_width=True):
                    st.write("""
                    <script>
                    navigator.clipboard.writeText('https://www.superbed.cn/').then(function() {
                        alert('✅ 复制成功！');
                    }, function() {
                        alert('❌ 复制失败，请手动复制');
                    });
                    </script>
                    """, unsafe_allow_html=True)
                    st.success("已复制到剪贴板！")
                    time.sleep(1)
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # 第二步：认证信息
            st.markdown("""
            <div class="step-card">
                <div class="step-title">
                    <span class="step-number">2</span>
                    提供认证信息
                </div>
            """, unsafe_allow_html=True)
            
            # 请求URL提示 - 带复制按钮
            st.markdown("""
            <div class="tip-box">
                <div class="tip-title">
                    <span>🔗 请求URL</span>
                </div>
                <div class="tip-content">
                    请求URL格式：
                </div>
            """, unsafe_allow_html=True)
            
            request_url = "https://acs.m.goofish.com/h5/mtop.idle.wx.user.profile.update/1.0/2.0/?jsv=2.4.12&"
            
            # 使用Streamlit的列布局创建带复制按钮的URL显示
            col1, col2 = st.columns([4, 1])
            with col1:
                st.code(request_url, language="text")
            with col2:
                if st.button("📋 复制", key="copy_request_url", use_container_width=True):
                    st.write(f"""
                    <script>
                    navigator.clipboard.writeText('{request_url}').then(function() {{
                        alert('✅ 复制成功！');
                    }}, function() {{
                        alert('❌ 复制失败，请手动复制');
                    }});
                    </script>
                    """, unsafe_allow_html=True)
                    st.success("已复制到剪贴板！")
                    time.sleep(1)
                    st.rerun()
            
            input_method = st.radio(
                "选择输入方式",
                ["📋 粘贴完整的HTTP请求（推荐）", "✏️ 手动输入关键信息"],
                horizontal=True,
                key="input_method_main"
            )
            
            if input_method == "📋 粘贴完整的HTTP请求（推荐）":
                with st.expander("📝 查看示例请求格式", expanded=False):
                    st.code("""https://acs.m.goofish.com/h5/mtop.idle.wx.user.profile.update/1.0/2.0/?jsv=2.4.12&appKey=12574478&...
cookie: xxxx
x-smallstc: {...}
...
data={"utdid":"xxxx","platform":"mac","miniAppVersion":"9.9.9","profileCode":"avatar","profileImageUrl":"..."}""")
                
                request_text = st.text_area(
                    "请粘贴完整的HTTP请求",
                    height=200,
                    placeholder="粘贴完整的HTTP请求内容...",
                    key="request_text_main"
                )
                
                if st.button("🔍 解析请求", key="parse_btn", use_container_width=True):
                    if request_text:
                        with st.spinner("正在解析请求..."):
                            st.session_state.auth_info = extract_from_request(request_text)
                            st.success("✅ 请求解析成功！")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("utdid", st.session_state.auth_info.get("utdid", "未提取")[:20] + "..." if st.session_state.auth_info.get("utdid") else "未提取")
                            with col2:
                                st.metric("cookie数量", len(st.session_state.auth_info.get("cookies", {})))
            
            else:  # 手动输入
                with st.form("manual_input_form_main"):
                    col1, col2 = st.columns(2)
                    with col1:
                        utdid = st.text_input("utdid *", help="必需", key="utdid_manual")
                        cookie2 = st.text_input("cookie2", key="cookie2_manual")
                        sgcookie = st.text_input("sgcookie", key="sgcookie_manual")
                        csg = st.text_input("csg", key="csg_manual")
                    with col2:
                        unb = st.text_input("unb", key="unb_manual")
                        munb = st.text_input("munb", key="munb_manual")
                        bx_umidtoken = st.text_input("bx-umidtoken", key="bx_umidtoken_manual")
                    
                    col3, col4 = st.columns(2)
                    with col3:
                        x_ticid = st.text_input("x-ticid", key="x_ticid_manual")
                    with col4:
                        mini_janus = st.text_input("mini-janus", key="mini_janus_manual")
                        bx_ua = st.text_input("bx-ua", key="bx_ua_manual")
                    
                    submitted = st.form_submit_button("💾 保存信息", use_container_width=True)
                    
                    if submitted:
                        if not utdid:
                            st.error("❌ utdid不能为空")
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
                            if bx_umidtoken:
                                st.session_state.auth_info["headers"]["bx-umidtoken"] = bx_umidtoken
                            if x_ticid:
                                st.session_state.auth_info["headers"]["x-ticid"] = x_ticid
                            if mini_janus:
                                st.session_state.auth_info["headers"]["mini-janus"] = mini_janus
                            if bx_ua:
                                st.session_state.auth_info["headers"]["bx-ua"] = bx_ua
                            
                            st.success("✅ 信息保存成功！")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # 第三步：执行更新
            st.markdown("""
            <div class="step-card">
                <div class="step-title">
                    <span class="step-number">3</span>
                    执行头像更新
                </div>
            """, unsafe_allow_html=True)
            
            if st.button("🚀 开始更新头像", key="update_btn", use_container_width=True):
                if not image_url:
                    st.error("❌ 请先输入图片URL")
                elif not st.session_state.auth_info.get("utdid"):
                    st.error("❌ 请先提供认证信息")
                else:
                    try:
                        # 下载并上传图片
                        final_url = upload_from_url(image_url, st.session_state.auth_info)
                        
                        # 更新头像
                        with st.status("🔄 正在更新头像信息...", expanded=True) as status:
                            result = update_avatar(final_url, st.session_state.auth_info)
                            status.update(label="✅ 头像更新完成", state="complete")
                        
                        # 显示结果
                        st.markdown("""
                        <div class="success-message">
                            <h3>✨ 处理完成！</h3>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.json(result)
                        with col2:
                            if result.get("ret") and "SUCCESS" in str(result["ret"]):
                                # 显示成功弹窗
                                st.session_state.show_success_popup = True
                                st.rerun()
                            else:
                                st.warning("⚠️ 头像更新可能失败，请检查返回信息")
                        
                        # 更新预览
                        st.session_state.preview_url = final_url
                        
                    except Exception as e:
                        st.error(f"❌ 错误: {str(e)}")
                        with st.expander("查看详细错误信息"):
                            st.exception(e)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        with right_col:
            # 预览区域
            st.markdown("""
            <div class="step-card">
                <div class="step-title">
                    <span class="step-number">👁️</span>
                    头像预览
                </div>
            """, unsafe_allow_html=True)
            
            preview_url = st.session_state.get('preview_url', image_url if image_url else None)
            
            if preview_url:
                st.markdown(f"""
                <div class="preview-card">
                    <img src="{preview_url}" class="preview-image" onerror="this.src='https://via.placeholder.com/200?text=加载失败'">
                    <p style="color: #666; margin-top: 1rem;">点击图片可放大查看</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("### 📊 图片信息")
                with st.container():
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**URL类型**")
                        st.info("网络图片" if preview_url.startswith(('http://', 'https://')) else "未知")
                    with col2:
                        st.markdown("**预览状态**")
                        st.success("预览中")
                
                with st.expander("🔍 点击放大预览"):
                    st.image(preview_url, use_column_width=True)
            else:
                st.markdown("""
                <div class="preview-card">
                    <div style="width: 200px; height: 200px; border-radius: 50%; background: linear-gradient(135deg, #667eea, #764ba2); margin: 0 auto 1rem auto; display: flex; align-items: center; justify-content: center;">
                        <span style="color: white; font-size: 3rem;">🖼️</span>
                    </div>
                    <p style="color: #666;">输入URL后点击"预览图片"查看效果</p>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            with st.expander("💡 快速帮助", expanded=False):
                st.markdown("""
                ### 使用说明
                1. **输入图片URL**：支持各种图片格式
                2. **提供认证信息**：粘贴HTTP请求或手动输入
                3. **点击更新**：自动完成上传和更新
                
                ### 支持的图片格式
                - JPG/JPEG
                - PNG
                - GIF
                - WEBP
                - BMP
                
                ### 常见问题
                - **401错误**：图片需要授权，尝试添加认证信息
                - **SSL错误**：程序会自动尝试多种下载策略
                - **上传失败**：检查网络和认证信息
                """)

    with tab2:
        st.markdown("""
        <div class="step-card">
            <div class="step-title">
                <span class="step-number">📊</span>
                上传历史记录
            </div>
        """, unsafe_allow_html=True)
        
        if st.session_state.upload_history:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown("""
                <div class="stat-card">
                    <div class="stat-number">{}</div>
                    <div class="stat-label">总上传次数</div>
                </div>
                """.format(len(st.session_state.upload_history)), unsafe_allow_html=True)
            with col2:
                total_size = sum(float(item["大小"].replace(" KB", "")) for item in st.session_state.upload_history)
                st.markdown("""
                <div class="stat-card">
                    <div class="stat-number">{:.1f} KB</div>
                    <div class="stat-label">总上传大小</div>
                </div>
                """.format(total_size), unsafe_allow_html=True)
            with col3:
                avg_size = total_size / len(st.session_state.upload_history) if st.session_state.upload_history else 0
                st.markdown("""
                <div class="stat-card">
                    <div class="stat-number">{:.1f} KB</div>
                    <div class="stat-label">平均大小</div>
                </div>
                """.format(avg_size), unsafe_allow_html=True)
            with col4:
                last_time = st.session_state.upload_history[-1]["时间"] if st.session_state.upload_history else "暂无"
                st.markdown("""
                <div class="stat-card">
                    <div class="stat-number">{}</div>
                    <div class="stat-label">最后上传</div>
                </div>
                """.format(last_time.split()[0]), unsafe_allow_html=True)
            
            df = pd.DataFrame(st.session_state.upload_history)
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "时间": "上传时间",
                    "原始URL": "原始URL",
                    "最终URL": st.column_config.LinkColumn("最终URL"),
                    "文件名": "文件名",
                    "大小": "文件大小"
                }
            )
            
            if st.button("🗑️ 清空历史记录", key="clear_history"):
                st.session_state.upload_history = []
                st.rerun()
        else:
            st.info("暂无上传历史记录")
        
        st.markdown('</div>', unsafe_allow_html=True)

    with tab3:
        st.markdown("""
        <div class="step-card">
            <div class="step-title">
                <span class="step-number">⚙️</span>
                系统设置
            </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🔐 Token管理")
            st.text_input("当前 _m_h5_tk", value=st.session_state.current_m_h5_tk, disabled=True)
            
            if st.button("🔄 重置 Token", use_container_width=True):
                st.session_state.current_m_h5_tk = "717336018584e9c7c54f266f5db96fca_1772912434028"
                st.success("Token已重置")
                st.rerun()
        
        with col2:
            st.subheader("🗑️ 数据管理")
            if st.button("🧹 清除所有数据", use_container_width=True):
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
                st.session_state.upload_history = []
                st.session_state.preview_url = None
                st.success("所有数据已清除")
                st.rerun()
        
        st.subheader("📝 关于")
        st.markdown("""
        <div class="info-box">
            <h4>闲鱼头像自动更新工具 v2.0</h4>
            <p>本工具可以帮助你自动更新闲鱼头像，支持各种图片格式和认证方式。</p>
            <p><strong>主要功能：</strong></p>
            <ul>
                <li>支持多种图片格式（JPG、PNG、GIF、WEBP等）</li>
                <li>自动处理SSL证书问题</li>
                <li>支持401授权认证</li>
                <li>实时预览头像效果</li>
                <li>上传历史记录</li>
            </ul>
            <p><strong>注意事项：</strong></p>
            <ul>
                <li>请确保提供的认证信息有效</li>
                <li>图片URL需要可以直接访问</li>
                <li>建议使用图床获取稳定图片链接</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

    # 页脚
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: #666; padding: 1rem;">
            <p>Made with ❤️ for 闲鱼用户 | 版本 2.0</p>
        </div>
        """,
        unsafe_allow_html=True
    )

# 主程序
if not st.session_state.authenticated:
    show_login()
else:
    main_app()
