import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict

from i18n import get_language


@dataclass
class MonitorConfig:
    cookie: str
    limit: int = 50
    state_file: str = "fanbox_monitor_state.json"
    bark_key: Optional[str] = None
    bark_group: str = "Fanbox更新跟踪"
    check_following: bool = False
    min_fee_required: int = 0  # 最小收费金额（日元），只有收费 >= 此值的投稿才会触发通知，0 表示不限制
    creators_file: str = "fanbox_monitor_creators.json"  # 保存赞助者和关注者列表的文件
    proxy: Optional[str] = None  # HTTP 代理地址，例如 "http://172.17.0.1:7890"，不设置则不使用代理
    language: Optional[str] = None  # 语言代码 (en, zh, zh-tw, ja, ko)，不设置则自动检测


def load_creator_min_fees(config_path: str) -> Dict[str, int]:
    """
    从配置文件中加载每个创作者的最小监听金额配置。
    如果配置文件中没有 creator_min_fees 字段，返回空字典。
    """
    p = Path(config_path)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        creator_min_fees = data.get("creator_min_fees") or {}
        if isinstance(creator_min_fees, dict):
            return {str(k): int(v) for k, v in creator_min_fees.items()}
    except Exception:
        pass
    return {}


def save_creator_min_fees(config_path: str, creator_min_fees: Dict[str, int]) -> None:
    """
    将每个创作者的最小监听金额配置保存到配置文件。
    会保留配置文件中的其他字段。
    """
    p = Path(config_path)
    if not p.exists():
        # 如果配置文件不存在，创建一个新的
        data = {}
    else:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    
    data["creator_min_fees"] = creator_min_fees
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def ensure_creator_min_fee(config_path: str, creator_id: str, default_fee: int = 0) -> int:
    """
    确保配置文件中存在该创作者的最小监听金额配置。
    如果不存在，自动写入默认值。
    返回该创作者的最小监听金额。
    """
    creator_min_fees = load_creator_min_fees(config_path)
    if creator_id not in creator_min_fees:
        creator_min_fees[creator_id] = default_fee
        save_creator_min_fees(config_path, creator_min_fees)
    return creator_min_fees.get(creator_id, default_fee)


def load_config(path: str = "fanbox_monitor_config.json") -> MonitorConfig:
    """
    从 JSON 文件加载配置。
    示例内容：
    {
      "cookie": "从浏览器复制过来的整段 Cookie 字符串",
      "limit": 50,
      "state_file": "fanbox_monitor_state.json",
      "bark_key": "你的 Bark 推送 key，可选",
      "bark_group": "可选的 Bark 分组名称，默认：Fanbox更新跟踪",
      "check_following": false,
      "min_fee_required": 0,
      "creators_file": "fanbox_monitor_creators.json",
      "proxy": "http://172.17.0.1:7890",
      "language": "zh"
    }
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"配置文件 {path} 不存在，请先创建，并填入 Fanbox 登录后的 Cookie。"
        )
    data = json.loads(p.read_text(encoding="utf-8"))
    cookie = data.get("cookie") or ""
    if not cookie:
        raise ValueError("配置文件中缺少 cookie 字段。")
    limit = int(data.get("limit") or 50)
    state_file = str(data.get("state_file") or "fanbox_monitor_state.json")
    bark_key = data.get("bark_key") or None
    bark_group = data.get("bark_group") or "Fanbox更新跟踪"
    check_following = bool(data.get("check_following") or False)
    min_fee_required = int(data.get("min_fee_required") or 0)
    creators_file = str(data.get("creators_file") or "fanbox_monitor_creators.json")
    proxy = data.get("proxy") or None
    language = data.get("language") or None
    # 获取实际使用的语言
    language = get_language(language)
    return MonitorConfig(
        cookie=cookie,
        limit=limit,
        state_file=state_file,
        bark_key=bark_key,
        bark_group=bark_group,
        check_following=check_following,
        min_fee_required=min_fee_required,
        creators_file=creators_file,
        proxy=proxy,
        language=language,
    )

