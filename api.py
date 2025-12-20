import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

import requests


@dataclass
class FanboxPost:
    id: str
    title: str
    published_datetime: str
    updated_datetime: str
    creator_id: str
    creator_name: str
    creator_icon_url: Optional[str] = None
    fee_required: int = 0  # 收费金额（日元），0 表示免费


class FanboxAPI:
    """
    一个非常薄的 Fanbox Web API 封装，参考 src/ts/API.ts 和 docs/fanbox.md。
    实现本项目需要的接口：
      - post.listSupporting（正在赞助的投稿列表）
      - creator.listFollowing（关注的创作者列表）
      - post.listCreator（单个创作者的投稿列表）
    """

    def __init__(
        self,
        cookie: str,
        base_url: str = "https://api.fanbox.cc",
        timeout: int = 15,
        extra_headers: Optional[Dict[str, str]] = None,
        proxy: Optional[str] = None,
    ) -> None:
        """
        :param cookie: 浏览器里复制的 Cookie 字符串（整段粘贴即可）
        :param base_url: Fanbox API 基础地址
        :param timeout: 请求超时时间（秒）
        :param extra_headers: 额外自定义的 HTTP 头
        :param proxy: HTTP 代理地址，例如 "http://172.17.0.1:7890"，不设置则不使用代理
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        self.session = requests.Session()
        # 设置代理
        if proxy:
            self.session.proxies = {
                "http": proxy,
                "https": proxy,
            }
        # 基本的请求头，User-Agent 随便写一个常见浏览器即可
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json, text/plain, */*",
                "Referer": "https://www.fanbox.cc",
                "Origin": "https://www.fanbox.cc",
                "Cookie": cookie,
            }
        )
        if extra_headers:
            self.session.headers.update(extra_headers)

    def _request(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}/{path.lstrip('/')}"
        resp = self.session.get(url, params=params, timeout=self.timeout)
        if not resp.ok:
            raise RuntimeError(
                f"HTTP error {resp.status_code} {resp.reason} for {url}"
            )
        try:
            return resp.json()
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON response from {url}: {e}") from e

    # -------- 公开接口 --------

    def list_supporting_posts(
        self,
        limit: int = 50,
        max_published_datetime: str = "",
        max_id: str = "",
    ) -> Dict[str, Any]:
        """
        对应扩展里的 post.listSupporting：
        https://fanbox.pixiv.net/api/post.listSupporting

        返回原始 JSON（含 body.items）。
        """
        params: Dict[str, Any] = {"limit": limit}
        if max_published_datetime:
            params["maxPublishedDatetime"] = max_published_datetime
        if max_id:
            params["maxId"] = max_id
        return self._request("post.listSupporting", params=params)

    @staticmethod
    def parse_posts_from_supporting(raw: Dict[str, Any]) -> List[FanboxPost]:
        """
        从 post.listSupporting 的返回值中解析出简单的帖子列表。
        """
        body = raw.get("body") or {}
        items = body.get("items") or []
        result: List[FanboxPost] = []
        for item in items:
            try:
                user = item.get("user") or {}
                fee_required = int(item.get("feeRequired", 0) or 0)
                result.append(
                    FanboxPost(
                        id=str(item.get("id")),
                        title=str(item.get("title", "")),
                        published_datetime=str(item.get("publishedDatetime", "")),
                        updated_datetime=str(item.get("updatedDatetime", "")),
                        creator_id=str(item.get("creatorId") or user.get("userId", "")),
                        creator_name=str(user.get("name", "")),
                        creator_icon_url=str(user.get("iconUrl", "")) if user.get("iconUrl") else None,
                        fee_required=fee_required,
                    )
                )
            except Exception:
                # 某条数据异常时，简单跳过
                continue
        return result

    def list_following_creators(self) -> List[Dict[str, Any]]:
        """
        获取关注的创作者列表。
        对应扩展里的 creator.listFollowing：
        https://api.fanbox.cc/creator.listFollowing

        返回格式: [{creatorId: str, name: str, iconUrl: str}, ...]
        """
        raw = self._request("creator.listFollowing")
        body = raw.get("body") or []
        result: List[Dict[str, Any]] = []
        for creator in body:
            try:
                user = creator.get("user") or {}
                result.append({
                    "creatorId": str(creator.get("creatorId", "")),
                    "name": str(user.get("name", "")),
                    "iconUrl": str(user.get("iconUrl", "")) if user.get("iconUrl") else None,
                })
            except Exception:
                continue
        return result

    def list_creator_posts(
        self,
        creator_id: str,
        limit: int = 50,
        max_published_datetime: str = "",
        max_id: str = "",
    ) -> Dict[str, Any]:
        """
        获取单个创作者的投稿列表。
        对应扩展里的 post.listCreator：
        https://api.fanbox.cc/post.listCreator?creatorId=xxx

        返回原始 JSON（含 body.items）。
        """
        params: Dict[str, Any] = {"creatorId": creator_id, "limit": limit}
        if max_published_datetime:
            params["maxPublishedDatetime"] = max_published_datetime
        if max_id:
            params["maxId"] = max_id
        return self._request("post.listCreator", params=params)

    @staticmethod
    def parse_posts_from_creator(raw: Dict[str, Any], creator_id: str, creator_name: str, creator_icon_url: Optional[str] = None) -> List[FanboxPost]:
        """
        从 post.listCreator 的返回值中解析出简单的帖子列表。
        """
        body = raw.get("body") or {}
        items = body
        result: List[FanboxPost] = []
        for item in items:
            try:
                user = item.get("user") or {}
                # 如果 item 里没有 user.iconUrl，使用传入的 creator_icon_url
                icon_url = str(user.get("iconUrl", "")) if user.get("iconUrl") else creator_icon_url
                fee_required = int(item.get("feeRequired", 0) or 0)
                result.append(
                    FanboxPost(
                        id=str(item.get("id")),
                        title=str(item.get("title", "")),
                        published_datetime=str(item.get("publishedDatetime", "")),
                        updated_datetime=str(item.get("updatedDatetime", "")),
                        creator_id=str(item.get("creatorId") or creator_id),
                        creator_name=str(user.get("name") or creator_name),
                        creator_icon_url=icon_url if icon_url else None,
                        fee_required=fee_required,
                    )
                )
            except Exception:
                continue
        return result

