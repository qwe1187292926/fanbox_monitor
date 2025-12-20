import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

# 独立脚本形式：假设在同一目录下有 api.py 和 config.py
from api import FanboxAPI, FanboxPost
from config import load_config, ensure_creator_min_fee
from onepush import get_notifier
from i18n import translate


def load_state(path: Path) -> Dict[str, str]:
    """
    读取上次已知的每个创作者的最新投稿 id。
    返回格式: {"supporting:creator_id": last_post_id, "following:creator_id": last_post_id}
    使用 "type:creator_id" 作为 key 来区分赞助和关注。
    """
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
    except Exception:
        pass
    return {}


def save_state(path: Path, state: Dict[str, str]) -> None:
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def group_latest_by_creator(posts: list[FanboxPost]) -> Dict[str, FanboxPost]:
    """
    从一堆按时间倒序的帖子中，取出每个创作者最新的一条。
    """
    latest: Dict[str, FanboxPost] = {}
    for p in posts:
        if p.creator_id not in latest:
            latest[p.creator_id] = p
    return latest


def format_datetime(datetime_str: str) -> str:
    """
    将 ISO 8601 格式的日期时间字符串格式化为易读的中文格式。
    例如: "2020-02-29T19:27:19+09:00" -> "2020年2月29日 19:27"
    """
    try:
        # 尝试解析 ISO 8601 格式
        dt = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
        # 格式化为中文日期时间
        return dt.strftime("%Y年%m月%d日 %H:%M")
    except Exception:
        # 如果解析失败，返回原字符串
        return datetime_str


def build_post_url(post: FanboxPost) -> str:
    """
    根据 creatorId 和 post.id 构造一个大多数情况下可用的网页地址。
    新版 fanbox 域名一般是 https://www.fanbox.cc/@{creatorId}/posts/{postId}
    """
    # creator_id 里有的是用户名（如 nekoworks），有的是数字 userId，二者都支持这种写法。
    return f"https://www.fanbox.cc/@{post.creator_id}/posts/{post.id}"


def notify_bark(
    bark_key: Optional[str],
    bark_group: str,
    post: FanboxPost,
    post_type: str,  # "supporting" 或 "following"
    language: str = "en",
) -> None:
    """
    使用 onepush 的 bark 通知。
    :param post_type: "supporting"（赞助）或 "following"（关注）
    :param language: 语言代码
    """
    if not bark_key:
        return
    notifier = get_notifier("bark")
    if post_type == "supporting":
        title = translate("supporting_title", language, creator_name=post.creator_name)
    else:
        title = translate("following_title", language, creator_name=post.creator_name)
    formatted_date = format_datetime(post.published_datetime)
    msg = f"{post.title}({post.fee_required}日元)\n发布于 {formatted_date}"
    url = build_post_url(post)
    try:
        # Bark 通知参数：icon 用于设置通知图标
        notify_params = {
            "key": bark_key,
            "title": title,
            "content": msg,
            "url": url,
            "group": bark_group,
        }
        # 如果有头像 URL，添加到通知参数中
        if post.creator_icon_url:
            notify_params["icon"] = post.creator_icon_url
        notifier.notify(**notify_params)
    except Exception as e:
        print(f"Bark 通知失败: {e}", file=sys.stderr)


def notify_error_bark(
    bark_key: Optional[str],
    bark_group: str,
    error_message: str,
    language: str = "en",
) -> None:
    """
    发送错误通知到 Bark。
    """
    if not bark_key:
        return
    try:
        notifier = get_notifier("bark")
        notify_params = {
            "key": bark_key,
            "title": translate("error_title", language),
            "content": error_message,
            "group": bark_group,
        }
        notifier.notify(**notify_params)
    except Exception as e:
        print(f"发送错误通知失败: {e}", file=sys.stderr)


def save_creators(
    creators_file: str,
    supporting_creators: list[Dict[str, str]],
    following_creators: Optional[list[Dict[str, str]]] = None,
) -> None:
    """
    将赞助者和关注者列表保存到配置文件。
    """
    data = {
        "supporting": [
            {
                "creatorId": c["creatorId"],
                "name": c["name"],
                "iconUrl": c.get("iconUrl"),
            }
            for c in supporting_creators
        ],
    }
    if following_creators is not None:
        data["following"] = [
            {
                "creatorId": c["creatorId"],
                "name": c["name"],
                "iconUrl": c.get("iconUrl"),
            }
            for c in following_creators
        ]
    path = Path(creators_file)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def check_supporting_posts(
    api: FanboxAPI,
    state: Dict[str, str],
    bark_key: Optional[str],
    bark_group: str,
    limit: int,
    default_min_fee: int,
    config_path: str,
    language: str = "en",
) -> Tuple[Dict[str, str], list[Dict[str, str]]]:
    """
    检查正在赞助的创作者是否有新投稿。
    返回 (更新后的 state, 创作者列表)。
    """
    raw = api.list_supporting_posts(limit=limit)
    posts = api.parse_posts_from_supporting(raw)
    latest = group_latest_by_creator(posts)

    # 收集创作者信息（用于保存到配置文件）
    creators_list = []
    for creator_id, post in latest.items():
        creators_list.append({
            "creatorId": creator_id,
            "name": post.creator_name,
            "iconUrl": post.creator_icon_url,
        })

    new_state = dict(state)
    for creator_id, post in latest.items():
        # 确保配置文件中存在该创作者的最小监听金额配置
        creator_min_fee = ensure_creator_min_fee(config_path, creator_id, default_min_fee)
        
        state_key = f"supporting:{creator_id}"
        last_id = state.get(state_key)
        if last_id is None:
            # 第一次看到这个创作者，记录当前 id，不提示
            new_state[state_key] = post.id
            continue

        if str(post.id) != str(last_id):
            # 检查收费金额是否符合要求（使用该创作者特定的最小金额）
            if post.fee_required < creator_min_fee:
                # 收费金额不足，跳过通知但更新状态
                new_state[state_key] = post.id
                continue

            # 有新投稿且符合收费要求
            formatted_date = format_datetime(post.published_datetime)
            fee_info = f" (收费: {post.fee_required}日元)" if post.fee_required > 0 else " (免费)"
            print(
                f"[NEW] 赞助 - {post.creator_name} ({creator_id}) 有新投稿："
                f"{post.title} (id={post.id}, 发布于 {formatted_date}{fee_info})"
            )
            notify_bark(bark_key, bark_group, post, "supporting", language)
            new_state[state_key] = post.id

    return new_state, creators_list


def check_following_posts(
    api: FanboxAPI,
    state: Dict[str, str],
    bark_key: Optional[str],
    bark_group: str,
    limit: int,
    default_min_fee: int,
    config_path: str,
    language: str = "en",
) -> Tuple[Dict[str, str], list[Dict[str, str]]]:
    """
    检查关注的创作者是否有新投稿。
    返回 (更新后的 state, 创作者列表)。
    """
    try:
        creators = api.list_following_creators()
    except Exception as e:
        print(f"获取关注者列表失败: {e}", file=sys.stderr)
        return state, []

    if not creators:
        return state, []

    new_state = dict(state)
    for creator_info in creators:
        creator_id = creator_info["creatorId"]
        creator_name = creator_info["name"]
        creator_icon_url = creator_info.get("iconUrl")

        try:
            raw = api.list_creator_posts(creator_id, limit=limit)
            posts = api.parse_posts_from_creator(raw, creator_id, creator_name, creator_icon_url)
            if not posts:
                continue

            # 取最新的一条
            latest_post = posts[0]
            state_key = f"following:{creator_id}"
            last_id = state.get(state_key)

            # 确保配置文件中存在该创作者的最小监听金额配置
            creator_min_fee = ensure_creator_min_fee(config_path, creator_id, default_min_fee)
            
            if last_id is None:
                # 第一次看到这个创作者，记录当前 id，不提示
                new_state[state_key] = latest_post.id
                continue

            if str(latest_post.id) != str(last_id):
                # 检查收费金额是否符合要求（使用该创作者特定的最小金额）
                if latest_post.fee_required < creator_min_fee:
                    # 收费金额不足，跳过通知但更新状态
                    new_state[state_key] = latest_post.id
                    continue

                # 有新投稿且符合收费要求
                formatted_date = format_datetime(latest_post.published_datetime)
                fee_info = f" (收费: {latest_post.fee_required}日元)" if latest_post.fee_required > 0 else " (免费)"
                print(
                    f"[NEW] 关注 - {latest_post.creator_name} ({creator_id}) 有新投稿："
                    f"{latest_post.title} (id={latest_post.id}, 发布于 {formatted_date}{fee_info})"
                )
                notify_bark(bark_key, bark_group, latest_post, "following", language)
                new_state[state_key] = latest_post.id
        except Exception as e:
            print(f"检查关注者 {creator_name} ({creator_id}) 的投稿失败: {e}", file=sys.stderr)
            continue

    # 返回创作者列表（用于保存到配置文件）
    creators_list = [
        {
            "creatorId": c["creatorId"],
            "name": c["name"],
            "iconUrl": c.get("iconUrl"),
        }
        for c in creators
    ]
    return new_state, creators_list


def run_once(
    api: FanboxAPI,
    state: Dict[str, str],
    bark_key: Optional[str],
    bark_group: str,
    limit: int,
    check_following: bool,
    default_min_fee: int,
    creators_file: str,
    config_path: str,
    language: str = "en",
) -> Dict[str, str]:
    """
    执行一次检测：
      - 检查正在赞助的创作者（post.listSupporting）
      - 如果配置开启，也检查关注的创作者（creator.listFollowing + post.listCreator）
      - 与 state 比较，打印"发现新投稿"的提示并发送 Bark 通知
      - 保存赞助者和关注者列表到配置文件
      - 返回更新后的 state
    """
    # 检查赞助的创作者
    new_state, supporting_creators = check_supporting_posts(
        api, state, bark_key, bark_group, limit, default_min_fee, config_path, language
    )

    # 如果配置开启，也检查关注的创作者
    following_creators = None
    if check_following:
        new_state, following_creators = check_following_posts(
            api, new_state, bark_key, bark_group, limit, default_min_fee, config_path, language
        )

    # 保存创作者列表到配置文件
    save_creators(creators_file, supporting_creators, following_creators)

    return new_state


def main() -> None:
    config_path = "fanbox_monitor_config.json"
    cfg = None
    try:
        cfg = load_config(config_path)
    except Exception as e:
        error_msg = f"{translate('config_load_error', 'en')}: {e}"
        print(error_msg, file=sys.stderr)
        # 如果配置加载失败，无法获取 bark_key，所以无法发送通知
        sys.exit(1)

    language = cfg.language or "en"
    
    try:
        api = FanboxAPI(cookie=cfg.cookie, proxy=cfg.proxy)
        state_path = Path(cfg.state_file)
        state = load_state(state_path)

        # 单次执行：用于外部定时器调用（如计划任务 / cron）
        try:
            new_state = run_once(
                api,
                state,
                cfg.bark_key,
                cfg.bark_group,
                cfg.limit,
                cfg.check_following,
                cfg.min_fee_required,
                cfg.creators_file,
                config_path,
                language,
            )
            save_state(state_path, new_state)
        except Exception as e:
            error_msg = f"{translate('detection_error', language)}: {e}"
            print(error_msg, file=sys.stderr)
            # 发送错误通知
            notify_error_bark(cfg.bark_key, cfg.bark_group, error_msg, language)
    except Exception as e:
        error_msg = f"{translate('runtime_error', language)}: {e}"
        print(error_msg, file=sys.stderr)
        # 发送错误通知（如果配置已加载）
        if cfg:
            notify_error_bark(cfg.bark_key, cfg.bark_group, error_msg, language)


if __name__ == "__main__":
    main()

