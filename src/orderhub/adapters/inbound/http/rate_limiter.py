"""Limitador de peticiones en memoria (ventana fija).

Este módulo no importa Flask: es el mecanismo puro (contar, expirar, acotar
memoria) y lo puede construir el Composition Root. La parte HTTP (clave por IP o
por usuario, respuesta 429, ProxyFix) vive en `rate_limiting.py`.

Limitaciones asumidas (DT-23): el estado vive en el proceso, así que se pierde
al reiniciar o dormirse el servicio y cada worker tendría su propio contador
(gunicorn corre con un solo worker, ver gunicorn.conf.py). La ventana fija
permite una ráfaga de hasta el doble del límite en el borde entre dos ventanas.
"""

import math
import threading
import time
from dataclasses import dataclass
from typing import Callable, Dict, List

DEFAULT_MAX_KEYS = 10_000


class InMemoryRateLimiter:
    """Permite `max_requests` por clave en cada ventana de `window_seconds`.

    - Thread-safe: un Lock protege el estado (`python app.py` es multihilo).
    - El reloj es inyectable para probar sin dormir.
    - Memoria acotada: las ventanas vencidas se purgan en cada llamada y, si
      aun así se llega a `max_keys` claves, se descarta la más antigua.
    """

    def __init__(
        self,
        max_requests: int,
        window_seconds: float,
        clock: Callable[[], float] = time.monotonic,
        max_keys: int = DEFAULT_MAX_KEYS,
    ) -> None:
        if max_requests < 1 or window_seconds <= 0 or max_keys < 1:
            raise ValueError("max_requests, window_seconds y max_keys deben ser > 0")
        self._max_requests = max_requests
        self._window = window_seconds
        self._clock = clock
        self._max_keys = max_keys
        self._lock = threading.Lock()
        # clave -> [fin de la ventana, peticiones contadas]. Se inserta siempre
        # al final, así que el orden del dict es el orden de vencimiento.
        self._windows: Dict[str, List[float]] = {}

    def __len__(self) -> int:
        with self._lock:
            return len(self._windows)

    def hit(self, key: str) -> int:
        """Registra una petición. Devuelve 0 si se permite, o los segundos que
        faltan para que se abra una ventana nueva si se superó el límite."""
        with self._lock:
            now = self._clock()
            self._purge_expired(now)

            entry = self._windows.get(key)
            if entry is None:
                self._make_room()
                self._windows[key] = [now + self._window, 1]
                return 0
            if entry[1] < self._max_requests:
                entry[1] += 1
                return 0
            return max(1, math.ceil(entry[0] - now))

    def _purge_expired(self, now: float) -> None:
        expired = []
        for key, (window_end, _) in self._windows.items():
            if window_end > now:
                break
            expired.append(key)
        for key in expired:
            del self._windows[key]

    def _make_room(self) -> None:
        while len(self._windows) >= self._max_keys:
            del self._windows[next(iter(self._windows))]


class NoRateLimiter:
    """Limitador desactivado (RATE_LIMIT_ENABLED=0): nunca bloquea."""

    def hit(self, key: str) -> int:
        return 0


@dataclass(frozen=True)
class RateLimitConfig:
    """Límites por ámbito. Los valores por defecto son holgados para una demo."""

    enabled: bool = True
    login_max: int = 30
    login_window: int = 60
    users_max: int = 30
    users_window: int = 60
    global_max: int = 300
    global_window: int = 60
    clock: Callable[[], float] = time.monotonic


@dataclass(frozen=True)
class RateLimiters:
    login: object
    users: object
    global_: object


def create_rate_limiters(config: RateLimitConfig) -> RateLimiters:
    if not config.enabled:
        disabled = NoRateLimiter()
        return RateLimiters(login=disabled, users=disabled, global_=disabled)
    return RateLimiters(
        login=InMemoryRateLimiter(
            config.login_max, config.login_window, clock=config.clock
        ),
        users=InMemoryRateLimiter(
            config.users_max, config.users_window, clock=config.clock
        ),
        global_=InMemoryRateLimiter(
            config.global_max, config.global_window, clock=config.clock
        ),
    )
