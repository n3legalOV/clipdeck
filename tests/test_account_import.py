import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.account_import import parse_line, parse_accounts

SID = "a1b2c3d4e5f60718293a4b5c6d7e8f90"


def test_tab_separated():
    assert parse_line(f"main\t{SID}\tuseast8") == {"username": "main", "sessionid": SID, "dc_id": "useast8"}


def test_dc_first_and_at_sign():
    assert parse_line(f"useast5\t{SID}\t@second")["username"] == "second"


def test_session_first():
    item = parse_line(f"{SID}, main, useast2a")
    assert item["username"] == "main" and item["dc_id"] == "useast2a"


def test_missing_session_is_error():
    accounts, errors = parse_accounts("main\tuseast8\ngood\t" + SID + "\n")
    assert len(accounts) == 1 and errors == [1]


def test_duplicates_collapse():
    text = f"main\t{SID}\nMAIN\t{SID}"
    accounts, errors = parse_accounts(text)
    assert len(accounts) == 1 and not errors


def test_junk_lines_skipped():
    accounts, errors = parse_accounts("\n# комментарий\n   \n")
    assert accounts == [] and errors == []


def test_semicolon_csv_with_quotes():
    assert parse_line(f'"main";"{SID}";"useast5"')["username"] == "main"
