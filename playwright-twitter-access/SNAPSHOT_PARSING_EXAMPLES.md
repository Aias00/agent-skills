# Snapshot 数据解析示例

本文档展示如何解析 Playwright browser 工具返回的 snapshot 数据。

---

## 实例 1: 解析用户信息

### Snapshot 结构
```json
{
  "document": {
    "banner": {
      "main": {
        "heading": "Elon Musk Verified account @elonmusk 98.1K posts",
        "text": "1,290 Following",
        "link": "235.5M Followers",
        "link": "Joined June 2009"
      }
    }
  }
}
```

### Python 解析代码
```python
import json

def parse_user_info_snapshot(snapshot_data):
    """解析用户信息 snapshop"""
    if not snapshot_data or 'document' not in snapshot_data:
        return None

    document = snapshot_data['document']
    banner = document.get('banner', {})
    main = banner.get('main', {})

    # 提取用户名
    user_data = {
        'username': None,
        'verified': False,
        'posts': 0,
        'following': 0,
        'followers': 0,
        'joined': None
    }

    # 遍历 main 的子元素
    for element in main:
        if 'heading' in element:
            # 用户名 + 帖子数
            heading_text = element['heading']
            parts = heading_text.split()
            if len(parts) >= 2:
                user_data['username'] = parts[0]
                user_data['verified'] = 'Verified' in heading_text

                # 提取帖子数
                for part in parts:
                    if 'posts' in part.lower():
                        num_str = part.split()[0]
                        if 'K' in num_str:
                            user_data['posts'] = float(num_str.replace('K', '')) * 1000
                        elif 'M' in num_str:
                            user_data['posts'] = float(num_str.replace('M', '')) * 1000000
                        else:
                            user_data['posts'] = int(num_str)

        elif 'text' in element:
            text = element['text']
            if 'Following' in text:
                # 提取关注数
                num_str = text.split()[0]
                if 'K' in num_str:
                    user_data['following'] = float(num_str.replace('K', '')) * 1000
                elif 'M' in num_str:
                    user_data['following'] = float(num_str.replace('M', '')) * 1000000
                else:
                    user_data['following'] = int(num_str)
            elif 'Followers' in text and isinstance(element, dict) and 'link' in element:
                # 提取粉丝数
                link_text = element['link']
                num_str = link_text.split()[0]
                if 'K' in num_str:
                    user_data['followers'] = float(num_str.replace('K', '')) * 1000
                elif 'M' in num_str:
                    user_data['followers'] = float(num_str.replace('M', '')) * 1000000
                else:
                    user_data['followers'] = int(num_str)

        elif 'link' in element and 'Joined' in element.get('link', ''):
            # 加入时间
            user_data['joined'] = element['link']

    return user_data

# 使用示例
with open('outputs/elonmusk_snapshot.json', 'r') as f:
    snapshot = json.load(f)

user_info = parse_user_info_snapshot(snapshot)
print(json.dumps(user_info, indent=2))
```

---

## 实例 2: 解析推文数据

### Snapshot 结构
```json
{
  "document": {
    "banner": {
      "main": {
        "region": "Conversation",
        "article": [
          {
            "link": "Elon Musk Verified account",
            "link": "@elonmusk",
            "link": "7 hours ago",
            "text": "推文内容...",
            "group": {
              "button": "3560 Replies",
              "button": "8964 reposts",
              "button": "71087 Likes",
              "link": "35753772 views"
            }
          }
        ]
      }
    }
  }
}
```

### Python 解析代码
```python
def parse_tweet_snapshot(snapshot_data):
    """解析推文 snapshot"""
    if not snapshot_data or 'document' not in snapshot_data:
        return None

    document = snapshot_data['document']
    banner = document.get('banner', {})
    main = banner.get('main', {})

    # 查找 Conversation region
    conversation_region = None
    for element in main:
        if isinstance(element, dict) and 'region' in element:
            if element.get('region') == 'Conversation':
                conversation_region = element
                break

    if not conversation_region:
        return None

    # 提取第一条 article（主推文）
    articles = conversation_region.get('article', [])
    if not articles:
        return None

    tweet_article = articles[0]

    # 解析推文数据
    tweet_data = {
        'author': None,
        'username': None,
        'verified': False,
        'time': None,
        'content': None,
        'stats': {
            'replies': 0,
            'reposts': 0,
            'likes': 0,
            'views': 0
        }
    }

    for element in tweet_article:
        if 'link' in element:
            link_text = element['link']

            # 用户信息
            if 'Verified account' in link_text:
                tweet_data['author'] = link_text.split(' Verified')[0]
                tweet_data['verified'] = True
            elif link_text.startswith('@'):
                tweet_data['username'] = link_text
            elif 'hours ago' in link_text.lower() or 'minutes ago' in link_text.lower():
                tweet_data['time'] = link_text

        elif 'text' in element:
            tweet_data['content'] = element['text']

        elif 'group' in element:
            # 统计数据
            group = element['group']
            for stat_element in group:
                if 'button' in stat_element:
                    stat_text = stat_element['button']
                    if 'Replies' in stat_text:
                        num_str = stat_text.split()[0]
                        tweet_data['stats']['replies'] = parse_number(num_str)
                    elif 'reposts' in stat_text.lower():
                        num_str = stat_text.split()[0]
                        tweet_data['stats']['reposts'] = parse_number(num_str)
                    elif 'Likes' in stat_text:
                        num_str = stat_text.split()[0]
                        tweet_data['stats']['likes'] = parse_number(num_str)
                elif 'link' in stat_element and 'views' in stat_element['link']:
                    num_str = stat_element['link'].split()[0]
                    tweet_data['stats']['views'] = parse_number(num_str)

    return tweet_data

def parse_number(num_str):
    """解析数字字符串（支持 K/M 后缀）"""
    num_str = num_str.replace(',', '').replace('.', '')  # 移除分隔符

    if 'K' in num_str:
        return int(float(num_str.replace('K', '')) * 1000)
    elif 'M' in num_str:
        return int(float(num_str.replace('M', '')) * 1000000)
    elif 'B' in num_str:
        return int(float(num_str.replace('B', '')) * 1000000000)
    else:
        return int(num_str) if num_str.isdigit() else 0

# 使用示例
with open('outputs/2027644868881957020_tweet_snapshot.json', 'r') as f:
    snapshot = json.load(f)

tweet_data = parse_tweet_snapshot(snapshot)
print(json.dumps(tweet_data, indent=2))
```

---

## 实例 3: 解析回复列表

### Python 解析代码
```python
def parse_replies_snapshot(snapshot_data):
    """解析回复列表 snapshot"""
    if not snapshot_data or 'document' not in snapshot_data:
        return []

    document = snapshot_data['document']
    banner = document.get('banner', {})
    main = banner.get('main', {})

    # 查找 Conversation region
    conversation_region = None
    for element in main:
        if isinstance(element, dict) and 'region' in element:
            if element.get('region') == 'Conversation':
                conversation_region = element
                break

    if not conversation_region:
        return []

    # 提取所有 article（主推文 + 回复）
    articles = conversation_region.get('article', [])
    if not articles or len(articles) < 2:
        return []

    # 跳过第一条（主推文），提取回复
    replies = []
    for article in articles[1:]:  # 从第二条开始是回复
        reply_data = {
            'author': None,
            'username': None,
            'verified': False,
            'time': None,
            'content': None,
            'images': []
        }

        for element in article:
            if 'link' in element:
                link_text = element['link']

                if 'Verified account' in link_text:
                    reply_data['author'] = link_text.split(' Verified')[0]
                    reply_data['verified'] = True
                elif link_text.startswith('@'):
                    reply_data['username'] = link_text
                elif 'hours ago' in link_text.lower() or 'minutes ago' in link_text.lower():
                    reply_data['time'] = link_text
                elif link_text == 'Image':
                    # 图片链接
                    if '/url' in element:
                        reply_data['images'].append(element['/url'])

            elif 'text' in element:
                reply_data['content'] = element['text']

        replies.append(reply_data)

    return replies

# 使用示例
with open('outputs/2027644868881957020_tweet_snapshot.json', 'r') as f:
    snapshot = json.load(f)

replies = parse_replies_snapshot(snapshot)
print(f"找到 {len(replies)} 条回复:")
for i, reply in enumerate(replies, 1):
    print(f"\n回复 {i}:")
    print(f"  作者: {reply['author']} (@{reply['username']})")
    print(f"  时间: {reply['time']}")
    print(f"  内容: {reply['content'][:50]}...")
```

---

## 实例 4: 完整综合解析

```python
def parse_twitter_snapshot(snapshot_data):
    """综合解析 Twitter snapshot"""
    if not snapshot_data or 'document' not in snapshot_data:
        return None

    document = snapshot_data['document']
    banner = document.get('banner', {})
    main = banner.get('main', {})

    result = {
        'user': None,
        'tweets': [],
        'replies': []
    }

    # 检测页面类型
    page_type = None
    for element in main:
        if 'heading' in element and 'Verified account' in element['heading']:
            # 可能是用户主页或推文详情
            if any('region' in e and 'Conversation' in e['region'] for e in main if isinstance(e, dict)):
                page_type = 'tweet'
            else:
                page_type = 'user'
            break

    if page_type == 'user':
        # 解析用户主页
        result['user'] = parse_user_info_snapshot(snapshot_data)
        # TODO: 解析推文列表
    elif page_type == 'tweet':
        # 解析推文详情
        result['tweets'] = [parse_tweet_snapshot(snapshot_data)]
        result['replies'] = parse_replies_snapshot(snapshot_data)

    return result

# 使用示例
with open('outputs/2027644868881957020_tweet_snapshot.json', 'r') as f:
    snapshot = json.load(f)

parsed_data = parse_twitter_snapshot(snapshot)
print(json.dumps(parsed_data, indent=2))
```

---

## 📝 解析器使用流程

### 1. 获取 Snapshot
```bash
browser action=snapshot depth=5 refs=role > snapshot.json
```

### 2. 加载 JSON
```python
import json
with open('snapshot.json', 'r') as f:
    snapshot = json.load(f)
```

### 3. 调用解析器
```python
# 用户信息
user_info = parse_user_info_snapshot(snapshot)

# 推文数据
tweet_data = parse_tweet_snapshot(snapshot)

# 回复列表
replies = parse_replies_snapshot(snapshot)

# 综合解析
parsed = parse_twitter_snapshot(snapshot)
```

### 4. 处理结果
```python
print(json.dumps(parsed, indent=2))
# 或
import pandas as pd
df = pd.json_normalize(parsed)
```

---

## 📊 输出格式示例

### 用户信息
```json
{
  "username": "elonmusk",
  "verified": true,
  "posts": 98100,
  "following": 1290,
  "followers": 235500000,
  "joined": "Joined June 2009"
}
```

### 推文数据
```json
{
  "author": "Elon Musk",
  "username": "elonmusk",
  "verified": true,
  "time": "7 hours ago",
  "content": "推文内容...",
  "stats": {
    "replies": 3560,
    "reposts": 8964,
    "likes": 71087,
    "views": 35753772
  }
}
```

### 回复列表
```json
[
  {
    "author": "Anas",
    "username": "Anas_founder",
    "verified": true,
    "time": "6 hours ago",
    "content": "Elon musk's keyboard",
    "images": []
  },
  {
    "author": "Soda Pop Comix",
    "username": "SodaPopComix",
    "verified": true,
    "time": "12 minutes ago",
    "content": "",
    "images": ["https://x.com/..."]
  }
]
```

---

## 💡 最佳实践

### 1. 错误处理
```python
def safe_parse(snapshot_data):
    try:
        return parse_tweet_snapshot(snapshot_data)
    except Exception as e:
        print(f"解析失败: {e}")
        return None
```

### 2. 数据验证
```python
def validate_tweet_data(tweet_data):
    if not tweet_data:
        return False
    required_fields = ['author', 'username', 'content']
    return all(field in tweet_data for field in required_fields)
```

### 3. 批量处理
```python
import os
import glob

def batch_parse_snapshots(directory):
    results = []
    for json_file in glob.glob(f"{directory}/*.json"):
        with open(json_file, 'r') as f:
            snapshot = json.load(f)
        parsed = parse_tweet_snapshot(snapshot)
        if parsed:
            results.append(parsed)
    return results
```

---

*更新时间: 2026-02-28*