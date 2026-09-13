"""hangul-doctor - diagnose CJK / Korean problems in coding-agent workspaces."""
import argparse
import sys
from pathlib import Path

from . import __version__, checks, data, scan

C = {"warn": "\033[33m", "info": "\033[36m", "bad": "\033[31m",
     "ok": "\033[32m", "dim": "\033[2m", "off": "\033[0m"}


def _c(key, s):
    return f"{C[key]}{s}{C['off']}" if sys.stdout.isatty() else s


def _refs(nums):
    return "" if not nums else _c("dim", "  " + " ".join(f"#{n}" for n in nums))


def cmd_check(args):
    found = checks.run_all(args.path)
    print(_c("dim", f"환경 점검  ({Path(args.path or Path.cwd()).resolve()})\n"))
    if not found:
        print(_c("ok", "  알려진 문제 조건에 해당하지 않습니다."))
        return 0
    for f in found:
        mark = "!" if f["level"] == "warn" else "-"
        print(f"{_c(f['level'], mark)} {f['title']}{_refs(f['refs'])}")
        for line in f["detail"].split("\n"):
            print(f"   {line.strip() if line.startswith('   ') else line}")
        if f["fix"]:
            print(_c("dim", f"   → {f['fix']}"))
        print()
    return 1


def cmd_why(args):
    q = " ".join(args.symptom)
    hits = []
    for it in data.issues():
        hay = " ".join(it["symptoms_ko"] + it.get("symptoms_en", []) +
                       [it["title_ko"], it["title_en"]])
        score = sum(1 for tok in q.replace(",", " ").split() if tok and tok in hay)
        if score:
            hits.append((score, it))
    if not hits:
        print(f"'{q}' 에 맞는 항목을 못 찾았습니다.\n")
        print("등록된 증상 예시:")
        for it in data.issues():
            print(f"  - {it['symptoms_ko'][0]}")
        return 1
    hits.sort(key=lambda x: -x[0])
    for _, it in hits[:args.limit]:
        state = {"open": "미해결", "closed": "수정됨", "n/a": "-"}.get(it["state"], it["state"])
        head = f"{it['title_ko']}  [{state}]"
        print(_c("warn" if it["state"] == "open" else "info", head) + _refs(it["issues"]))
        if it.get("reactions"):
            print(_c("dim", f"  공감 {it['reactions']}명"))
        print(f"  원인  {it['cause_ko']}")
        print(f"  대처  {it['workaround_ko']}")
        print(_c("dim", f"  대응  {' / '.join(it['response'])}"))
        print()
    return 0


def cmd_scan(args):
    root = Path(args.path or ".").resolve()
    print(_c("dim", f"작업 공간 검사  ({root})\n"))
    r = scan.run_all(root)
    n = 0

    if r["replacement"]:
        n += len(r["replacement"])
        print(_c("bad", f"! 깨진 글자(U+FFFD)가 남아 있는 파일 {len(r['replacement'])}개") + _refs([93848, 43746]))
        for h in r["replacement"][:args.limit]:
            print(f"   {h['path']}:{h['line']}  ({h['count']}개)")
        print(_c("dim", "   되돌릴 수 없습니다. 해당 부분을 다시 생성하도록 요청하세요.\n"))

    if r["escapes"]:
        n += len(r["escapes"])
        print(_c("bad", f"! 한글이 이스케이프로 박힌 파일 {len(r['escapes'])}개") + _refs([83033]))
        for h in r["escapes"][:args.limit]:
            print(f"   {h['path']}:{h['line']}  ({h['count']}개, 예: {h['sample']})")
        print(_c("dim", "   모델이 한글을 그대로 쓰지 않고 코드로 바꿔 쓴 흔적입니다.\n"))

    nz = r["normalization"]
    if nz["mixed"]:
        n += 1
        print(_c("warn", "! 한글 파일명 저장 방식이 섞여 있습니다") + _refs([84966, 86829]))
        print(f"   합친 방식 {len(nz['nfc'])}개 / 풀어쓴 방식 {len(nz['nfd'])}개")
        for p in nz["nfd"][:args.limit]:
            print(f"   {p}")
        print(_c("dim", "   에이전트가 '파일이 없다'고 할 수 있습니다.\n"))

    if r["legacy"]:
        n += len(r["legacy"])
        print(_c("warn", f"! 예전 인코딩으로 저장된 파일 {len(r['legacy'])}개"))
        for h in r["legacy"][:args.limit]:
            print(f"   {h['path']}  ({h['encoding']})")
        print(_c("dim", "   그대로 읽으면 깨집니다.\n"))

    if n == 0:
        print(_c("ok", "  문제를 찾지 못했습니다."))
        return 0
    return 1


def cmd_issues(args):
    m = data.meta()
    print(f"조사 기준 {m['source']}")
    print(f"수집 {m['surveyed']}건 중 미해결 {m['open_at_survey']}건 (하한선)\n")
    for it in data.issues():
        state = {"open": "미해결", "closed": "수정됨"}.get(it["state"], "-")
        print(f"  [{state}] {it['title_ko']}{_refs(it['issues'])}")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="hangul-doctor",
        description="한글·CJK 환경에서 코딩 에이전트가 겪는 문제를 진단합니다.")
    p.add_argument("--version", action="version", version=f"hangul-doctor {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="환경이 알려진 문제 조건에 걸리는지 확인")
    c.add_argument("path", nargs="?", default=None)
    c.set_defaults(fn=cmd_check)

    w = sub.add_parser("why", help="증상으로 원인 찾기")
    w.add_argument("symptom", nargs="+")
    w.add_argument("-n", "--limit", type=int, default=3)
    w.set_defaults(fn=cmd_why)

    s = sub.add_parser("scan", help="작업 공간에서 이미 망가진 흔적 찾기")
    s.add_argument("path", nargs="?", default=".")
    s.add_argument("-n", "--limit", type=int, default=5)
    s.set_defaults(fn=cmd_scan)

    i = sub.add_parser("issues", help="알려진 문제 목록")
    i.set_defaults(fn=cmd_issues)

    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
