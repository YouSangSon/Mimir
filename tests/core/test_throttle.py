from mimir.core.throttle import Throttle


class FakeClock:
    def __init__(self) -> None:
        self.t = 0.0
        self.slept: list[float] = []

    def monotonic(self) -> float:
        return self.t

    def sleep(self, secs: float) -> None:
        self.slept.append(secs)
        self.t += secs


def test_first_call_does_not_sleep():
    clock = FakeClock()
    Throttle(max_per_second=2.0, sleep=clock.sleep, monotonic=clock.monotonic).wait()
    assert clock.slept == []


def test_second_call_sleeps_to_respect_rate():
    clock = FakeClock()
    # 2 req/s -> min interval 0.5s
    t = Throttle(max_per_second=2.0, sleep=clock.sleep, monotonic=clock.monotonic)
    t.wait()
    t.wait()
    assert clock.slept == [0.5]


def test_none_rate_uses_conservative_default():
    clock = FakeClock()
    # None -> conservative default 1 req/s
    t = Throttle(max_per_second=None, sleep=clock.sleep, monotonic=clock.monotonic)
    t.wait()
    t.wait()
    assert clock.slept == [1.0]
