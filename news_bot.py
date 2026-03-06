#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日新闻汇总机器人
获取新闻并发送到飞书群
"""

import requests
import os
import xml.etree.ElementTree as ET
from datetime import datetime

# ============ 配置区域 ============
# 在 GitHub Secrets 中配置以下变量：
# - FEISHU_APP_ID: 飞书应用的 App ID
# - FEISHU_APP_SECRET: 飞书应用的 App Secret
# - FEISHU_CHAT_ID: 接收消息的聊天 ID（群聊或私聊）
# ==================================

def get_feishu_token():
    """获取飞书 access_token"""
    app_id = os.getenv('FEISHU_APP_ID')
    app_secret = os.getenv('FEISHU_APP_SECRET')
    
    if not app_id or not app_secret:
        print("❌ 错误：未配置 FEISHU_APP_ID 或 FEISHU_APP_SECRET")
        return None
    
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {
        "app_id": app_id,
        "app_secret": app_secret
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        result = response.json()
        
        if result.get('code') == 0:
            return result.get('tenant_access_token')
        else:
            print(f"❌ 获取 token 失败：{result}")
            return None
    except Exception as e:
        print(f"❌ 异常：{e}")
        return None

def parse_rss(content):
    """解析 RSS XML 内容"""
    items = []
    try:
        root = ET.fromstring(content)
        # 处理不同的 RSS 命名空间
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        channel = root.find('.//channel')
        if channel is not None:
            for item in channel.findall('item'):
                title = item.find('title')
                link = item.find('link')
                description = item.find('description')
                if title is not None and link is not None:
                    items.append({
                        'title': title.text or '',
                        'link': link.text or '',
                        'summary': description.text[:100] + '...' if description is not None and description.text else '点击查看详细内容'
                    })
    except Exception as e:
        print(f"⚠️ RSS 解析失败：{e}")
    return items

def get_news():
    """获取新闻内容 - 国际 + 国内混合源"""
    news_items = []
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; NewsBot/1.0)'}
    
    # 1. BBC 新闻头条（国际）
    try:
        response = requests.get("https://feeds.bbci.co.uk/news/rss.xml", headers=headers, timeout=10)
        if response.status_code == 200:
            items = parse_rss(response.content)
            for item in items[:2]:
                news_items.append({
                    "title": "🌍 " + item['title'],
                    "content": item['summary'],
                    "url": item['link']
                })
    except Exception as e:
        print(f"⚠️ BBC 获取失败：{e}")
    
    # 2. 知乎热榜（热点）
    try:
        zhihu_response = requests.get("https://www.zhihu.com/api/v3/feed/topstory/hot?limit=5", headers=headers, timeout=10)
        if zhihu_response.status_code == 200:
            zhihu_data = zhihu_response.json()
            for item in zhihu_data.get('data', [])[:2]:
                target = item.get('target', {})
                news_items.append({
                    "title": "🔥 " + target.get('title', '知乎热榜'),
                    "content": target.get('excerpt', '点击查看')[:100] + "...",
                    "url": target.get('url', 'https://www.zhihu.com/hot')
                })
    except Exception as e:
        print(f"⚠️ 知乎获取失败：{e}")
    
    # 3. 36 氪（科技财经）
    try:
        response = requests.get("https://36kr.com/feed", headers=headers, timeout=10)
        if response.status_code == 200:
            items = parse_rss(response.content)
            for item in items[:1]:
                news_items.append({
                    "title": "💡 " + item['title'],
                    "content": item['summary'],
                    "url": item['link']
                })
    except Exception as e:
        print(f"⚠️ 36 氪获取失败：{e}")
    
    # 如果没有获取到任何新闻，使用备用数据
    if not news_items:
        print("⚠️ 使用备用新闻数据")
        news_items = [
            {
                "title": "📰 今日科技要闻",
                "content": "AI 技术持续发展，多个领域取得突破",
                "url": "https://36kr.com/"
            },
            {
                "title": "🌍 国际动态",
                "content": "全球科技合作进一步加强",
                "url": "https://www.bbc.com/news"
            },
            {
                "title": "💡 创新前沿",
                "content": "新技术应用落地，改变生活方式",
                "url": "https://www.zhihu.com/hot"
            }
        ]
    
    return news_items[:6]  # 最多返回 6 条

def format_message(news_items):
    """格式化飞书消息 - 使用 text 类型简化"""
    today = datetime.now().strftime("%Y年%m月%d日")
    
    text_lines = [f"📅 {today} 新闻汇总\n"]
    
    for i, news in enumerate(news_items, 1):
        text_lines.append(f"\n{i}. {news['title']}")
        text_lines.append(news['content'])
        text_lines.append(f"🔗 {news['url']}")
    
    text_lines.append("\n━━━━━━━━━━━━━━")
    text_lines.append("\n祝你有美好的一天！☀️")
    
    full_text = "\n".join(text_lines)
    
    return {
        "msg_type": "text",
        "content": {
            "text": full_text
        }
    }

def send_to_feishu(message, access_token):
    """使用飞书 API 发送消息"""
    import json
    
    chat_id = os.getenv('FEISHU_CHAT_ID')
    
    if not chat_id:
        print("❌ 错误：未配置 FEISHU_CHAT_ID")
        return False
    
    if not access_token:
        print("❌ 错误：未获取到 access_token")
        return False
    
    # 飞书消息 API v1 - receive_id_type 作为 query 参数
    receive_id_type = "open_id"  # ou_ 开头的是 open_id
    url = f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type={receive_id_type}"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # content 需要是 JSON 字符串
    payload = {
        "receive_id": chat_id,
        "msg_type": message["msg_type"],
        "content": json.dumps(message["content"])
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        result = response.json()
        
        if result.get('code') == 0:
            print("✅ 新闻发送成功！")
            return True
        else:
            print(f"❌ 发送失败：{result}")
            return False
            
    except Exception as e:
        print(f"❌ 异常：{e}")
        return False

def main():
    print("🚀 开始获取新闻...")
    news_items = get_news()
    print(f"📰 获取到 {len(news_items)} 条新闻")
    
    print("📝 格式化消息...")
    message = format_message(news_items)
    
    print("🔑 获取飞书 Token...")
    access_token = get_feishu_token()
    
    if not access_token:
        print("⚠️ 无法获取 token，请检查 FEISHU_APP_ID 和 FEISHU_APP_SECRET 配置")
        exit(1)
    
    print("📤 发送到飞书...")
    success = send_to_feishu(message, access_token)
    
    if success:
        print("✨ 完成！")
    else:
        print("⚠️ 发送失败，请检查配置")
        exit(1)

if __name__ == "__main__":
    main()
