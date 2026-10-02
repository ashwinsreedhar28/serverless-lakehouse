from lakehouse.redact import find, redact

# Fake tokens built to match the shapes, never real credentials.
HF = "hf_" + "A" * 34
RUNPOD = "rpa_" + "B" * 40
OPENROUTER = "sk-or-v1-" + "c" * 48
GITHUB = "ghp_" + "D" * 36


def test_known_token_shapes_are_replaced():
    text = f"export HF_TOKEN={HF}\nAuthorization: Bearer {RUNPOD}\nkey={OPENROUTER} {GITHUB}"
    out, hits = redact(text)
    assert HF not in out and RUNPOD not in out and OPENROUTER not in out and GITHUB not in out
    assert hits["hf_token"] == 1 and hits["runpod_key"] == 1 and hits["sk_key"] == 1 and hits["github_token"] == 1


def test_kv_secret_keeps_key_and_separator():
    value = "ZmFrZXZhbHVl" * 3                       # built at runtime so the pre-commit scan of this file stays clean
    out, hits = redact(f'"api_key": "{value}"')
    assert out == '"api_key": "<redacted:kv_secret>"'
    assert hits["kv_secret"] == 1


def test_already_redacted_and_benign_text_untouched():
    benign = [
        '"api_key": "<redacted>"',                                   # emberserve already redacts the sweep args
        "Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits",
        "revision/b968826d9c46dd6066d109eabc6255188de91218",       # HF commit hash in a URL
        "fixture_sha,7e6005269552", "worker_id=80fcxq58vdfrqt",      # ids that are not credentials
        "export RUNPOD_API_KEY=...   ENDPOINT_ID=kbme98hqtjthdl",    # runbook placeholder
    ]
    for s in benign:
        out, hits = redact(s)
        assert out == s and not hits, s
        assert find(s) == []


def test_find_masks_the_match():
    hits = find(f"token={HF}")
    assert {name for name, _ in hits} == {"hf_token", "kv_secret"}   # both patterns see it; neither leaks it
    for _, masked in hits:
        assert HF not in masked and "…" in masked
