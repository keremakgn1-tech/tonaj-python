"""CI yardimci script'i: build.log'un son kismini bir GitHub issue yorumu
olarak gonderir. build-apk.yml'deki "APK derle" adimi basarisiz oldugunda
(if: failure()) calisir; GITHUB_TOKEN ortam degiskenini ve /tmp/build.log
dosyasini kullanir.

Ayri bir dosya olarak tutulur (YAML "run:" blogunun icine gomulu bir
heredoc olarak DEGIL) cunku YAML blok girintisi heredoc govdesine oldugu
gibi tasindiginda uretilen python kodu satir basi girintili top-level
ifadelere donusur ve "IndentationError" ile bu tani adiminin kendisi
sessizce basarisiz olur - build.log'daki asil hatayi hic gormeden.
"""
import json
import os
import subprocess
import urllib.error
import urllib.request

LOG_PATH = "/tmp/build.log"
TAIL_LINES = 150
ISSUE_NUMBER = 1


def main():
    try:
        with open(LOG_PATH, "r", errors="replace") as f:
            lines = f.readlines()
    except FileNotFoundError:
        lines = ["(build.log bulunamadi - docker adimi loga ulasamadan mi patladi?)\n"]

    tail = "".join(lines[-TAIL_LINES:])
    sha = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True
    ).stdout.strip()
    run_url = (
        f"{os.environ.get('GITHUB_SERVER_URL', '')}/"
        f"{os.environ.get('GITHUB_REPOSITORY', '')}/actions/runs/"
        f"{os.environ.get('GITHUB_RUN_ID', '')}"
    )
    body = f"### Derleme basarisiz - commit {sha}\nRun: {run_url}\n\n```\n{tail}\n```\n"

    repo = os.environ["GITHUB_REPOSITORY"]
    url = f"https://api.github.com/repos/{repo}/issues/{ISSUE_NUMBER}/comments"
    req = urllib.request.Request(
        url,
        data=json.dumps({"body": body}).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            print(resp.status, resp.read().decode())
    except urllib.error.HTTPError as e:
        print("HTTP HATA", e.code, e.read().decode())
        raise


if __name__ == "__main__":
    main()
