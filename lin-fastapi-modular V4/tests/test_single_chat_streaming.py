from pathlib import Path


ROOT = Path(__file__).parents[1]
FRONTEND = (ROOT / "app/web/frontend.py").read_text()


def _send_source():
    start = FRONTEND.index("async function send(){")
    end = FRONTEND.index("async function llogs(){", start)
    return FRONTEND[start:end]


def test_send_error_path_can_read_stream_buffers_without_reference_error():
    source = _send_source()
    assert source.count("let reasoningBuffer = '';") == 1
    assert source.count("let contentBuffer = '';") == 1
    assert "if (!contentBuffer) addMsg('lin', describeSendError(e));" in source


def test_send_keeps_the_existing_watch_stream_parser():
    source = _send_source()
    assert "fetch(AU+'/watch'" in source
    assert "response.body.getReader()" in source
    assert "currentEvent === 'reasoning'" in source
    assert "currentEvent === 'text_delta'" in source
    assert "currentEvent === 'tool_step_update'" in source
