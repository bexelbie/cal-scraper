import base64
import json

from cal_scraper.fleet_fact import emit_fleet_fact


def test_emit_fleet_fact_round_trip(tmp_path):
    detail = {"sites_ok": 2, "sites_failed": 1, "exit": 0}
    out_path, line = emit_fleet_fact(
        detail,
        "partial",
        ts=1730000000,
        output_dir=str(tmp_path),
        host="host-a",
    )

    assert out_path is not None
    assert line is not None
    assert out_path.parent == tmp_path
    assert out_path.read_text(encoding="utf-8").startswith(line)

    measurement_and_tags, field_string = line.split(" ", 1)
    measurement, tag_string = measurement_and_tags.split(",", 1)
    assert measurement == "fleet_fact"
    assert "host=host-a" in tag_string
    assert "service=cal-scraper" in tag_string
    assert "fact=run" in tag_string

    assert "schema=1i" in field_string
    assert 'status="partial"' in field_string

    ts_field = next(field for field in field_string.split(",") if field.startswith("ts="))
    assert ts_field.endswith("i")
    assert int(ts_field[len("ts=") : -1]) == 1730000000

    detail_field = next(
        field for field in field_string.split(",") if field.startswith("detail_b64_json=")
    )
    encoded_detail = detail_field[len("detail_b64_json=") :].strip('"')
    decoded_detail = json.loads(base64.b64decode(encoded_detail).decode())
    assert decoded_detail == detail
