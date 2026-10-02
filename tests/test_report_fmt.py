from lakehouse.report import fmt


def test_fmt_keeps_price_precision_and_drops_noise():
    assert fmt(1.22) == "1.22" and fmt(0.69) == "0.69" and fmt(1.1) == "1.1"      # $/hr inputs print as written
    assert fmt(0.0052) == "0.0052" and fmt(0.149) == "0.149"                        # rates and $ per request
    assert fmt(147518.7) == "147,519" and fmt(17156) == "17156"                     # ms stay readable; ints untouched
    assert fmt(float("nan")) == "NaN" and fmt(float("inf")) == "inf" and fmt(None) == ""
    assert fmt(12.0) == "12" and fmt(26.862) == "26.862"
