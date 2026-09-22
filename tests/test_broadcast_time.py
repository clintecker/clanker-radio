from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from ai_radio.broadcast_time import broadcast_hour, spoken_hour

CHI = ZoneInfo("America/Chicago")


@pytest.mark.parametrize(
    "hh,mm,expected",
    [(15, 52, 16), (15, 50, 16), (16, 0, 16), (16, 1, 16), (16, 29, 16), (16, 30, 17), (23, 55, 0)],
)
def test_nearest_top_of_hour(hh, mm, expected):
    # The 2026-09-22 bug: a reboot catch-up generated at 16:00 announced "5 pm".
    assert broadcast_hour(datetime(2026, 9, 22, hh, mm, tzinfo=CHI)).hour == expected


def test_timezone_preserved():
    assert broadcast_hour(datetime(2026, 9, 22, 15, 52, tzinfo=CHI)).tzinfo is CHI


def test_spoken():
    assert spoken_hour(datetime(2026, 9, 22, 16)) == "4 pm"
    assert spoken_hour(datetime(2026, 9, 22, 0)) == "midnight"
    assert spoken_hour(datetime(2026, 9, 22, 12)) == "noon"
    assert spoken_hour(datetime(2026, 9, 22, 9)) == "9 am"
