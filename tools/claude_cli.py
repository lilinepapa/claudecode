"""Claude Code CLI를 서브프로세스로 호출하는 래퍼."""

import logging
import shutil
import subprocess
import tempfile

logger = logging.getLogger(__name__)


def call_claude(prompt: str, timeout: int = 180) -> str:
    """claude -p 명령으로 Claude Code CLI를 호출하고 응답 텍스트를 반환한다.

    임시 디렉토리에서 실행해 git 레포 컨텍스트 감지를 방지한다.
    """
    if not shutil.which("claude"):
        raise RuntimeError(
            "claude CLI가 설치되어 있지 않습니다.\n"
            "설치: npm install -g @anthropic-ai/claude-code\n"
            "로그인: claude"
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=tmpdir,  # git 레포 밖에서 실행 → 순수 텍스트 생성 모드
        )

    if result.returncode != 0:
        raise RuntimeError(
            f"claude CLI 오류 (exit {result.returncode}): {result.stderr.strip()}"
        )

    return result.stdout.strip()
