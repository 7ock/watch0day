from typing import List, Dict
import feedparser
from .fetcher import Fetcher
from datetime import datetime, timezone, timedelta


class RSSFetcher(Fetcher):
    def __init__(self, config: Dict):
        super().__init__(config)
        self.sources = [
            {
                "url": "https://feeds.feedburner.com/TheHackersNews",
                "name": "The Hacker News",
                "type": "news"
            },
            {
                "url": "https://www.exploit-db.com/rss.xml",
                "name": "Exploit-DB",
                "type": "exploit"
            },
            {
                "url": "https://www.zerodayinitiative.com/rss/upcoming/",
                "name": "Zero Day Initiative",
                "type": "vulnerability"
            }
        ]

    def fetch(self) -> List[dict]:
        results = []
        for source in self.sources:
            max_retries = 3
            timeout_seconds = 15  # Increased from 10 to 15 seconds
            
            for attempt in range(max_retries):
                try:
                    # 使用requests获取RSS内容并设置超时
                    import requests
                    from requests.exceptions import RequestException
                    try:
                        proxies = {
                            'http': 'http://127.0.0.1:7890',
                            'https': 'http://127.0.0.1:7890'
                        } if 'proxy' in self.config and self.config['proxy'] else None
                        response = requests.get(source["url"], 
                                             headers={'User-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'},
                                             timeout=(3.05, timeout_seconds),
                                             proxies=proxies)  # Connect timeout 3.05s, read timeout 10s
                    except RequestException as e:
                        raise Exception(f"Network error: {str(e)}")
                    response.raise_for_status()
                    feed = feedparser.parse(response.content)
                    
                    if feed.bozo and feed.bozo_exception:
                        raise Exception(f"RSS解析错误: {feed.bozo_exception}")
                    
                    for entry in feed.entries[:50]:
                        title = entry.title.lower()
                        desc = entry.description.lower() if hasattr(entry, 'description') else ""
                        if any(kw in title or kw in desc for kw in self.config["keywords"]):
                            date = datetime(*entry.published_parsed[:6]).astimezone(timezone(timedelta(hours=8)))
                            results.append({
                                "source": source["name"],
                                "title": entry.title,
                                "link": entry.link,
                                "date": date.strftime("%Y-%m-%d %H:%M"),
                                "type": source["type"],
                                "summary": entry.description[:250] + "..." if hasattr(entry, 'description') else ""
                            })
                    break  # 成功则跳出重试循环
                except Exception as e:
                    if attempt == max_retries - 1:  # 最后一次尝试仍然失败
                        print(f"[{source['name']}] 抓取失败(尝试 {attempt+1}/{max_retries}): {e}")
                    else:
                        print(f"[{source['name']}] 抓取失败(尝试 {attempt+1}/{max_retries}), 将在{timeout_seconds}秒后重试: {e}")
                        import time
                        time.sleep(timeout_seconds)
        return results
