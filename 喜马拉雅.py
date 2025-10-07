import requests
import json
import time
import random
import hashlib
from bs4 import BeautifulSoup
import re
import pandas as pd
from urllib.parse import urljoin, urlparse
import os
from datetime import datetime

class XimalayaSpider:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://m.ximalaya.com"
        self.api_base = "https://mobile.ximalaya.com"
        
        # 移动端headers
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://m.ximalaya.com/',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        self.session.headers.update(self.headers)
        
        # 创建输出目录
        self.output_dir = "ximalaya_data"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def get_timestamp(self):
        """获取当前时间戳"""
        return str(int(time.time() * 1000))

    def safe_request(self, url, params=None, method='GET', retry=3):
        """安全的请求函数，包含重试机制"""
        for i in range(retry):
            try:
                if method.upper() == 'GET':
                    response = self.session.get(url, params=params, timeout=15)
                else:
                    response = self.session.post(url, data=params, timeout=15)
                
                if response.status_code == 200:
                    return response
                elif response.status_code == 403:
                    print("访问被拒绝，可能触发了反爬机制")
                elif response.status_code == 404:
                    print("页面不存在")
                else:
                    print(f"请求失败，状态码: {response.status_code}")
                
            except Exception as e:
                print(f"请求异常: {e}")
            
            # 重试延迟
            if i < retry - 1:
                sleep_time = random.uniform(2, 5)
                print(f"等待 {sleep_time:.1f} 秒后重试...")
                time.sleep(sleep_time)
        
        return None

    def get_homepage_data(self):
        """获取首页数据"""
        print("正在获取首页数据...")
        url = self.base_url
        response = self.safe_request(url)
        
        if not response:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        homepage_data = {
            'title': self.get_title(soup),
            'metadata': self.get_metadata(soup),
            'navigation': self.extract_navigation(soup),
            'recommendations': self.extract_recommendations(soup),
            'hot_categories': self.extract_hot_categories(soup),
            'crawl_time': datetime.now().isoformat()
        }
        
        return homepage_data

    def get_title(self, soup):
        """获取页面标题"""
        title_tag = soup.find('title')
        return title_tag.text.strip() if title_tag else "喜马拉雅"

    def get_metadata(self, soup):
        """获取页面元数据"""
        metadata = {}
        meta_tags = soup.find_all('meta')
        for tag in meta_tags:
            name = tag.get('name') or tag.get('property')
            content = tag.get('content')
            if name and content:
                metadata[name] = content
        return metadata

    def extract_navigation(self, soup):
        """提取导航菜单"""
        navigation = []
        nav_selectors = [
            'a[class*="nav"]',
            'a[class*="menu"]', 
            'a[class*="tab"]',
            '.nav a',
            '.menu a'
        ]
        
        for selector in nav_selectors:
            elements = soup.select(selector)
            for elem in elements:
                text = elem.get_text(strip=True)
                href = elem.get('href')
                if text and href and len(text) < 20:
                    navigation.append({
                        'text': text,
                        'url': urljoin(self.base_url, href)
                    })
        
        return navigation[:15]  # 限制数量

    def extract_recommendations(self, soup):
        """提取推荐内容"""
        recommendations = []
        
        # 多种选择器尝试
        selectors = [
            '.recommend-item',
            '.hot-item', 
            '.album-item',
            '.track-item',
            '[class*="recommend"]',
            '[class*="hot"]',
            '[class*="album"]'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            for elem in elements[:20]:  # 限制数量
                title_elem = elem.find(['h1', 'h2', 'h3', 'h4', 'a'])
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    if title:
                        item_data = {
                            'title': title,
                            'type': 'unknown',
                            'url': ''
                        }
                        
                        # 获取链接
                        link = elem.find('a', href=True)
                        if link:
                            item_data['url'] = urljoin(self.base_url, link['href'])
                        
                        # 判断类型
                        if any(keyword in title for keyword in ['专辑', '节目', 'album']):
                            item_data['type'] = 'album'
                        elif any(keyword in title for keyword in ['声音', '音频', 'track']):
                            item_data['type'] = 'track'
                        
                        recommendations.append(item_data)
        
        # 去重
        seen_titles = set()
        unique_recommendations = []
        for item in recommendations:
            if item['title'] not in seen_titles:
                seen_titles.add(item['title'])
                unique_recommendations.append(item)
        
        return unique_recommendations[:30]

    def extract_hot_categories(self, soup):
        """提取热门分类"""
        categories = []
        
        # 查找分类相关元素
        category_indicators = ['分类', '频道', 'Category', 'category']
        for indicator in category_indicators:
            elements = soup.find_all(string=re.compile(indicator))
            for elem in elements:
                parent = elem.parent
                if parent:
                    # 查找父元素中的链接
                    links = parent.find_all('a', href=True)
                    for link in links:
                        text = link.get_text(strip=True)
                        if text and text != indicator:
                            categories.append({
                                'name': text,
                                'url': urljoin(self.base_url, link['href'])
                            })
        
        return categories[:20]

    def search_content(self, keyword, page=1, search_type='album'):
        """搜索内容"""
        print(f"正在搜索: {keyword} (第{page}页)")
        
        search_url = f"{self.api_base}/mobile/v1/search"
        params = {
            'core': search_type,
            'kw': keyword,
            'page': page,
            'spellchecker': 'true',
            'rows': 20,
            'condition': 'relation',
            'device': 'iPhone',
            'fq': '',
            'paidFilter': 'false',
            'scope': 'all',
            'ts': self.get_timestamp()
        }
        
        response = self.safe_request(search_url, params)
        if not response:
            return None
        
        try:
            data = response.json()
            return self.parse_search_results(data, search_type)
        except:
            return self.fallback_search(keyword, page)

    def parse_search_results(self, data, search_type):
        """解析搜索结果"""
        if not data:
            return []
        
        results = []
        
        if search_type == 'album' and 'data' in data:
            albums = data['data'].get('docs', [])
            for album in albums:
                results.append({
                    'id': album.get('id'),
                    'title': album.get('title'),
                    'cover': album.get('cover'),
                    'play_count': album.get('playCount'),
                    'track_count': album.get('trackCount'),
                    'is_paid': album.get('isPaid', False),
                    'type': 'album',
                    'anchor': album.get('anchorName'),
                    'category': album.get('categoryTitle')
                })
        
        elif search_type == 'track' and 'data' in data:
            tracks = data['data'].get('docs', [])
            for track in tracks:
                results.append({
                    'id': track.get('id'),
                    'title': track.get('title'),
                    'album_id': track.get('albumId'),
                    'album_title': track.get('albumTitle'),
                    'duration': track.get('duration'),
                    'play_count': track.get('playCount'),
                    'is_paid': track.get('isPaid', False),
                    'type': 'track'
                })
        
        return results

    def fallback_search(self, keyword, page):
        """备用搜索方法"""
        print("使用备用搜索方法...")
        search_url = f"https://m.ximalaya.com/search/{quote(keyword)}"
        response = self.safe_request(search_url)
        
        if not response:
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        # 尝试查找专辑卡片
        album_cards = soup.select('[class*="album"], [class*="item"]')
        for card in album_cards[:20]:
            title_elem = card.find(['h1', 'h2', 'h3', 'h4', 'a'])
            if title_elem:
                title = title_elem.get_text(strip=True)
                if title and len(title) > 3:
                    results.append({
                        'title': title,
                        'type': 'album',
                        'url': ''
                    })
        
        return results

    def get_album_detail(self, album_id):
        """获取专辑详情"""
        print(f"获取专辑详情: {album_id}")
        
        url = f"{self.api_base}/mobile/v1/album"
        params = {
            'albumId': album_id,
            'ts': self.get_timestamp()
        }
        
        response = self.safe_request(url, params)
        if not response:
            return None
        
        try:
            data = response.json()
            return self.parse_album_detail(data)
        except Exception as e:
            print(f"解析专辑详情失败: {e}")
            return None

    def parse_album_detail(self, data):
        """解析专辑详情"""
        if not data or 'data' not in data:
            return None
        
        album = data['data']
        
        # 获取音轨列表
        tracks = self.get_album_tracks(album['albumId'])
        
        album_info = {
            'album_id': album.get('albumId'),
            'title': album.get('title'),
            'cover_url': album.get('cover'),
            'description': album.get('intro', '')[:500],
            'play_count': album.get('playCount', 0),
            'track_count': album.get('trackCount', 0),
            'subscribe_count': album.get('subscribeCount', 0),
            'is_finished': album.get('isFinished', False),
            'is_paid': album.get('isPaid', False),
            'category': album.get('categoryTitle'),
            'anchor': {
                'name': album.get('anchorName'),
                'id': album.get('anchorId')
            },
            'tracks': tracks,
            'free_tracks_count': len([t for t in tracks if not t.get('is_paid', True)]),
            'crawl_time': datetime.now().isoformat()
        }
        
        return album_info

    def get_album_tracks(self, album_id, page=1, page_size=50):
        """获取专辑音轨列表"""
        url = f"{self.api_base}/mobile/v1/album/track"
        params = {
            'albumId': album_id,
            'pageId': page,
            'pageSize': page_size,
            'ts': self.get_timestamp()
        }
        
        response = self.safe_request(url, params)
        if not response:
            return []
        
        try:
            data = response.json()
            tracks = data.get('data', {}).get('list', [])
            
            parsed_tracks = []
            for track in tracks:
                parsed_tracks.append({
                    'track_id': track.get('trackId'),
                    'title': track.get('title'),
                    'duration': track.get('duration'),
                    'play_count': track.get('playCount'),
                    'is_paid': track.get('isPaid', False),
                    'is_free': track.get('isFree', False),
                    'order_num': track.get('orderNum')
                })
            
            return parsed_tracks
        except:
            return []

    def get_track_detail(self, track_id):
        """获取音轨详情"""
        print(f"获取音轨详情: {track_id}")
        
        url = f"{self.api_base}/mobile/track/v2/baseInfo"
        params = {
            'trackId': track_id,
            'ts': self.get_timestamp()
        }
        
        response = self.safe_request(url, params)
        if not response:
            return None
        
        try:
            data = response.json()
            track = data.get('data', {})
            
            track_info = {
                'track_id': track.get('trackId'),
                'title': track.get('title'),
                'album_id': track.get('albumId'),
                'album_title': track.get('albumTitle'),
                'duration': track.get('duration'),
                'play_count': track.get('playCount'),
                'comment_count': track.get('commentCount'),
                'like_count': track.get('likeCount'),
                'is_paid': track.get('isPaid', False),
                'is_free': track.get('isFree', False),
                'cover_url': track.get('cover'),
                'description': track.get('intro', '')[:300],
                'crawl_time': datetime.now().isoformat()
            }
            
            return track_info
        except Exception as e:
            print(f"解析音轨详情失败: {e}")
            return None

    def get_categories(self):
        """获取分类列表"""
        print("获取分类列表...")
        
        url = f"{self.api_base}/mobile/category/v2/list"
        params = {
            'ts': self.get_timestamp()
        }
        
        response = self.safe_request(url, params)
        if not response:
            return []
        
        try:
            data = response.json()
            categories = data.get('data', [])
            
            parsed_categories = []
            for cat in categories:
                parsed_categories.append({
                    'id': cat.get('id'),
                    'name': cat.get('name'),
                    'cover_url': cat.get('cover'),
                    'description': cat.get('describe')
                })
            
            return parsed_categories
        except:
            return []

    def get_hot_recommends(self):
        """获取热门推荐"""
        print("获取热门推荐...")
        
        url = f"{self.api_base}/mobile/discovery/v2/hotRecommends"
        params = {
            'ts': self.get_timestamp()
        }
        
        response = self.safe_request(url, params)
        if not response:
            return []
        
        try:
            data = response.json()
            recommends = data.get('data', [])
            
            parsed_recommends = []
            for rec in recommends:
                parsed_recommends.append({
                    'id': rec.get('id'),
                    'title': rec.get('title'),
                    'cover_url': rec.get('cover'),
                    'description': rec.get('describe', ''),
                    'type': rec.get('contentType')
                })
            
            return parsed_recommends
        except:
            return []

    def save_data(self, data, filename, format_type='json'):
        """保存数据到文件"""
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            if format_type == 'json':
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            elif format_type == 'csv' and isinstance(data, list):
                df = pd.DataFrame(data)
                df.to_csv(filepath, index=False, encoding='utf-8-sig')
            
            print(f"数据已保存: {filepath}")
            return True
        except Exception as e:
            print(f"保存文件失败: {e}")
            return False

    def generate_report(self, all_data):
        """生成爬取报告"""
        report = {
            'crawl_time': datetime.now().isoformat(),
            'summary': {
                'total_albums_crawled': len(all_data.get('album_details', [])),
                'total_tracks_crawled': len(all_data.get('track_details', [])),
                'total_categories': len(all_data.get('categories', [])),
                'total_recommendations': len(all_data.get('hot_recommends', []))
            },
            'file_outputs': [
                'homepage_data.json',
                'search_results.json', 
                'album_details.json',
                'track_details.json',
                'categories.json',
                'hot_recommends.json'
            ]
        }
        
        self.save_data(report, 'crawl_report.json')
        return report

def main():
    """主函数 - 直接运行即可"""
    print("=" * 60)
    print("喜马拉雅爬虫 v1.0")
    print("开始爬取公开内容...")
    print("=" * 60)
    
    spider = XimalayaSpider()
    all_data = {}
    
    try:
        # 1. 获取首页数据
        print("\n[1/6] 获取首页数据...")
        homepage_data = spider.get_homepage_data()
        if homepage_data:
            spider.save_data(homepage_data, 'homepage_data.json')
            all_data['homepage'] = homepage_data
            print(f"✓ 获取首页成功，找到 {len(homepage_data.get('recommendations', []))} 个推荐内容")
        
        # 2. 搜索示例内容
        print("\n[2/6] 搜索示例内容...")
        search_results = spider.search_content("科技", 1, 'album')
        if search_results:
            spider.save_data(search_results, 'search_results.json')
            all_data['search_results'] = search_results
            print(f"✓ 搜索成功，找到 {len(search_results)} 个专辑")
        
        # 3. 获取分类列表
        print("\n[3/6] 获取分类列表...")
        categories = spider.get_categories()
        if categories:
            spider.save_data(categories, 'categories.json')
            all_data['categories'] = categories
            print(f"✓ 获取分类成功，找到 {len(categories)} 个分类")
        
        # 4. 获取热门推荐
        print("\n[4/6] 获取热门推荐...")
        hot_recommends = spider.get_hot_recommends()
        if hot_recommends:
            spider.save_data(hot_recommends, 'hot_recommends.json')
            all_data['hot_recommends'] = hot_recommends
            print(f"✓ 获取热门推荐成功，找到 {len(hot_recommends)} 个推荐")
        
        # 5. 获取专辑详情（示例）
        print("\n[5/6] 获取专辑详情示例...")
        album_details = []
        if search_results:
            # 取前2个专辑获取详情
            for album in search_results[:2]:
                album_id = album.get('id')
                if album_id:
                    detail = spider.get_album_detail(album_id)
                    if detail:
                        album_details.append(detail)
                    time.sleep(1)  # 请求间隔
            
            if album_details:
                spider.save_data(album_details, 'album_details.json')
                all_data['album_details'] = album_details
                print(f"✓ 获取专辑详情成功，共 {len(album_details)} 个专辑")
        
        # 6. 获取音轨详情（示例）
        print("\n[6/6] 获取音轨详情示例...")
        track_details = []
        if album_details:
            for album in album_details:
                tracks = album.get('tracks', [])
                if tracks:
                    # 取前2个音轨获取详情
                    for track in tracks[:2]:
                        track_id = track.get('track_id')
                        if track_id:
                            detail = spider.get_track_detail(track_id)
                            if detail:
                                track_details.append(detail)
                            time.sleep(1)  # 请求间隔
            
            if track_details:
                spider.save_data(track_details, 'track_details.json')
                all_data['track_details'] = track_details
                print(f"✓ 获取音轨详情成功，共 {len(track_details)} 个音轨")
        
        # 生成报告
        print("\n生成爬取报告...")
        report = spider.generate_report(all_data)
        
        print("\n" + "=" * 60)
        print("爬取完成！")
        print("=" * 60)
        print(f"输出目录: {spider.output_dir}")
        print(f"爬取时间: {report['crawl_time']}")
        print(f"总计爬取:")
        print(f"  - 专辑: {report['summary']['total_albums_crawled']}")
        print(f"  - 音轨: {report['summary']['total_tracks_crawled']}")
        print(f"  - 分类: {report['summary']['total_categories']}")
        print(f"  - 推荐: {report['summary']['total_recommendations']}")
        
    except Exception as e:
        print(f"爬取过程中出现错误: {e}")
    
    finally:
        print("\n" + "=" * 60)
        print("注意事项:")
        print("1. 本爬虫仅用于爬取公开内容")
        print("2. 请遵守网站的使用条款")
        print("3. 设置合理的请求频率")
        print("4. 仅用于学习和研究目的")
        print("=" * 60)

if __name__ == "__main__":
    # 直接运行
    main()