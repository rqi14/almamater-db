"""Manual mapping QS English name <-> Chinese name for top Chinese universities."""
from __future__ import annotations

# QS English name -> Chinese normalized name. Used by qs_world.py to attach
# QS rank to existing CN rows rather than inserting duplicates.
QS_EN_TO_ZH: dict[str, str] = {
    "Tsinghua University": "清华大学",
    "Peking University": "北京大学",
    "Fudan University": "复旦大学",
    "Shanghai Jiao Tong University": "上海交通大学",
    "Zhejiang University": "浙江大学",
    "University of Science and Technology of China": "中国科学技术大学",
    "Nanjing University": "南京大学",
    "Sun Yat-sen University": "中山大学",
    "Tongji University": "同济大学",
    "Wuhan University": "武汉大学",
    "Harbin Institute of Technology": "哈尔滨工业大学",
    "Beijing Normal University": "北京师范大学",
    "Beijing Institute of Technology": "北京理工大学",
    "Tianjin University": "天津大学",
    "Xi'an Jiaotong University": "西安交通大学",
    "Nankai University": "南开大学",
    "Huazhong University of Science and Technology": "华中科技大学",
    "South China University of Technology": "华南理工大学",
    "Renmin University of China": "中国人民大学",
    "Sichuan University": "四川大学",
    "Shandong University": "山东大学",
    "Xiamen University": "厦门大学",
    "Beihang University": "北京航空航天大学",
    "Central South University": "中南大学",
    "Dalian University of Technology": "大连理工大学",
    "Tongji Medical College": "同济大学",
    "Jilin University": "吉林大学",
    "Hunan University": "湖南大学",
    "Chongqing University": "重庆大学",
    "East China Normal University": "华东师范大学",
    "Soochow University": "苏州大学",
    "University of Electronic Science and Technology of China": "电子科技大学",
    "Northwestern Polytechnical University": "西北工业大学",
    "Lanzhou University": "兰州大学",
    "Shanghai University": "上海大学",
    "Northeastern University (China)": "东北大学",
    "Beijing University of Posts and Telecommunications": "北京邮电大学",
    "Nanjing University of Science and Technology": "南京理工大学",
    "Southeast University": "东南大学",
    "Beijing Jiaotong University": "北京交通大学",
    "China Agricultural University": "中国农业大学",
    "Ocean University of China": "中国海洋大学",
    "Northeast Normal University": "东北师范大学",
    "Wuhan University of Technology": "武汉理工大学",
    "Southwest Jiaotong University": "西南交通大学",
    "East China University of Science and Technology": "华东理工大学",
}

ZH_TO_QS_EN: dict[str, str] = {v: k for k, v in QS_EN_TO_ZH.items()}

# Common Chinese short-forms (alias -> canonical name).
# Auto-generation (e.g. name[:2]+"大") is unreliable: 中国人民大学→人大 not 中大,
# 清华大学→清华 not 清大. Maintained manually for the most-searched names only.
SHORT_ALIASES: dict[str, str] = {
    "北大":   "北京大学",
    "清华":   "清华大学",
    "人大":   "中国人民大学",
    "浙大":   "浙江大学",
    "复旦":   "复旦大学",
    "交大":   "上海交通大学",
    "南大":   "南京大学",
    "同济":   "同济大学",
    "武大":   "武汉大学",
    "华科":   "华中科技大学",
    "中大":   "中山大学",
    "川大":   "四川大学",
    "西交":   "西安交通大学",
    "哈工大": "哈尔滨工业大学",
    "北航":   "北京航空航天大学",
    "北理":   "北京理工大学",
    "南开":   "南开大学",
    "天大":   "天津大学",
    "东南":   "东南大学",
    "厦大":   "厦门大学",
    "中科大": "中国科学技术大学",
    "国科大": "中国科学院大学",
    "科大":   "中国科学技术大学",
    "东北大": "东北大学",
}


def to_zh(name_en: str) -> str | None:
    return QS_EN_TO_ZH.get(name_en)


def to_en(name_zh: str) -> str | None:
    return ZH_TO_QS_EN.get(name_zh)
