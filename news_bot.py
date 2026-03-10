#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日新闻汇总机器人 - 垂直领域版
领域：金融、科技、AI、汽车
每条新闻含来源链接 + 专业点评
"""

import requests
import os
import json
import xml.etree.ElementTree as ET
from datetime import datetime

# ============ 配置区域 ============
# GitHub Secrets:
# - FEISHU_APP_ID
# - FEISHU_APP_SECRET
# - FEISHU_CHAT_ID
# - DASHSCOPE_API_KEY (可选，用于 AI 点评)
# ==================================

# 目标领域关键词
TARGET_CATEGORIES = ['金融', '科技', 'AI', '人工智能', '汽车', '电动车', '投资', '财经', '半导体', '互联网']

# 排除关键词 - 社会/民生/娱乐类
EXCLUDE_KEYWORDS = [
    '娱乐', '明星', '体育', '政治', '社会', '天气', '旅游', '美食',
    '寄生虫', '食安', '食品安全', '吃出', '曝光', '被曝',
    '调休', '放假', '假期', '人大代表', '政协', '两会',
    '婚姻', '恋爱', '相亲', '家庭', '孩子', '学校', '医院',
    '车祸', '火灾', '事故', '案件', '警方', '法院',
    '购物', '消费', '优惠', '打折', '电商', '快递'
]

# 汇总类新闻标记（需要特殊处理）
SUMMARY_INDICATORS = ['8 点 1 氪', '早晚报', '日报', '周报', '一周盘点', '丨']

def get_feishu_token():
    """获取飞书 access_token"""
    app_id = os.getenv('FEISHU_APP_ID')
    app_secret = os.getenv('FEISHU_APP_SECRET')
    
    if not app_id or not app_secret:
        print("❌ 错误：未配置 FEISHU_APP_ID 或 FEISHU_APP_SECRET")
        return None
    
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {"app_id": app_id, "app_secret": app_secret}
    
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
                        'summary': description.text[:200] if description is not None and description.text else ''
                    })
    except Exception as e:
        print(f"⚠️ RSS 解析失败：{e}")
    return items

def classify_news(title, summary):
    """分类新闻到具体领域，返回领域标签"""
    text = (title + ' ' + summary).lower()
    
    # 1. 检查是否为汇总类新闻（如"8 点 1 氪丨..."）
    is_summary = any(indicator in title for indicator in SUMMARY_INDICATORS)
    
    # 2. 检查排除词 - 汇总类新闻更严格
    if is_summary:
        # 汇总类新闻：只要包含任何排除词就过滤
        for word in EXCLUDE_KEYWORDS:
            if word.lower() in text:
                return None, f"汇总类含排除词：{word}"
    else:
        # 普通新闻：检查排除词
        for word in EXCLUDE_KEYWORDS:
            if word.lower() in text:
                return None, f"排除类别：{word}"
    
    # 3. 按优先级分类（顺序重要）
    # 金融/财经 优先（扩大关键词）
    finance_keywords = ['金融', '财经', '投资', '融资', 'ipo', '上市', '股票', '基金', 
                       '银行', '保险', '估值', '创业', 'vc', 'pe', '并购', '财报', 
                       '营收', '利润', '利率', '央行', '通胀', '经济', '信托', '期货']
    if any(kw in text for kw in finance_keywords):
        return '金融', '金融/财经'
    
    # 汽车/电动车（扩大关键词）
    auto_keywords = ['汽车', '电动车', 'ev', '特斯拉', '比亚迪', '蔚来', '小鹏', 
                    '理想', '自动驾驶', '新能源', '造车', '车企', '销量', '交付',
                    '小米汽车', '华为汽车', '智驾', '续航', '充电桩']
    if any(kw in text for kw in auto_keywords):
        return '汽车', '汽车/出行'
    
    # AI/大模型（缩小范围，避免过度匹配）
    ai_keywords = ['ai 大模型', '人工智能', 'llm', 'deepseek', 'qwen', 'deepmind', 'openai', 'gpt-4', 'gpt-5', 'sora']
    if any(kw in text for kw in ai_keywords):
        return 'AI', 'AI/大模型'
    
    # 科技/互联网（扩大关键词，作为次级兜底）
    tech_keywords = ['科技', '互联网', '半导体', '芯片', '手机', 'app', '软件', '系统', 
                    '数码', '硬件', '5g', '6g', '物联网', '云计算', '大数据',
                    '腾讯', '阿里', '字节', '美团', '拼多多', '小米', '华为', '百度',
                    '电商', '社交', '游戏', '直播', '短视频', '操作系统']
    if any(kw in text for kw in tech_keywords):
        return '科技', '科技/互联网'
    
    # 默认兜底：归到科技类（不再过滤）
    return '科技', '科技/互联网（兜底）'

def generate_insight(title, summary, url):
    """使用 AI 生成专业点评 - 支持 DeepSeek/DashScope"""
    # 优先使用 DeepSeek，其次 DashScope
    api_key = os.getenv('DASHSCOPE_API_KEY')  # 保持原名，兼容旧配置
    use_deepseek = os.getenv('USE_DEEPSEEK', 'true').lower() == 'true'
    
    if not api_key:
        return "[点评需配置 API Key]"
    
    prompt = f"""
作为资深行业分析师，对以下新闻给出简洁犀利的专业点评（50 字内）：

新闻：{title}
摘要：{summary[:100]}

点评要求：
- 一针见血，直击本质
- 专业视角，有洞察力
- 50 字以内
- 不要复述新闻，要给观点
"""
    
    try:
        if use_deepseek:
            # DeepSeek API (兼容 OpenAI 格式)
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            payload = {
                'model': 'deepseek-chat',
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 100,
                'temperature': 0.7
            }
            response = requests.post(
                'https://api.deepseek.com/v1/chat/completions',
                headers=headers,
                json=payload,
                timeout=10
            )
            result = response.json()
            if result.get('choices') and len(result['choices']) > 0:
                insight = result['choices'][0]['message']['content'].strip()
                return insight[:80] + "..." if len(insight) > 80 else insight
        else:
            # DashScope API (阿里云)
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            payload = {
                'model': 'qwen3.5-plus',
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 100
            }
            response = requests.post(
                'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation',
                headers=headers,
                json=payload,
                timeout=10
            )
            result = response.json()
            if result.get('output') and result['output'].get('choices'):
                insight = result['output']['choices'][0]['message']['content'].strip()
                return insight[:80] + "..." if len(insight) > 80 else insight
        
        return "[AI 点评生成失败]"
    except Exception as e:
        print(f"⚠️ 点评生成失败：{e}")
        return "[AI 点评暂不可用]"

def get_news():
    """获取新闻内容 - 垂直领域源"""
    news_items = []
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; NewsBot/1.0)'}
    
    # 1. 36 氪 - 科技财经
    print("📡 获取 36 氪...")
    try:
        response = requests.get("https://36kr.com/feed", headers=headers, timeout=10)
        if response.status_code == 200:
            items = parse_rss(response.content)
            for item in items[:8]:
                category, reason = classify_news(item['title'], item['summary'])
                if category:
                    news_items.append({
                        "title": item['title'],
                        "summary": item['summary'][:150],
                        "url": item['link'],
                        "source": "36 氪",
                        "domain": category
                    })
    except Exception as e:
        print(f"⚠️ 36 氪获取失败：{e}")
    
    # 2. 虎嗅 - 科技商业
    print("📡 获取虎嗅...")
    try:
        response = requests.get("https://www.huxiu.com/rss/0.xml", headers=headers, timeout=10)
        if response.status_code == 200:
            items = parse_rss(response.content)
            for item in items[:5]:
                category, reason = classify_news(item['title'], item['summary'])
                if category:
                    news_items.append({
                        "title": item['title'],
                        "summary": item['summary'][:150],
                        "url": item['link'],
                        "source": "虎嗅",
                        "domain": category
                    })
    except Exception as e:
        print(f"⚠️ 虎嗅获取失败：{e}")
    
    # 3. 车东西 - 汽车科技
    print("📡 获取车东西...")
    try:
        response = requests.get("http://www.chedongxi.com/feed/", headers=headers, timeout=10)
        if response.status_code == 200:
            items = parse_rss(response.content)
            for item in items[:5]:
                category, reason = classify_news(item['title'], item['summary'])
                if category:
                    news_items.append({
                        "title": item['title'],
                        "summary": item['summary'][:150],
                        "url": item['link'],
                        "source": "车东西",
                        "domain": category
                    })
    except Exception as e:
        print(f"⚠️ 车东西获取失败：{e}")
    
    # 4. 知乎 - AI/科技话题
    print("📡 获取知乎热榜...")
    try:
        zhihu_response = requests.get("https://www.zhihu.com/api/v3/feed/topstory/hot?limit=20", headers=headers, timeout=10)
        if zhihu_response.status_code == 200:
            zhihu_data = zhihu_response.json()
            for item in zhihu_data.get('data', [])[:10]:
                target = item.get('target', {})
                title = target.get('title', '')
                excerpt = target.get('excerpt', '')
                category, reason = classify_news(title, excerpt)
                if category:
                    news_items.append({
                        "title": title,
                        "summary": excerpt[:150],
                        "url": target.get('url', 'https://www.zhihu.com/hot'),
                        "source": "知乎",
                        "domain": category
                    })
    except Exception as e:
        print(f"⚠️ 知乎获取失败：{e}")
    
    # 去重（按 URL）
    seen_urls = set()
    unique_items = []
    for item in news_items:
        if item['url'] not in seen_urls:
            seen_urls.add(item['url'])
            unique_items.append(item)
    
    print(f"✅ 获取到 {len(unique_items)} 条有效新闻")
    return unique_items[:8]  # 最多 8 条

def format_message(news_items):
    """格式化飞书消息 - 按领域分类 + 专业点评"""
    today = datetime.now().strftime("%Y年%m月%d日")
    
    # 按领域分组
    domains = {}
    domain_order = ['AI', '金融', '科技', '汽车']  # 显示顺序
    
    for item in news_items:
        domain = item.get('domain', '科技')
        if domain not in domains:
            domains[domain] = []
        domains[domain].append(item)
    
    text_lines = [f"📅 {today} 金融/科技/AI/汽车 情报\n"]
    text_lines.append("━━━━━━━━━━━━━━\n")
    
    global_idx = 1
    for domain in domain_order:
        if domain not in domains:
            continue
        
        items = domains[domain]
        # 领域标题
        domain_emoji = {'AI': '🤖', '金融': '💰', '科技': '💻', '汽车': '🚗'}.get(domain, '📌')
        text_lines.append(f"【{domain_emoji} {domain}】")
        
        for news in items:
            text_lines.append(f"{global_idx}. {news['title']}")
            text_lines.append(f"   📰 来源：{news['source']}")
            text_lines.append(f"   🔗 {news['url']}")
            
            # 生成点评
            print(f"   💡 生成点评 {global_idx}/{len(news_items)}...")
            insight = generate_insight(news['title'], news['summary'], news['url'])
            text_lines.append(f"   💼 点评：{insight}")
            text_lines.append("")
            
            global_idx += 1
        
        text_lines.append("")
    
    text_lines.append("━━━━━━━━━━━━━━")
    text_lines.append("\n🤖 自动汇总 | 专业点评 | 来源可溯")
    
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
    
    receive_id_type = "open_id"
    url = f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type={receive_id_type}"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        "receive_id": chat_id,
        "msg_type": message["msg_type"],
        "content": json.dumps(message["content"])
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
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
    print("🚀 开始获取垂直领域新闻...\n")
    
    news_items = get_news()
    print(f"\n📰 筛选后：{len(news_items)} 条\n")
    
    if len(news_items) == 0:
        print("⚠️ 未获取到新闻，使用备用数据")
        news_items = [{
            "title": "暂无符合条件的新闻",
            "summary": "请检查新闻源或关键词配置",
            "url": "https://36kr.com/",
            "source": "系统",
            "category": "备用"
        }]
    
    print("📝 格式化消息...")
    message = format_message(news_items)
    
    print("\n🔑 获取飞书 Token...")
    access_token = get_feishu_token()
    
    if not access_token:
        print("⚠️ 无法获取 token")
        exit(1)
    
    print("📤 发送到飞书...")
    success = send_to_feishu(message, access_token)
    
    if success:
        print("✨ 完成！")
    else:
        print("⚠️ 发送失败")
        exit(1)

if __name__ == "__main__":
    main()
