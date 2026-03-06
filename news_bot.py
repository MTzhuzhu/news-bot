#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日新闻汇总机器人
获取新闻并发送到飞书群
"""

import requests
import os
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

def get_news():
    """获取新闻内容"""
    # 这里可以接入实际新闻 API
    # 示例：知乎日报、新浪新闻等
    
    news_items = [
        {
            "title": "📰 今日科技要闻",
            "content": "AI 技术持续发展，多个领域取得突破",
            "url": "https://example.com/tech"
        },
        {
            "title": "🌍 国际动态",
            "content": "全球科技合作进一步加强",
            "url": "https://example.com/world"
        },
        {
            "title": "💡 创新前沿",
            "content": "新技术应用落地，改变生活方式",
            "url": "https://example.com/innovation"
        }
    ]
    
    return news_items

def format_message(news_items):
    """格式化飞书消息"""
    today = datetime.now().strftime("%Y年%m月%d日")
    
    content = [
        [
            {
                "tag": "text",
                "text": f"📅 {today} 新闻汇总\n",
                "style": ["bold"]
            }
        ]
    ]
    
    for i, news in enumerate(news_items, 1):
        content.append([
            {
                "tag": "text",
                "text": f"\n{i}. {news['title']}\n",
                "style": ["bold"]
            }
        ])
        content.append([
            {
                "tag": "text",
                "text": f"{news['content']}\n"
            }
        ])
        content.append([
            {
                "tag": "a",
                "text": "查看详情 →",
                "href": news['url']
            }
        ])
    
    content.append([
        {"tag": "hr"}
    ])
    content.append([
        {
            "tag": "text",
            "text": "\n祝你有美好的一天！☀️",
            "style": ["italic"]
        }
    ])
    
    return {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": f"📰 {today} 新闻汇总",
                    "content": content
                }
            }
        }
    }

def send_to_feishu(message, access_token):
    """使用飞书 API 发送消息"""
    chat_id = os.getenv('FEISHU_CHAT_ID')
    
    if not chat_id:
        print("❌ 错误：未配置 FEISHU_CHAT_ID")
        return False
    
    if not access_token:
        print("❌ 错误：未获取到 access_token")
        return False
    
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # 飞书消息 API 参数
    payload = {
        "receive_id": chat_id,
        "msg_type": "interactive",
        "content": message
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
