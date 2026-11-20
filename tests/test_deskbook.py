from datetime import datetime

import pytest

from deskbook.cli import main
from deskbook.engine import Request, load_desks, load_requests, simulate, summarize


def req(rid, person, desk, a, b, show=True):
    f = "%Y-%m-%d %H:%M"
    return Request(rid, person, desk, datetime.strptime(a, f), datetime.strptime(b, f), show)


D = {"D1", "D2"}


def test_first_request_accepted():
    out = simulate([req("1", "A", "D1", "2026-03-02 08:00", "2026-03-02 12:00")], D)
    assert out[0].accepted


def test_overlap_on_same_desk_rejected():
    out = simulate([req("1", "A", "D1", "2026-03-02 08:00", "2026-03-02 12:00"),
                    req("2", "B", "D1", "2026-03-02 11:00", "2026-03-02 13:00")], D)
    assert not out[1].accepted and out[1].reason == "desk already booked"


def test_back_to_back_same_desk_allowed():
    out = simulate([req("1", "A", "D1", "2026-03-02 08:00", "2026-03-02 12:00"),
                    req("2", "B", "D1", "2026-03-02 12:00", "2026-03-02 14:00")], D)
    assert out[1].accepted


def test_person_cannot_hold_two_desks_at_once():
    out = simulate([req("1", "A", "D1", "2026-03-02 08:00", "2026-03-02 12:00"),
                    req("2", "A", "D2", "2026-03-02 10:00", "2026-03-02 11:00")], D)
    assert out[1].reason == "person already booked then"


def test_unknown_desk():
    assert simulate([req("1", "A", "D9", "2026-03-02 08:00", "2026-03-02 09:00")], D)[0].reason == "unknown desk"


def test_too_long():
    out = simulate([req("1", "A", "D1", "2026-03-02 08:00", "2026-03-02 18:00")], D, max_hours=8)
    assert out[0].reason == "longer than 8 hours"


def test_end_before_start():
    out = simulate([req("1", "A", "D1", "2026-03-02 12:00", "2026-03-02 11:00")], D)
    assert out[0].reason == "end not after start"


def test_rejected_request_does_not_block_later_ones():
    out = simulate([req("1", "A", "D1", "2026-03-02 08:00", "2026-03-02 20:00"),
                    req("2", "B", "D1", "2026-03-02 09:00", "2026-03-02 10:00")], D)
    assert not out[0].accepted and out[1].accepted


def test_summary_no_show_and_utilization():
    out = simulate([req("1", "A", "D1", "2026-03-02 08:00", "2026-03-02 12:00", show=False)], D)
    s = summarize(out, D, day_hours=8)
    assert s["no_show_hours"] == 4.0 and s["by_desk"]["D1"] == 50.0 and s["by_desk"]["D2"] == 0.0


def test_summary_empty():
    s = summarize([], D)
    assert s["requests"] == 0 and s["by_desk"]["D1"] == 0.0


def test_load_requests_bad_time(tmp_path):
    f = tmp_path / "r.csv"
    f.write_text("request,person,desk,start,end\n1,A,D1,tomorrow,2026-03-02 10:00\n")
    with pytest.raises(ValueError, match="bad time"):
        load_requests(f)


def test_load_desks_empty(tmp_path):
    f = tmp_path / "d.csv"
    f.write_text("desk\n")
    with pytest.raises(ValueError):
        load_desks(f)


def test_cli_run_examples(capsys):
    assert main(["run", "examples/desks.csv", "examples/requests.csv", "--by-desk"]) == 0
    out = capsys.readouterr().out
    assert "REJECTED" in out and "Booked share" in out


def test_cli_missing_file(capsys):
    assert main(["run", "nope.csv", "examples/requests.csv"]) == 2
