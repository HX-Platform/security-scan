"""Post a CI/CD result to a Google Chat space as a card.

Every value arrives through the environment, never through string
interpolation — commit subjects and branch names are attacker-controlled.

A webhook problem is reported as a warning and exits 0: a broken notification
must never turn a successful deploy red.
"""

import json
import os
import sys
import urllib.error
import urllib.request

STATUS_STYLE = {
    "success": ("✅", "Succeeded", (0.20, 0.66, 0.33)),
    "failure": ("🔴", "Failed", (0.86, 0.21, 0.27)),
    "cancelled": ("⚪", "Cancelled", (0.50, 0.50, 0.50)),
}


def env(name, default=""):
    return os.environ.get(name, default) or default


def build_card():
    status = env("STATUS", "unknown").lower()
    icon, label, rgb = STATUS_STYLE.get(status, ("❓", status.title(), (0.5, 0.5, 0.5)))

    title = env("TITLE", "workflow")
    repo = env("REPO")
    ref = env("REF")
    sha = env("SHA")
    actor = env("ACTOR")
    run_url = env("RUN_URL")

    # Untrusted, and often long: first line only, clipped.
    subject = env("SUBJECT").splitlines()[0].strip() if env("SUBJECT").strip() else ""
    if len(subject) > 120:
        subject = subject[:117] + "…"

    widgets = []

    if subject:
        widgets.append(
            {
                "decoratedText": {
                    "topLabel": f"{sha[:7]} · {actor}" if sha else actor,
                    "text": subject,
                    "wrapText": True,
                }
            }
        )
    elif sha:
        widgets.append(
            {"decoratedText": {"topLabel": "Commit", "text": f"{sha[:7]} · {actor}"}}
        )

    # One fact per line, "Label: value" split into a labelled row where possible.
    details = [d.strip() for d in env("DETAILS").splitlines() if d.strip()]
    for line in details:
        if ": " in line:
            head, tail = line.split(": ", 1)
            widgets.append(
                {
                    "decoratedText": {
                        "topLabel": head.strip(),
                        "text": tail.strip(),
                        "wrapText": True,
                    }
                }
            )
        else:
            widgets.append({"textParagraph": {"text": line}})

    if run_url:
        button = {
            "text": "View run",
            "onClick": {"openLink": {"url": run_url}},
        }
        if status == "failure":
            button["color"] = {
                "red": rgb[0],
                "green": rgb[1],
                "blue": rgb[2],
                "alpha": 1,
            }
        widgets.append({"buttonList": {"buttons": [button]}})

    subtitle = " · ".join(x for x in (repo.split("/")[-1], ref) if x)

    return {
        # Fallback text drives the mobile push preview and the space list line.
        "text": f"{icon} {title} — {label.lower()}"
        + (f" · {ref}" if ref else ""),
        "cardsV2": [
            {
                "cardId": "cicd-status",
                "card": {
                    "header": {
                        "title": f"{icon} {title}",
                        "subtitle": f"{label} · {subtitle}" if subtitle else label,
                    },
                    "sections": [{"widgets": widgets}] if widgets else [],
                },
            }
        ],
    }


def main():
    webhook = env("WEBHOOK")
    if not webhook:
        print("::warning::GOOGLE_CHAT_WEBHOOK is not set — skipping notification")
        return 0

    payload = json.dumps(build_card()).encode("utf-8")

    if env("DRY_RUN") == "1":
        print(json.dumps(build_card(), indent=2, ensure_ascii=False))
        return 0

    request = urllib.request.Request(
        webhook,
        data=payload,
        headers={"Content-Type": "application/json; charset=UTF-8"},
    )

    for attempt in (1, 2, 3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                print(f"notified Google Chat ({env('TITLE')}: {env('STATUS')})")
                return 0
        except urllib.error.HTTPError as exc:
            body = exc.read()[:400].decode("utf-8", "replace")
            print(f"::warning::Google Chat returned HTTP {exc.code}: {body}")
            if exc.code < 500:
                return 0  # our fault, retrying will not help
        except Exception as exc:  # noqa: BLE001 - never fail the caller
            print(f"::warning::Google Chat request failed ({attempt}/3): {exc}")

    print("::warning::giving up on the Google Chat notification")
    return 0


if __name__ == "__main__":
    sys.exit(main())
