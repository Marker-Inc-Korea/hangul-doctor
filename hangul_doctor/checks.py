"""Environment checks: warn before the symptom happens."""
import os
import platform
from pathlib import Path

from . import slug


def _f(level, title, detail, refs=(), fix=None):
    return {"level": level, "title": title, "detail": detail,
            "refs": list(refs), "fix": fix}


def check_no_flicker():
    v = os.environ.get("CLAUDE_CODE_NO_FLICKER")
    if v and v not in ("0", "false", "False"):
        return _f("warn",
                  "CLAUDE_CODE_NO_FLICKER 가 켜져 있습니다",
                  "이 렌더러에서 한글·일본어·중국어를 복사하면 깨진다는 신고가 여러 건 있습니다. "
                  "공식적으로는 수정됐으나 재발 보고가 있습니다.",
                  [50605, 44118, 42703, 42417, 42406],
                  "unset CLAUDE_CODE_NO_FLICKER")
    return None


def check_project_path(cwd=None):
    cwd = Path(cwd or Path.cwd()).resolve()
    s, hit, ambiguous = slug.collision_risk(cwd)
    if not ambiguous:
        return None
    others = [x for x in slug.existing_slugs() if x == s]
    detail = (f"현재 경로가 저장소 폴더 이름으로 바뀔 때 '{s}' 가 됩니다.\n"
              "   영숫자가 아닌 글자는 전부 '-' 로 바뀝니다. 한글은 한 글자가 '-' 하나입니다.\n"
              "   글자 수가 같은 다른 한글 경로와 같은 폴더를 쓰게 되고,\n"
              "   그러면 대화 기록과 기억이 조용히 섞입니다.")
    if others:
        detail += "\n   이미 같은 이름의 폴더가 존재합니다."
    return _f("warn" if others else "info",
              "프로젝트 경로에 영문이 아닌 글자가 있습니다",
              detail, [93743, 91735, 70076, 70674, 87552],
              "프로젝트를 영문 경로에 두거나, 영문 경로에 두고 심볼릭 링크를 거세요")


def check_platform():
    out = []
    sysname = platform.system()
    if sysname == "Windows":
        out.append(_f("info",
                      "윈도우에서 실행 중입니다",
                      "한글 입력이 깨지거나 붙여넣기가 mojibake 되는 신고가 윈도우에 집중돼 있습니다.",
                      [65806, 73064, 51768],
                      "Git Bash + winpty 조합이 낫다는 커뮤니티 보고가 있습니다 (#51768)"))
    if os.environ.get("TERM_PROGRAM") == "vscode":
        out.append(_f("info",
                      "VS Code 통합 터미널입니다",
                      "긴 세션 후 글자가 손상되거나 한글 파일 링크가 열리지 않는 신고가 있습니다.",
                      [59915, 59163, 86829, 93638], None))
    return out


def run_all(cwd=None):
    found = []
    for fn in (check_no_flicker, lambda: check_project_path(cwd)):
        r = fn()
        if r:
            found.append(r)
    found.extend(check_platform())
    return found
