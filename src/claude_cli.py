"""Claude Code CLI(`claude -p`)를 호출한다. API 키 없이 구독 계정 사용."""
from __future__ import annotations
import json, shutil, subprocess
from src.common import get_logger
log = get_logger(__name__)

def available() -> bool:
    return shutil.which("claude") is not None

def ask(prompt: str, system: str = "", model: str | None = None, timeout: int = 600) -> str:
    """헤드리스로 한 번 묻고 텍스트 응답을 돌려준다."""
    cmd = ["claude", "-p", "--output-format", "text"]
    if system:
        cmd += ["--append-system-prompt", system]
    if model:
        cmd += ["--model", model]
    log.info("claude -p 호출 (model=%s, %d자)", model or "기본", len(prompt))
    r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"claude CLI 실패: {r.stderr.strip()[:300]}")
    return r.stdout.strip()

def ask_json(prompt: str, system: str = "", model: str | None = None) -> dict:
    text = ask(prompt + "\n\nJSON 객체만 출력하세요. 코드 블록 없이.", system, model)
    text = text.strip().strip("`").removeprefix("json").strip()
    return json.loads(text)
