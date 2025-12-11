from igdb import ArtworkTD


def stringify_ids(obj: any):
    """
    Recursively convert all *_id fields in a dict or list to strings.
    """
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if v is None:
                out[k] = None
            elif (k.endswith("_id")) and isinstance(v, (int,)):
                out[k] = str(v)
            else:
                out[k] = stringify_ids(v)
        return out
    if isinstance(obj, list):
        return [stringify_ids(i) for i in obj]
    return obj


def flat_artworks_to_urls(artworks: list[ArtworkTD]):
    artworks_urls: list[str] = []

    for item in artworks:
        # 只处理 dict 且含 url 的项
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        if not url:
            continue
        # 如果 URL 是协议相对的（//...），加上 https:
        if url.startswith("//"):
            url = "https:" + url
        # 把缩略图尺寸替换为较大尺寸
        url = url.replace("t_thumb", "t_1080p")
        artworks_urls.append(url)

    return artworks_urls
