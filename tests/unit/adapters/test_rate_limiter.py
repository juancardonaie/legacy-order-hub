"""Tests del limitador en memoria: sin Flask y sin dormir (reloj falso)."""

import threading

import pytest

from orderhub.adapters.inbound.http.rate_limiter import (
    InMemoryRateLimiter,
    NoRateLimiter,
    RateLimitConfig,
    create_rate_limiters,
)


class FakeClock:
    def __init__(self, now: float = 1000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


def test_permite_hasta_el_maximo_y_bloquea_la_siguiente(clock):
    limiter = InMemoryRateLimiter(3, 60, clock=clock)

    assert [limiter.hit("a") for _ in range(3)] == [0, 0, 0]
    assert limiter.hit("a") > 0


def test_devuelve_los_segundos_que_faltan_para_la_ventana_nueva(clock):
    limiter = InMemoryRateLimiter(1, 60, clock=clock)
    limiter.hit("a")
    clock.advance(10)

    assert limiter.hit("a") == 50


def test_el_retry_after_nunca_es_cero_ni_decimal(clock):
    limiter = InMemoryRateLimiter(1, 60, clock=clock)
    limiter.hit("a")
    clock.advance(59.4)

    assert limiter.hit("a") == 1


def test_al_acabar_la_ventana_se_vuelve_a_permitir(clock):
    limiter = InMemoryRateLimiter(1, 60, clock=clock)
    limiter.hit("a")
    assert limiter.hit("a") > 0

    clock.advance(60)

    assert limiter.hit("a") == 0
    assert limiter.hit("a") > 0


def test_cada_clave_tiene_su_propio_contador(clock):
    limiter = InMemoryRateLimiter(1, 60, clock=clock)

    assert limiter.hit("a") == 0
    assert limiter.hit("b") == 0
    assert limiter.hit("a") > 0


def test_purga_las_claves_vencidas(clock):
    limiter = InMemoryRateLimiter(5, 60, clock=clock)
    for clave in ("a", "b", "c"):
        limiter.hit(clave)
    assert len(limiter) == 3

    clock.advance(61)
    limiter.hit("d")

    assert len(limiter) == 1


def test_no_purga_las_claves_con_ventana_vigente(clock):
    limiter = InMemoryRateLimiter(5, 60, clock=clock)
    limiter.hit("a")
    clock.advance(30)
    limiter.hit("b")
    clock.advance(31)  # "a" venció, "b" sigue vigente

    limiter.hit("c")

    assert len(limiter) == 2


def test_el_numero_de_claves_tiene_un_tope(clock):
    limiter = InMemoryRateLimiter(1, 60, clock=clock, max_keys=3)

    for numero in range(10):
        limiter.hit(f"ip-{numero}")
        assert len(limiter) <= 3


def test_al_llegar_al_tope_se_descarta_la_clave_mas_antigua(clock):
    limiter = InMemoryRateLimiter(1, 60, clock=clock, max_keys=2)
    limiter.hit("vieja")
    clock.advance(1)
    limiter.hit("media")
    clock.advance(1)
    limiter.hit("nueva")  # expulsa a "vieja"

    assert limiter.hit("media") > 0  # sigue contada
    assert limiter.hit("vieja") == 0  # empezó de cero


def test_es_seguro_con_varios_hilos():
    """Con 8 hilos x 50 peticiones y límite 100, pasan exactamente 100."""
    limiter = InMemoryRateLimiter(100, 3600)
    permitidas = []
    lock = threading.Lock()

    def trabajo():
        propias = sum(1 for _ in range(50) if limiter.hit("compartida") == 0)
        with lock:
            permitidas.append(propias)

    hilos = [threading.Thread(target=trabajo) for _ in range(8)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()

    assert sum(permitidas) == 100


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_requests": 0, "window_seconds": 60},
        {"max_requests": 1, "window_seconds": 0},
        {"max_requests": 1, "window_seconds": 60, "max_keys": 0},
    ],
)
def test_rechaza_parametros_invalidos(kwargs):
    with pytest.raises(ValueError):
        InMemoryRateLimiter(**kwargs)


def test_el_limitador_desactivado_nunca_bloquea():
    limiter = NoRateLimiter()

    assert all(limiter.hit("a") == 0 for _ in range(1000))


def test_create_rate_limiters_usa_los_valores_de_cada_ambito(clock):
    config = RateLimitConfig(login_max=1, users_max=2, global_max=3, clock=clock)

    limiters = create_rate_limiters(config)

    assert [limiters.login.hit("k") for _ in range(2)][1] > 0
    assert [limiters.users.hit("k") for _ in range(3)][2] > 0
    assert [limiters.global_.hit("k") for _ in range(4)][3] > 0


def test_create_rate_limiters_desactivado_devuelve_limitadores_neutros():
    limiters = create_rate_limiters(RateLimitConfig(enabled=False, login_max=1))

    assert all(limiters.login.hit("k") == 0 for _ in range(5))
    assert isinstance(limiters.users, NoRateLimiter)
    assert isinstance(limiters.global_, NoRateLimiter)
