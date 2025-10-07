const CryptoJS = require("crypto-js");
const cheerio = require("cheerio");
const axios = require("axios");

// 基础配置
const BASE_URL = "https://139fm.cyou";
const USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36";

// 创建axios实例
const api = axios.create({
  baseURL: BASE_URL,
  headers: {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "zh-CN,zh;q=0.9,zh-TW;q=0.8",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-User": "?1",
    "Sec-Fetch-Dest": "document",
    "Upgrade-Insecure-Requests": "1"
  }
});

// ROT13字符转换
function rot13Char(char) {
  if ('a' <= char && char <= 'z') {
    return String.fromCharCode(((char.charCodeAt(0) - 'a'.charCodeAt(0) + 13) % 26) + 'a'.charCodeAt(0));
  } else if ('A' <= char && char <= 'Z') {
    return String.fromCharCode(((char.charCodeAt(0) - 'A'.charCodeAt(0) + 13) % 26) + 'A'.charCodeAt(0));
  } else {
    return char;
  }
}

// ee2函数 - 对字母字符进行ROT13转换
function ee2(text) {
  let result = [];
  for (let i = 0; i < text.length; i++) {
    const char = text[i];
    const charCode = char.charCodeAt(0);
    
    // 小写字母处理
    if ('a'.charCodeAt(0) <= charCode && charCode <= 'z'.charCodeAt(0)) {
      result.push(rot13Char(char));
    }
    // 大写字母处理  
    else if ('A'.charCodeAt(0) <= charCode && charCode <= 'Z'.charCodeAt(0)) {
      result.push(rot13Char(char));
    } else {
      result.push(char);
    }
  }
  
  return result.join('');
}

// 主解密函数
function dd0(encryptedText, defaultValue) {
  try {
    // 第一步: ROT13解码
    const step1 = ee2(encryptedText);
    // 第二步: Base64解码
    const step2 = CryptoJS.enc.Base64.parse(step1).toString(CryptoJS.enc.Utf8);
    // 第三步: 再次ROT13解码
    const step3 = ee2(step2);
    return step3;
  } catch (error) {
    console.error("解密失败:", error);
    return defaultValue;
  }
}

// 从JavaScript代码中提取_conf对象
function extractConfFromHtml(html) {
  const confMatch = html.match(/var\s+_conf\s*=\s*({[^}]*});/);
  if (confMatch) {
    try {
      // 使用Function来安全地执行字符串获取_conf对象
      const confStr = confMatch[1];
      const _conf = new Function(`return ${confStr}`)();
      return _conf;
    } catch (error) {
      console.error("解析_conf对象失败:", error);
    }
  }
  return null;
}

// 解密所有配置数据
function decryptAll(confData) {
  const results = [];
  if (confData && confData.a && Array.isArray(confData.a)) {
    for (const encryptedStr of confData.a) {
      if (encryptedStr) { // 只处理非空字符串
        const result = dd0(encryptedStr, confData.c || '');
        results.push(result);
      }
    }
  }
  return results;
}

// 分类映射
const CATEGORY_MAP = {
  "1": "长篇有声",
  "2": "短篇有声", 
  "3": "自慰催眠",
  "4": "ASMR专区"
};

// 主播映射
const ANCHOR_MAP = {
  "小苮儿": "小苮儿",
  "步非烟团队": "步非烟团队",
  "小野猫": "小野猫",
  "戴逸": "戴逸",
  "姽狐": "姽狐",
  "小咪": "小咪",
  "浅浅": "浅浅",
  "季姜": "季姜",
  "丽莎": "丽莎",
  "雅朵": "雅朵",
  "曼曼": "曼曼",
  "小窈": "小窈",
  "ASMR专区": "ASMR专区"
};

const _home = async ({ filter }) => {
  try {
    const response = await api.get("/podcasts");
    const $ = cheerio.load(response.data);
    
    const categories = [];
    
    // 解析分类
    $("#areas dd").each((index, element) => {
      const $dd = $(element);
      const dataVal = $dd.attr("data-val");
      if (dataVal && dataVal !== "-1") {
        categories.push({
          type_id: dataVal,
          type_name: $dd.text().trim()
        });
      }
    });
    
    // 解析主播分类
    $("#tags dd").each((index, element) => {
      const $dd = $(element);
      const dataVal = $dd.attr("data-val");
      if (dataVal && dataVal !== "全部" && ANCHOR_MAP[dataVal]) {
        categories.push({
          type_id: `anchor_${dataVal}`,
          type_name: `主播-${dataVal}`
        });
      }
    });
    
    // 获取首页列表
    const list = [];
    $(".mh-item").each((index, element) => {
      const $item = $(element);
      const $link = $item.find("a").first();
      const href = $link.attr("href");
      const coverStyle = $item.find(".mh-cover").attr("style");
      const title = $item.find(".title a").text().trim();
      const chapter = $item.find(".chapter").text().trim();
      
      let coverUrl = "";
      if (coverStyle) {
        const match = coverStyle.match(/url\((.*?)\)/);
        if (match) coverUrl = match[1];
      }
      
      if (href && title) {
        const vodId = href.split("/").pop();
        list.push({
          vod_id: vodId,
          vod_name: title,
          vod_pic: coverUrl,
          vod_remarks: chapter || "暂无简介"
        });
      }
    });
    
    return {
      class: categories,
      list: list
    };
  } catch (error) {
    console.error("Home error:", error);
    return {
      class: [],
      list: []
    };
  }
};

const _category = async ({ id, page, filter, filters }) => {
  try {
    let url = "/podcasts";
    const params = {};
    
    if (id && id.startsWith("anchor_")) {
      // 主播分类
      const anchor = id.replace("anchor_", "");
      params.tag = anchor;
    } else if (id && CATEGORY_MAP[id]) {
      // 内容分类
      params.area = id;
    }
    
    if (page && page > 1) {
      params.page = page;
    }
    
    if (Object.keys(params).length > 0) {
      url += "?" + new URLSearchParams(params).toString();
    }
    
    const response = await api.get(url);
    const $ = cheerio.load(response.data);
    
    const list = [];
    $(".mh-item").each((index, element) => {
      const $item = $(element);
      const $link = $item.find("a").first();
      const href = $link.attr("href");
      const coverStyle = $item.find(".mh-cover").attr("style");
      const title = $item.find(".title a").text().trim();
      const chapter = $item.find(".chapter").text().trim();
      
      let coverUrl = "";
      if (coverStyle) {
        const match = coverStyle.match(/url\((.*?)\)/);
        if (match) coverUrl = match[1];
      }
      
      if (href && title) {
        const vodId = href.split("/").pop();
        list.push({
          vod_id: vodId,
          vod_name: title,
          vod_pic: coverUrl,
          vod_remarks: chapter || "暂无简介"
        });
      }
    });
    
    // 解析分页信息
    let pagecount = 1;
    const $pagination = $(".pagination");
    if ($pagination.length) {
      const $lastPage = $pagination.find("a[title]").last();
      if ($lastPage.length) {
        const href = $lastPage.attr("href");
        const match = href.match(/page=(\d+)/);
        if (match) pagecount = parseInt(match[1]);
      }
    }
    
    return {
      list: list,
      page: parseInt(page) || 1,
      pagecount: pagecount
    };
  } catch (error) {
    console.error("Category error:", error);
    return {
      list: [],
      page: 1,
      pagecount: 1
    };
  }
};

const _detail = async ({ id }) => {
  const result = {
    list: []
  };

  for (const id_ of id) {
    try {
      const response = await api.get(`/podcast/${id_}`);
      const $ = cheerio.load(response.data);
      
      // 提取_conf对象并解密音频URL
      const _conf = extractConfFromHtml(response.data);
      let decryptedUrls = [];
      
      if (_conf) {
        console.log("找到_conf对象:", _conf);
        decryptedUrls = decryptAll(_conf);
        console.log("解密后的URL列表:", decryptedUrls);
      }
      
      // 基本信息
      const title = $("title").text().replace("-139FM", "").trim();
      let coverUrl = $('img[data-amplitude-song-info="cover_art_url"]').attr("src");
      
      // 如果没有获取到封面，尝试从其他位置获取
      if (!coverUrl) {
        const coverStyle = $(".mh-cover").attr("style");
        if (coverStyle) {
          const match = coverStyle.match(/url\((.*?)\)/);
          if (match) coverUrl = match[1];
        }
      }
      
      // 解析播放列表
      const episodes = [];
      $(".song").each((index, element) => {
        const $song = $(element);
        const episodeTitle = $song.find(".song-title").text().trim();
        const episodeArtist = $song.find(".song-artist").text().trim();
        const requireBuy = $song.attr("data-require-buy") === "1";
        const chapterId = $song.attr("data-chapter-id");
        
        // 获取对应的解密URL
        const audioUrl = index < decryptedUrls.length ? decryptedUrls[index] : "";
        
        episodes.push({
          name: episodeTitle,
          artist: episodeArtist,
          requireBuy: requireBuy,
          chapterId: chapterId,
          url: audioUrl
        });
      });
      
      // 解析详情信息
      const descMatch = response.data.match(/"desc":\s*"([^"]*)"/);
      const areaMatch = response.data.match(/"area":\s*"([^"]*)"/);
      const tagMatch = response.data.match(/"tag":\s*"([^"]*)"/);
      const clicksMatch = response.data.match(/"clicks":\s*"([^"]*)"/);
      
      let vodContent = "暂无简介";
      if (descMatch) {
        vodContent = descMatch[1].replace(/简介：/, "");
      }
      
      let vodRemarks = "";
      if (clicksMatch) {
        vodRemarks = clicksMatch[1].replace(/热度：/, "热度:");
      }
      
      // 清理HTML标签
      const cleanHtml = (html) => {
        if (!html) return "";
        return html.replace(/<[^>]*>/g, "");
      };
      
      let typeName = "";
      if (areaMatch) {
        typeName = cleanHtml(areaMatch[1]).replace(/类型：/, "").trim();
      }
      
      let vodActor = "";
      if (tagMatch) {
        vodActor = cleanHtml(tagMatch[1]).replace(/主播：/, "").trim();
      }
      
      // 构建播放源 - 修正格式
      const playFrom = "139FM"; // 平台名称
      
      // 构建播放URL - 格式：剧集1$URL1#剧集2$URL2
      const playUrlParts = [];
      episodes.forEach((ep, index) => {
        let episodeName = ep.name;
        if (ep.requireBuy) {
          episodeName += "[付费]";
        }
        
        let episodeUrl = ep.url;
        if (!episodeUrl) {
          // 如果没有解密URL，使用组合ID格式
          episodeUrl = `${id_}_${ep.chapterId}_${index}`;
        }
        
        playUrlParts.push(`${episodeName}$${episodeUrl}`);
      });
      
      const playUrl = playUrlParts.join("#");
      
      result.list.push({
        vod_id: id_,
        vod_name: title.replace("全集免费高清无修在线阅读", "").trim(), // 清理标题
        vod_pic: coverUrl,
        type_name: typeName,
        vod_actor: vodActor,
        vod_director: episodes.length > 0 ? `共${episodes.length}集` : "",
        vod_content: vodContent,
        vod_remarks: vodRemarks,
        vod_play_from: playFrom,
        vod_play_url: playUrl
      });
      
    } catch (error) {
      console.error(`Detail error for ${id_}:`, error);
      result.list.push({
        vod_id: id_,
        vod_name: "获取失败",
        vod_pic: "",
        vod_content: "获取详情失败"
      });
    }
  }

  return result;
};

const _search = async ({ page, quick, wd }) => {
  try {
    const params = {
      keyword: wd
    };
    
    if (page && page > 1) {
      params.page = page;
    }
    
    const response = await api.get("/search", { params });
    const $ = cheerio.load(response.data);
    
    const list = [];
    $(".mh-item").each((index, element) => {
      const $item = $(element);
      const $link = $item.find("a").first();
      const href = $link.attr("href");
      const coverStyle = $item.find(".mh-cover").attr("style");
      const title = $item.find(".title a").text().trim();
      const chapter = $item.find(".chapter").text().trim();
      
      let coverUrl = "";
      if (coverStyle) {
        const match = coverStyle.match(/url\((.*?)\)/);
        if (match) coverUrl = match[1];
      }
      
      if (href && title) {
        const vodId = href.split("/").pop();
        list.push({
          vod_id: vodId,
          vod_name: title,
          vod_pic: coverUrl,
          vod_remarks: chapter || "暂无简介"
        });
      }
    });
    
    return {
      list: list,
      page: parseInt(page) || 1,
      pagecount: 1,
      total: list.length
    };
  } catch (error) {
    console.error("Search error:", error);
    return {
      list: [],
      page: 1,
      pagecount: 1,
      total: 0
    };
  }
};

const _play = async ({ flag, flags, id }) => {
  try {
    // 如果id已经是完整的URL（解密后的），直接使用
    if (id.startsWith('http')) {
      return {
        parse: 0,
        jx: 0,
        url: id,
        header: {
          "Referer": BASE_URL,
          "User-Agent": USER_AGENT,
          "Accept": "*/*",
          "Range": "bytes=0-"
        }
      };
    }
    
    // id格式: podcastId_chapterId_index
    const parts = id.split('_');
    if (parts.length >= 3) {
      const [podcastId, chapterId, index] = parts;
      
      // 获取详情页面来解密音频URL
      const response = await api.get(`/podcast/${podcastId}`);
      const _conf = extractConfFromHtml(response.data);
      
      if (_conf) {
        const decryptedUrls = decryptAll(_conf);
        const audioIndex = parseInt(index);
        
        if (audioIndex < decryptedUrls.length && decryptedUrls[audioIndex]) {
          return {
            parse: 0,
            jx: 0,
            url: decryptedUrls[audioIndex],
            header: {
              "Referer": `${BASE_URL}/podcast/${podcastId}`,
              "User-Agent": USER_AGENT,
              "Accept": "*/*",
              "Range": "bytes=0-"
            }
          };
        }
      }
    }
    
    // 如果无法解析，返回空
    return {
      parse: 0,
      jx: 0,
      url: "",
      header: {}
    };
    
  } catch (error) {
    console.error("Play error:", error);
    return {
      parse: 0,
      jx: 0,
      url: "",
      header: {}
    };
  }
};

const _proxy = async (req, reply) => {
  return Object.assign({}, req.query, req.params);
};

const meta = {
  key: "y_139fm",
  name: "🎧139FM有声小说",
  type: 4,
  api: "/video/y_139fm",
  searchable: 1,
  quickSearch: 1,
  changeable: 0,
};

module.exports = async (app, opt) => {
  app.get(meta.api, async (req, reply) => {
    const { extend, filter, t, ac, pg, ext, ids, flag, play, wd, quick } = req.query;

    if (play) {
      return await _play({ flag: flag || "", flags: [], id: play });
    } else if (wd) {
      return await _search({
        page: parseInt(pg || "1"),
        quick: quick || false,
        wd,
      });
    } else if (!ac) {
      return await _home({ filter: filter ?? false });
    } else if (ac === "detail") {
      if (t) {
        const body = {
          id: t,
          page: parseInt(pg || "1"),
          filter: filter || false,
          filters: {},
        };
        if (ext) {
          try {
            body.filters = JSON.parse(
              CryptoJS.enc.Base64.parse(ext).toString(CryptoJS.enc.Utf8)
            );
          } catch {}
        }
        return await _category(body);
      } else if (ids) {
        return await _detail({
          id: ids
            .split(",")
            .map((_id) => _id.trim())
            .filter(Boolean),
        });
      }
    }

    return req.query;
  });
  
  app.get(`${meta.api}/proxy`, _proxy);
  
  opt.sites.push(meta);
};

