"""Participant study portal mounted by the unified EyeExplore server."""

from __future__ import annotations

import csv
import hmac
import io
import json
import os
import secrets
import smtplib
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Iterator

from flask import (
    Blueprint,
    abort,
    current_app,
    redirect,
    render_template,
    request,
    session,
    url_for,
)


ROOT = Path(__file__).resolve().parent
QUESTIONNAIRE_PATH = ROOT / "questions.json"
SETUP_PATH = ROOT / "study_setup.json"
blueprint = Blueprint(
    "user_study",
    __name__,
    url_prefix="/user-study",
    template_folder="templates",
    static_folder="static",
)
_database_ready = False
_database_init_lock = threading.Lock()


def _database_path() -> Path:
    configured = os.environ.get("USER_STUDY_DB")
    if configured:
        return Path(configured).expanduser().resolve()
    data_dir = Path(os.environ.get("USER_STUDY_DATA_DIR", ROOT / "data")).expanduser()
    return (data_dir / "responses.sqlite3").resolve()


@contextmanager
def _database() -> Iterator[sqlite3.Connection]:
    path = _database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=20)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 20000")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _init_database() -> None:
    with _database() as db:
        db.execute("PRAGMA journal_mode = WAL")
        db.execute(
            """CREATE TABLE IF NOT EXISTS study_sessions (
                id TEXT PRIMARY KEY,
                participant_id TEXT NOT NULL UNIQUE,
                cohort TEXT NOT NULL CHECK (cohort IN ('novice', 'expert')),
                set_number INTEGER NOT NULL CHECK (set_number IN (1, 2)),
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                test_started_at TEXT,
                current_question INTEGER NOT NULL DEFAULT 0,
                current_question_started REAL,
                question_events TEXT NOT NULL DEFAULT '[]',
                overall_rating INTEGER,
                review TEXT,
                completed_at TEXT,
                email_status TEXT NOT NULL DEFAULT 'pending'
            )"""
        )


@blueprint.before_request
def _ensure_database() -> None:
    global _database_ready
    if not _database_ready:
        with _database_init_lock:
            if not _database_ready:
                _init_database()
                _database_ready = True


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load_questions(cohort: str, set_number: int) -> list[dict]:
    try:
        with QUESTIONNAIRE_PATH.open(encoding="utf-8") as stream:
            questionnaire = json.load(stream)
        questions = questionnaire[f"{cohort}_set{set_number}"]
        with SETUP_PATH.open(encoding="utf-8") as stream:
            setup = json.load(stream)
        questions = [_apply_setup_values(question, setup) for question in questions]
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        current_app.logger.exception("Unable to load the configured study questions")
        raise RuntimeError("The study question set is not configured correctly.") from exc
    if not isinstance(questions, list) or len(questions) != 4:
        raise RuntimeError("Each study set must contain exactly four questions.")
    return questions


def _correct_option(cohort: str, set_number: int, question_id: str) -> str | None:
    key = f"{cohort.upper()}_SET{set_number}_{question_id[-2:]}_CORRECT_OPTION"
    try:
        with SETUP_PATH.open(encoding="utf-8") as stream:
            value = json.load(stream).get(key, "")
    except (OSError, json.JSONDecodeError):
        return None
    value = str(value).strip().upper()
    return value if value in {"A", "B", "C", "D"} else None


def _apply_setup_values(question: dict, setup: dict) -> dict:
    """Replace visible {{VARIABLE}} markers from the editable study setup file."""
    rendered = json.loads(json.dumps(question))
    for key, value in setup.items():
        marker = "{{" + key + "}}"

        def replace(item):
            if isinstance(item, str):
                return item.replace(marker, str(value))
            if isinstance(item, list):
                return [replace(child) for child in item]
            if isinstance(item, dict):
                return {name: replace(child) for name, child in item.items()}
            return item

        rendered = replace(rendered)
    return rendered


def _safe_question(question: dict) -> dict:
    return {
        "id": question["id"],
        "title": question["title"],
        "prompt": question["prompt"],
        "steps": question["steps"],
        "visualizations": question["visualizations"],
        "options": question["options"],
        "multiple": bool(question.get("multiple", False)),
    }


def _csrf_token() -> str:
    token = session.get("study_csrf")
    if not token:
        token = secrets.token_urlsafe(32)
        session["study_csrf"] = token
    return token


def _check_csrf() -> None:
    submitted = request.form.get("csrf_token", "")
    expected = session.get("study_csrf", "")
    if not expected or not hmac.compare_digest(submitted, expected):
        abort(400, "The form expired. Please reload the page and try again.")


def _participant_session() -> sqlite3.Row | None:
    session_id = session.get("study_session_id")
    if not session_id:
        return None
    with _database() as db:
        return db.execute(
            "SELECT * FROM study_sessions WHERE id = ?", (session_id,)
        ).fetchone()


def _require_session() -> sqlite3.Row:
    study_session = _participant_session()
    if study_session is None:
        abort(401)
    return study_session


def _send_results_email() -> str:
    recipient = os.environ.get("STUDY_RESULTS_EMAIL", "").strip()
    host = os.environ.get("STUDY_SMTP_HOST", "").strip()
    username = os.environ.get("STUDY_SMTP_USER", "").strip()
    password = os.environ.get("STUDY_SMTP_PASSWORD", "")
    sender = os.environ.get("STUDY_SMTP_FROM", username).strip()
    if not all((recipient, host, username, password, sender)):
        return "not_configured"

    rows = _completed_sessions()
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    question_count = max(
        (len(json.loads(row["question_events"])) for row in rows), default=0
    )
    header = [
        "participant_id", "cohort", "set_number", "started_at", "completed_at"
    ]
    for number in range(1, question_count + 1):
        header.extend(
            [
                f"q{number}_question",
                f"q{number}_prompt",
                f"q{number}_response",
                f"q{number}_response_text",
                f"q{number}_correctness",
                f"q{number}_technical_issue",
                f"q{number}_visualization_ratings",
                f"q{number}_started_at_utc",
                f"q{number}_ended_at_utc",
                f"q{number}_duration_seconds",
            ]
        )
    header.append("review")
    writer.writerow(header)

    for row in rows:
        events = json.loads(row["question_events"])
        values: list[str | int | float] = [
            _csv_safe(row["participant_id"]),
            row["cohort"],
            row["set_number"],
            row["test_started_at"] or row["created_at"],
            row["completed_at"] or "",
        ]
        for number in range(question_count):
            if number < len(events):
                event = events[number]
                response = event.get("response", [])
                values.extend(
                    [
                        _csv_safe(event.get("question_title", "")),
                        _csv_safe(event.get("question_prompt", "")),
                        _csv_safe("; ".join(response) if isinstance(response, list) else str(response)),
                        _csv_safe(event.get("response_text", "")),
                        event.get("correctness", "not_scored"),
                        "yes" if event.get("technical_issue") else "no",
                        _csv_safe(json.dumps(event.get("visualization_ratings", {}), ensure_ascii=False)),
                        event.get("started_at", ""),
                        event.get("ended_at", ""),
                        round(float(event.get("duration_seconds", 0)), 2),
                    ]
                )
            else:
                values.extend(["", "", "", "", "", "", "", "", "", ""])
        values.extend([_csv_safe(row["review"] or "")])
        writer.writerow(values)

    message = EmailMessage()
    message["Subject"] = f"EyeExplore user study results ({len(rows)} completed)"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        "Attached is the current cumulative CSV export of completed EyeExplore "
        "user-study sessions. The source records are also stored in the study database."
    )
    message.add_attachment(
        output.getvalue().encode("utf-8-sig"),
        maintype="text",
        subtype="csv",
        filename="eyeexplore_user_study_results.csv",
    )

    port = int(os.environ.get("STUDY_SMTP_PORT", "587"))
    timeout = float(os.environ.get("STUDY_SMTP_TIMEOUT", "20"))
    use_ssl = os.environ.get("STUDY_SMTP_SSL", "0") == "1"
    try:
        if use_ssl:
            with smtplib.SMTP_SSL(host, port, timeout=timeout) as smtp:
                smtp.login(username, password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(host, port, timeout=timeout) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
                smtp.login(username, password)
                smtp.send_message(message)
        return "sent"
    except Exception:
        current_app.logger.exception("Unable to email the user-study results")
        return "failed"


def _csv_safe(value: str) -> str:
    value = str(value)
    if value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def _completed_sessions() -> list[sqlite3.Row]:
    with _database() as db:
        return db.execute(
            "SELECT * FROM study_sessions WHERE status = 'complete' ORDER BY completed_at, participant_id"
        ).fetchall()


@blueprint.route("/", methods=["GET", "POST"])
def login():
    existing = _participant_session()
    if existing:
        return redirect(url_for(_route_for_status(existing["status"], existing["current_question"])))

    error = None
    if request.method == "POST":
        _check_csrf()
        participant_id_input = request.form.get("participant_id", "").strip()
        password_input = request.form.get("password", "")
        novice_password = "nuserstudy"
        expert_password = "euserstudy"

        if not participant_id_input.isdecimal() or int(participant_id_input) < 1:
            error = "Enter the participant ID given to you by the study leader."
        else:
            participant_id = str(int(participant_id_input))
            novice_match = hmac.compare_digest(password_input, novice_password)
            expert_match = hmac.compare_digest(password_input, expert_password)
            if novice_match == expert_match:
                error = "The access code is not valid. Please check it with the study leader."
            else:
                cohort = "novice" if novice_match else "expert"
                set_number = 1 if int(participant_id) % 2 else 2
                with _database() as db:
                    existing_id = db.execute(
                        "SELECT * FROM study_sessions WHERE participant_id = ?", (participant_id,)
                    ).fetchone()
                    if existing_id and existing_id["cohort"] != cohort:
                        error = "This participant ID has already been assigned. Please contact the study leader."
                    elif existing_id and existing_id["status"] == "complete":
                        error = "This participant ID has already completed the study. Please contact the study leader."
                    elif existing_id:
                        study_id = existing_id["id"]
                    else:
                        study_id = str(uuid.uuid4())
                        db.execute(
                            """INSERT INTO study_sessions
                            (id, participant_id, cohort, set_number, status, created_at)
                            VALUES (?, ?, ?, ?, 'instructions', ?)""",
                            (study_id, participant_id, cohort, set_number, _utc_now()),
                        )
                if error is None:
                    session.clear()
                    session["study_session_id"] = study_id
                    _csrf_token()
                    return redirect(url_for("user_study.instructions"))

    completed_status = request.args.get("completed", "")
    completed_messages = {
        "sent": "Responses saved and the results email was sent. The next participant may enter their ID and access code.",
        "failed": "Responses saved, but the results email could not be sent. Please notify the study leader. The next participant may continue.",
        "not_configured": "Responses saved. Results email is not configured on this server. The next participant may continue.",
    }
    return render_template(
        "login.html",
        error=error,
        completed_message=completed_messages.get(completed_status),
        csrf_token=_csrf_token(),
    )


def _route_for_status(status: str, current_question: int) -> str:
    if status == "instructions":
        return "user_study.instructions"
    if status == "in_progress":
        return "user_study.question"
    if status == "question_rating":
        return "user_study.question_rating"
    if status == "review":
        return "user_study.review"
    return "user_study.complete"


@blueprint.route("/instructions", methods=["GET", "POST"])
def instructions():
    study_session = _require_session()
    if study_session["status"] != "instructions":
        return redirect(url_for(_route_for_status(study_session["status"], study_session["current_question"])))
    questions = _load_questions(study_session["cohort"], study_session["set_number"])
    if request.method == "POST":
        _check_csrf()
        now = time.time()
        with _database() as db:
            db.execute(
                """UPDATE study_sessions SET status = 'in_progress', test_started_at = ?,
                current_question = 1, current_question_started = ? WHERE id = ?""",
                (_utc_now(), now, study_session["id"]),
            )
        return redirect(url_for("user_study.question"))
    return render_template(
        "instructions.html",
        csrf_token=_csrf_token(),
        cohort=study_session["cohort"],
        set_number=study_session["set_number"],
        question_count=len(questions),
    )


@blueprint.route("/question", methods=["GET", "POST"])
def question():
    study_session = _require_session()
    if study_session["status"] != "in_progress":
        return redirect(url_for(_route_for_status(study_session["status"], study_session["current_question"])))
    questions = _load_questions(study_session["cohort"], study_session["set_number"])
    number = int(study_session["current_question"])
    if number < 1 or number > len(questions):
        return redirect(url_for("user_study.review"))
    if not study_session["current_question_started"]:
        now = time.time()
        with _database() as db:
            db.execute(
                "UPDATE study_sessions SET current_question_started = ? WHERE id = ?",
                (now, study_session["id"]),
            )
        study_session = _require_session()

    raw_question = questions[number - 1]
    safe_question = _safe_question(raw_question)
    if request.method == "POST":
        _check_csrf()
        if request.form.get("question_id") != safe_question["id"]:
            abort(409, "This question is no longer active. Continue with the current question.")
        selected = request.form.getlist("answer") if safe_question["multiple"] else [request.form.get("answer", "")]
        valid_options = {option["id"] for option in safe_question["options"]}
        selected = [option for option in selected if option in valid_options]
        if not selected:
            return render_template(
                "question.html",
                question=safe_question,
                question_number=number,
                question_count=len(questions),
                error="Please choose an answer before continuing.",
                csrf_token=_csrf_token(),
            ), 400

        ended_epoch = time.time()
        started_epoch = float(study_session["current_question_started"] or ended_epoch)
        events = json.loads(study_session["question_events"])
        events.append(
            {
                "question_id": safe_question["id"],
                "question_title": safe_question["title"],
                "question_prompt": safe_question["prompt"],
                "started_at": datetime.fromtimestamp(started_epoch, timezone.utc).isoformat(timespec="milliseconds"),
                "ended_at": datetime.fromtimestamp(ended_epoch, timezone.utc).isoformat(timespec="milliseconds"),
                "duration_seconds": max(0, ended_epoch - started_epoch),
                "response": selected if safe_question["multiple"] else selected[0],
                "response_text": "; ".join(
                    f"{option['id']}. {option['text']}"
                    for option in safe_question["options"]
                    if option["id"] in selected
                ),
                "correctness": (
                    "technical_issue"
                    if selected[0] == "D"
                    else "not_scored"
                    if _correct_option(study_session["cohort"], study_session["set_number"], safe_question["id"]) is None
                    else "correct"
                    if selected[0] == _correct_option(study_session["cohort"], study_session["set_number"], safe_question["id"])
                    else "incorrect"
                ),
                "technical_issue": selected[0] == "D",
                "visualization_ratings": {},
            }
        )
        next_status = "question_rating"
        with _database() as db:
            db.execute(
                """UPDATE study_sessions SET question_events = ?,
                current_question_started = NULL, status = ? WHERE id = ?""",
                (json.dumps(events, ensure_ascii=False), next_status, study_session["id"]),
            )
        return redirect(url_for("user_study.question_rating"))

    return render_template(
        "question.html",
        question=safe_question,
        question_steps=safe_question["steps"],
        question_number=number,
        question_count=len(questions),
        error=None,
        csrf_token=_csrf_token(),
    )


@blueprint.route("/question-rating", methods=["GET", "POST"])
def question_rating():
    study_session = _require_session()
    if study_session["status"] != "question_rating":
        return redirect(url_for(_route_for_status(study_session["status"], study_session["current_question"])))
    questions = _load_questions(study_session["cohort"], study_session["set_number"])
    number = int(study_session["current_question"])
    question_data = questions[number - 1]
    events = json.loads(study_session["question_events"])
    if len(events) < number:
        abort(409, "The answer for this question has not been saved.")
    event = events[number - 1]
    if request.method == "POST":
        _check_csrf()
        ratings = {}
        for index, visualization in enumerate(question_data["visualizations"]):
            try:
                rating = int(request.form.get(f"rating_{index}", ""))
                if not 1 <= rating <= 10:
                    raise ValueError
            except ValueError:
                return render_template(
                    "question_rating.html", question=question_data,
                    question_number=number, question_count=len(questions),
                    rating_scale=_rating_scale(), error="Rate each visualization from 1 to 10.",
                    csrf_token=_csrf_token(),
                ), 400
            ratings[visualization] = rating
        event["visualization_ratings"] = ratings
        events[number - 1] = event
        next_number = number + 1
        next_status = "in_progress" if next_number <= len(questions) else "review"
        with _database() as db:
            db.execute(
                "UPDATE study_sessions SET question_events = ?, current_question = ?, status = ? WHERE id = ?",
                (json.dumps(events, ensure_ascii=False), next_number, next_status, study_session["id"]),
            )
        return redirect(url_for("user_study.question" if next_status == "in_progress" else "user_study.review"))
    return render_template(
        "question_rating.html", question=question_data, question_number=number,
        question_count=len(questions), rating_scale=_rating_scale(), error=None,
        csrf_token=_csrf_token(),
    )


def _rating_scale() -> list[dict]:
    with QUESTIONNAIRE_PATH.open(encoding="utf-8") as stream:
        return json.load(stream)["rating_scale"]


@blueprint.route("/review", methods=["GET", "POST"])
def review():
    study_session = _require_session()
    if study_session["status"] == "complete":
        return redirect(url_for("user_study.complete"))
    if study_session["status"] != "review":
        return redirect(url_for(_route_for_status(study_session["status"], study_session["current_question"])))

    error = None
    if request.method == "POST":
        _check_csrf()
        review_text = "" if request.form.get("skip_review") else request.form.get("review", "").strip()
        if len(review_text) > 5000:
            error = "Please keep your review under 5,000 characters."
        if not error:
            with _database() as db:
                db.execute(
                    """UPDATE study_sessions SET status = 'complete', review = ?,
                    completed_at = ?, email_status = 'sending'
                    WHERE id = ?""",
                    (review_text, _utc_now(), study_session["id"]),
                )
            try:
                email_status = _send_results_email()
            except Exception:
                current_app.logger.exception("Unable to build the user-study results email")
                email_status = "failed"
            with _database() as db:
                db.execute(
                    "UPDATE study_sessions SET email_status = ? WHERE id = ?",
                    (email_status, study_session["id"]),
                )
            session.clear()
            return redirect(url_for("user_study.login", completed=email_status))

    return render_template("review.html", error=error, csrf_token=_csrf_token())


@blueprint.route("/complete")
def complete():
    study_session = _require_session()
    if study_session["status"] != "complete":
        return redirect(url_for(_route_for_status(study_session["status"], study_session["current_question"])))
    status_messages = {
        "sent": "Your responses have been saved and the cumulative results were emailed to the study team.",
        "failed": "Your responses are safely saved, but email delivery failed. Please tell the study leader.",
        "not_configured": "Your responses are saved. Results email is not configured on this server.",
        "sending": "Your responses are saved. Email delivery is still being processed.",
    }
    return render_template(
        "complete.html",
        message=status_messages.get(study_session["email_status"], "Your responses have been saved."),
    )
