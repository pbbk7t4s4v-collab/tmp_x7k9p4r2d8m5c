import asyncio, time, random, json, pathlib
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field

# 给每个key限流防止超过并行数量限制
@dataclass
class TokenBucket:
    capacity: int                # 桶容量（最大令牌数量）
    refill_rate: float           # 每秒补充多少令牌
    tokens: float = 0.0
    last_refill_ts: float = field(default_factory=time.time)

    def try_consume(self, amount: float = 1.0) -> bool:
        now = time.time()
        delta = now - self.last_refill_ts
        self.tokens = min(self.capacity, self.tokens + delta * self.refill_rate)
        self.last_refill_ts = now
        if self.tokens >= amount:
            self.tokens -= amount
            return True
        return False

    def time_to_avail(self, amount: float = 1.0) -> float:
        if self.tokens >= amount:
            return 0.0
        need = amount - self.tokens
        return need / self.refill_rate if self.refill_rate > 0 else float("inf")


# 熔断机制，防止总是去用一个坏掉的key
@dataclass
class CircuitBreaker:
    failure_count: int = 0
    last_failure_ts: float = 0.0
    open_until: float = 0.0      # 已经熔断的key，到什么时刻再打开
    cooldown_seconds: float = 1# 目前默认熔断的key一秒再try
    threshold: int = 3           # 目前默认三次连续错就熔断

    def record_success(self):
        self.failure_count = 0
        self.last_failure_ts = 0
        self.open_until = 0

    def record_failure(self, cool: Optional[float] = None):
        self.failure_count += 1
        self.last_failure_ts = time.time()
        if self.failure_count >= self.threshold:
            self.open_until = time.time() + (cool or self.cooldown_seconds)

    def is_open(self) -> bool:
        return time.time() < self.open_until

    def half_open_probe_allowed(self) -> bool:
        # open 过期后允许半开探测，不过权重降低，如果健康再恢复正常状态
        return not self.is_open() and self.failure_count >= self.threshold

# key的包装
@dataclass
class APIKey:
    key: str
    vendor: str                 # "openai" | "gemini"
    weight: int = 1             # 权重越高越容易被选中
    dead: bool = False
    breaker: CircuitBreaker = field(default_factory=CircuitBreaker)
    bucket: TokenBucket = field(default_factory=lambda: TokenBucket(capacity=60, refill_rate=1.0))  # 60 rpm
    min_cooldown: float = 5.0   # 短冷却时长
    next_probe_ts: float = 0.0  # 半开探测时机
    metadata: Dict[str, Any] = field(default_factory=dict)

    def healthy(self) -> bool:
        if self.dead:
            return False
        if self.breaker.is_open():
            return False
        return True

    def short_cooldown(self, seconds: float):
        # 出错时短冷却
        self.breaker.open_until = max(self.breaker.open_until, time.time() + seconds)

# -------- KeyPool --------
class KeyPool:
    def __init__(self, keys: List[APIKey]):
        self._keys = keys
        self._lock = asyncio.Lock()
        self._rr_cursor = 0

    def _eligible_keys(self) -> List[APIKey]:
        now = time.time()
        out = []
        for k in self._keys:
            if k.dead:
                continue
            # 半开到期可以试一下
            if k.breaker.is_open():
                continue
            out.append(k)
        return out

    def _weighted_round_robin(self, candidates: List[APIKey]) -> Optional[APIKey]:
        # 按照weight选择
        expanded = []
        for k in candidates:
            expanded.extend([k] * max(0, k.weight))
        if not expanded:
            return None
        choice = expanded[self._rr_cursor % len(expanded)]
        self._rr_cursor += 1
        return choice

    async def acquire_key(self, vendor: Optional[str] = None) -> Optional[APIKey]:
        async with self._lock:
            cands = [k for k in self._eligible_keys() if (not vendor or k.vendor == vendor)]
            if not cands:
                return None
            # 找能用的key，都不能就等那个最短等待的
            best = None
            best_wait = float("inf")
            for _ in range(len(cands)):
                k = self._weighted_round_robin(cands)
                if not k:
                    break
                if k.bucket.try_consume(1):
                    return k
                else:
                    wait = k.bucket.time_to_avail(1)
                    if wait < best_wait:
                        best_wait = wait
                        best = k
            return best

    async def report_success(self, k: APIKey):
        async with self._lock:
            k.breaker.record_success()

    async def report_failure(self, k: APIKey, kind: str, retry_after: Optional[float] = None):
        """
        kind: 'auth' | 'rate' | 'server' | 'network' | 'other'
        """
        async with self._lock:
            if kind == 'auth':
                k.dead = True  # 死了
                return
            if kind == 'rate':
                cool = retry_after if retry_after else random.uniform(8, 20)
                k.breaker.record_failure(cool=cool)
                return
            if kind in ('server', 'network'):
                k.breaker.record_failure(cool=random.uniform(10, 60))
                return
            # 其他未知错误：短冷却
            k.breaker.record_failure(cool=k.min_cooldown)

    def have_live_key(self) -> bool:
        return any(k.healthy() for k in self._keys)

def load_keypool_from_config(path: str = "config_pool.json") -> List[APIKey]:
    """
    从同目录下 configpool.json 载入 API Key。
    支援两种格式：
    A) 新推荐格式（多把 key）：
       {
         "defaults": { "rpm": 60, "capacity": 60 },
         "keys": [
           {"key": "sk-xxx", "vendor": "openai", "weight": 3, "rpm": 90, "base_url": "https://yeysai.com/v1/"},
           {"key": "gm-yyy", "vendor": "gemini", "weight": 2}
         ]
       }
    B) 向下相容（旧单 key）：
       { "llm_key": "sk-xxx", "llm_settings": { "base_url": "https://yeysai.com/v1/" } }
       或 { "llm_key": "sk-xxx", "debug_settings": { "base_url": "..." } }
    """
    p = pathlib.Path(path)
    if not p.exists():
        return []

    cfg = json.loads(p.read_text(encoding="utf-8"))

    keys_cfg = cfg.get("keys", [])
    defaults: Dict[str, Any] = cfg.get("defaults", {})
    default_rpm = int(defaults.get("rpm", 60))
    default_capacity = int(defaults.get("capacity", default_rpm))  # 暂时设成 = rpm
    out: List[APIKey] = []

    # A) 新格式：多把 key
    for item in keys_cfg:
        key = item["key"]
        vendor = item["vendor"]
        weight = int(item.get("weight", 1))
        rpm = int(item.get("rpm", default_rpm))
        capacity = int(item.get("capacity", rpm))
        base_url = item.get("base_url") # 可选
        # 令牌桶：rpm -> 每秒补充 rpm/60
        bucket = TokenBucket(capacity=capacity, refill_rate=rpm / 60.0)
        metadata = {}
        if base_url:
            metadata["base_url"] = base_url
        out.append(APIKey(key=key, vendor=vendor, weight=weight, bucket=bucket, metadata=metadata))

    # 支持旧格式
    if not out and "llm_key" in cfg:
        base_url = None
        for sect in ("llm_settings", "debug_settings", "pptx_settings"):
            if cfg.get(sect, {}).get("base_url"):
                base_url = cfg[sect]["base_url"]
                break
        bucket = TokenBucket(capacity=default_capacity, refill_rate=default_rpm / 60.0)
        metadata = {"base_url": base_url} if base_url else {}
        out.append(APIKey(key=cfg["llm_key"], vendor="openai", weight=3, bucket=bucket, metadata=metadata))

    return KeyPool(out)