# coding = utf-8
# !/usr/bin/python
# 灰太狼 2025.09.02 sharkapp第三版
import hashlib
import re,sys,uuid,json,base64,urllib3
import time
import math
from Crypto.Cipher import AES
from base.spider import Spider
from Crypto.Util.Padding import pad,unpad
sys.path.append('..')
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class Spider(Spider):
    xurl,key,iv,init_data,search_verify = '','','','',''
    headerx = {
        'User-Agent': 'Dalvik/1.5.0 (Linux; U; Android 13; vivo Build/V2171A&sign=32e21d0ba2c2aa62770e4cfcafafa71dH6h7oR!@#$%^&*()_+-=[]{}|;:,.<>?WitQNBseoaa2b6822833bd08e7762e3b2ab050f47)',
    }
    def getName(self):
        return "首页"

    def init(self, extend):
        js1=json.loads(extend)
        host = js1['host']
        self.key1 = js1['hostkey']
        self.key2 = js1['parseskey']
        self.key3 = js1['listkey']
        if not re.match(r'^https?:\/\/[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*(:\d+)?(\/)?$',host):
            abc = self.fetch(host, headers=self.headerx, timeout=10, verify=False).text.rstrip('/')
            bcd = self.decrypt(abc,self.key1)
            host = json.loads(bcd)[0]
        api = js1.get('api','/shark/api.php?action=configs')
        api2 = js1.get('api', '/api.php/v1.')
        api3 = js1.get('api','/shark/api.php?action=parsevod')
        self.xurl = host + api
        self.xurl2 = host + api2
        self.xurl3 = host + api3
        res = self.fetch(self.xurl , headers=self.headerx, verify=False).content.decode('utf-8')
        response = self.decrypt(res,self.key2) or self.decrypt(res,self.key3)
        response_dict = json.loads(response) 
        ua_value = response_dict.get("ua", "")
        if not ua_value:  
            config_obj = response_dict.get("config", {})
            ua_value = config_obj.get("ua", "")
        ua_part1 = hashlib.md5(ua_value.encode('utf-8')).hexdigest()
        ua_part2 = '0000000000000000'
        current_timestamp = round(time.time() * 1000)  
        timestamp_str = f"a.{math.floor(current_timestamp)}"
        ua_part3 = hashlib.md5(timestamp_str.encode('utf-8')).hexdigest()
        self.headerx['ua'] = ua_part1 + ua_part2 + ua_part3
        self.headerx['version'] = response_dict['config']['versionName']
        playparse = response_dict['playerinfos']
        self.playerinfos = playparse
        self.key4 = response_dict['config']['hulue'].split('&')[0]

    def homeContent(self, filter):
        url = f'{self.xurl2}home/types'
        kjs = self.fetch(url , headers=self.headerx, verify=False).content.decode('utf-8')
        kjso = self.decrypt(kjs, self.key3) or self.decrypt(kjs, self.key2)
        kjson = json.loads(kjso)
        result = {"class": []}
        for i in kjson['data']['types']:
            if not(i['type_name'] in {'全部', 'QQ', 'juo.one','推荐','首页'} or '企鹅群' in i['type_name']):
                result['class'].append({
                    "type_id": i['type_id'],
                    "type_name": i['type_name']
                })
        return result

    def homeVideoContent(self):
        videos = []
        url1 = f'{self.xurl2}home/types'
        kjs1 = self.fetch(url1, headers=self.headerx, verify=False).content.decode('utf-8')
        kjso1 = self.decrypt(kjs1, self.key3) or self.decrypt(kjs1, self.key2)
        kjson1 = json.loads(kjso1)
        hometype = kjson1['data']['types'][0]['type_id']
        url = f'{self.xurl2}home/data?type_id={hometype}'
        kjs = self.fetch(url, headers=self.headerx, verify=False).content.decode('utf-8')
        kjso = self.decrypt(kjs, self.key3) or self.decrypt(kjs, self.key2)
        kjson = json.loads(kjso)
        for i in kjson['data']['verLandList']:
            for item in i['vertical_lands']:
                vod_id = item['vod_id']
                name = item['vod_name']
                pic = item['vod_pic']
                remarks = item['vod_remarks']
                video = {
                    "vod_id": vod_id,
                    "vod_name": name,
                    "vod_pic": pic,
                    "vod_remarks": remarks
                }
                videos.append(video)
        return {'list': videos}

    def categoryContent(self, cid, pg, filter, ext):
        videos = []
        payload = {
            'area': ext.get('area','全部地区'),
            'year': ext.get('year','全部年代'),
            'type_id': cid,
            'rank': ext.get('sort','最新'),
            'lang': ext.get('lang','全部语言'),
            'type': ext.get('class','全部类型')
        }
        url = f'{self.xurl2}classify/content?page={pg}'
        res = self.post(url=url, headers=self.headerx,data=payload, verify=False).content.decode('utf-8')
        kjso = self.decrypt(res, self.key3) or self.decrypt(res, self.key2)
        kjson = json.loads(kjso)
        encrypted_data = kjson['data']
        for i in encrypted_data['video_list']:
            id = i['vod_id']
            name = i['vod_name']
            pic = i['vod_pic']
            remarks = i.get('vod_remarks','')
            video = {
                "vod_id": id,
                "vod_name": name,
                "vod_pic": pic,
                "vod_remarks": remarks
            }
            videos.append(video)
        return {'list': videos, 'page': pg, 'pagecount': 9999, 'limit': 90, 'total': 999999}

    def detailContent(self, ids):
        did = ids[0]
        url = f'{self.xurl2}player/details?vod_id={did}'
        kjs = self.fetch(url, headers=self.headerx, verify=False).content.decode('utf-8')
        kjso = self.decrypt(kjs, self.key3) or self.decrypt(kjs, self.key2)
        kjson = json.loads(kjso)['data']['detail']
        videos = []
        play_form = ''
        play_url = ''
        lineid = 1
        name_count = {}
        for line in kjson['play_url_list']:
            keywords = {'防走丢', '群', '防失群', '官网'}
            player_show = line['from']
            if any(keyword in player_show for keyword in keywords):
                player_show = f'{lineid}线'
                line['from'] = player_show
            count = name_count.get(player_show, 0) + 1
            name_count[player_show] = count
            if count > 1:
                line['from'] = f"{player_show}{count}"
            play_form += line['from'] + '$$$'
            kurls = ""
            for vod in line['urls']:
                kurls += f"{str(vod['name'])}${line['from']},{vod['url']}#"
            kurls = kurls.rstrip('#')
            play_url += kurls + '$$$'
            lineid += 1
        play_form = play_form.rstrip('$$$')
        play_url = play_url.rstrip('$$$')
        videos.append({
            "vod_id": did,
            "vod_name": kjson['vod_name'],
            "vod_actor": kjson['vod_actor'].replace('演员', ''),
            "vod_director": kjson.get('vod_director', '').replace('导演', ''),
            "vod_content": kjson['vod_content'],
            "vod_remarks": kjson['vod_remarks'],
            "vod_year": kjson['vod_year'] + '年',
            "vod_area": kjson['vod_class'],
            "vod_play_from": play_form,
            "vod_play_url": play_url
        })
        return {'list': videos}

    def playerContent(self, flag, id, vipFlags):
        url = ''
        aid = id.split(',')
        uid = aid[0]
        kurl = aid[1]
        playerinfos = self.playerinfos
        playjk = self.find_player_info(playerinfos,uid)
        playjie = self.decrypt(playjk,self.key4)
        kjso = self.fetch(f"{playjie}{kurl}",headers=self.headerx).json()
        url = kjso['url']
        res = {"parse": 0, "playUrl": '', "url": url, "header": {'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 14; 23113RK12C Build/SKQ1.231004.001)'}}
        return res

    def searchContent(self, key, quick, pg="1"):
        videos = []
        data = self.fetch(f'{self.xurl2}search/data?wd={key}&type_id=0&page={pg}',headers=self.headerx, verify=False).content.decode('utf-8')
        kjso = self.decrypt(data, self.key3)or self.decrypt(data, self.key2)
        kjson = json.loads(kjso)
        for i in kjson['data']['search_data']:
            videos.append({
                "vod_id": i['vod_id'],
                "vod_name": i['vod_name'],
                "vod_pic": i['vod_pic'],
                "vod_remarks": i['vod_remarks']
            })
        return {'list': videos, 'page': pg, 'pagecount': 9999, 'limit': 90, 'total': 999999}

    def localProxy(self, params):
        if params['type'] == "m3u8":
            return self.proxyM3u8(params)
        elif params['type'] == "media":
            return self.proxyMedia(params)
        elif params['type'] == "ts":
            return self.proxyTs(params)
        return None

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def decrypt(self, encrypted_data_b64, key):
        try:
            if isinstance(encrypted_data_b64, bytes):
                encrypted_data_b64 = encrypted_data_b64.decode('utf-8', errors='ignore')
            encrypted_data_b64 = re.sub(r'[^A-Za-z0-9+/=]', '', encrypted_data_b64)
            encrypted_data_b64 = encrypted_data_b64.replace('-', '+').replace('_', '/')
            if len(encrypted_data_b64) % 4 != 0:
                encrypted_data_b64 += '=' * (4 - len(encrypted_data_b64) % 4)
            encrypted_data = base64.b64decode(encrypted_data_b64)
            key_bytes = key.encode('utf-8')
            cipher = AES.new(key_bytes, AES.MODE_ECB)
            decrypted_padded = cipher.decrypt(encrypted_data)
            decrypted = unpad(decrypted_padded, AES.block_size)
            return decrypted.decode('utf-8')
        except Exception as e:
            return None

    def encrypt(self, plaintext_data):
        key_bytes = self.key.encode('utf-8')
        data_bytes = plaintext_data.encode('utf-8')
        padded_data = pad(data_bytes, AES.block_size)
        cipher = AES.new(key_bytes, AES.MODE_ECB)
        encrypted_bytes = cipher.encrypt(padded_data)
        encrypted_data_b64 = base64.b64encode(encrypted_bytes).decode('utf-8')
        return encrypted_data_b64

    def ocr(self, base64img):
        dat2 = self.post("https://api.nn.ci/ocr/b64/text", data=base64img, headers=self.headerx, verify=False).text
        if dat2:
            return dat2
        else:
            return None

    def verification(self):
        random_uuid = str(uuid.uuid4())
        dat = self.fetch(f'{self.xurl}.verify/create?key={random_uuid}',headers=self.headerx, verify=False).content
        base64_img = base64.b64encode(dat).decode('utf-8')
        if not dat:
            return None
        code = self.ocr(base64_img)
        if not code:
            return None
        code = self.replace_code(code)
        if not (len(code) == 4 and code.isdigit()):
            return None
        return {'uuid': random_uuid, 'code': code}

    def replace_code(self, text):
        replacements = {'y': '9', '口': '0', 'q': '0', 'u': '0', 'o': '0', '>': '1', 'd': '0', 'b': '8', '已': '2','D': '0', '五': '5'}
        if len(text) == 3:
            text = text.replace('566', '5066')
            text = text.replace('066', '1666')
        return ''.join(replacements.get(c, c) for c in text)
        
    def find_player_info(self,data, player_name):
        for index, item in enumerate(data):
            if item.get('playername') == player_name:
                return item.get('playerjiekou')
        return -1, None

    def md5_encrypt(self,text, encoding='utf-8', uppercase=False):
        if isinstance(text, str):
            text = text.encode(encoding)
        md5_hash = hashlib.md5()
        md5_hash.update(text)
        result = md5_hash.hexdigest()
        return result.upper() if uppercase else result