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
import re
import subprocess
import urllib.error
import urllib.request

LOG_PATH = "/tmp/build.log"
TAIL_LINES = 150
ISSUE_NUMBER = 1
# SDK/platform kurulumuyla ilgili satirlari (tail'in disinda kalmis olsa bile)
# ayrica yakalamak icin desenler - "Available Android APIs are ()" hatasinin
# ASIL SEBEBININ (sdkmanager platform indirme/lisans kabul adimi nerede ve
# nasil basarisiz oldu) tail'den once, log'un cok daha erken bir yerinde
# olmasi kuvvetle muhtemel.
GREP_PATTERNS = [
    r"sdkmanager",
    r"[Ll]icense",
    r"platform[s]?;android-",
    r"build-tools",
    r"Available Android APIs",
    r"Requested API target",
    r"cmdline-tools",
    r"ANDROIDAPI",
]


def build_body(sha, run_url, lines):
    tail = "".join(lines[-TAIL_LINES:])

    grep_re = re.compile("|".join(GREP_PATTERNS))
    matched = [ln for ln in lines if grep_re.search(ln)]
    grep_block = "".join(matched[-120:]) if matched else "(eslesen satir yok)\n"

    return (
        f"### Derleme basarisiz - commit {sha}\n"
        f"Run: {run_url}\n\n"
        f"**SDK/platform ile ilgili satirlar (tum log icinde grep):**\n"
        f"```\n{grep_block}\n```\n\n"
        f"**Son {TAIL_LINES} satir (hatanin oldugu yer):**\n"
        f"```\n{tail}\n```\n"
    )


def main():
    try:
        with open(LOG_PATH, "r", errors="replace") as f:
            lines = f.readlines()
    except FileNotFoundError:
        lines = ["(build.log bulunamadi - docker adimi loga ulasamadan mi patladi?)\n"]

    sha = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True
    ).stdout.strip()
    run_url = (
        f"{os.environ.get('GITHUB_SERVER_URL', '')}/"
        f"{os.environ.get('GITHUB_REPOSITORY', '')}/actions/runs/"
        f"{os.environ.get('GITHUB_RUN_ID', '')}"
    )
    body = build_body(sha, run_url, lines)

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
