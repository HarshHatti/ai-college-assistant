from datetime import date, datetime, timedelta


def generate_study_plan(subject, exam_date, topics, hours_per_day, start_date=None):
    """Split topics across the days left before the exam.
    The last day before the exam is kept for revision."""
    # --- validate inputs ---
    subject = (subject or "").strip()
    if not subject:
        return {"success": False, "error": "Subject cannot be empty."}

    try:
        exam = datetime.strptime(exam_date, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return {"success": False, "error": "exam_date must be in YYYY-MM-DD format."}

    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else date.today()
    except ValueError:
        return {"success": False, "error": "start_date must be in YYYY-MM-DD format."}

    if isinstance(topics, str):  # the AI sometimes sends "a, b, c" as one string
        topics = topics.split(",")
    topics = [t.strip() for t in (topics or []) if str(t).strip()]
    if not topics:
        return {"success": False, "error": "Give at least one topic."}

    try:
        hours = float(hours_per_day)
    except (ValueError, TypeError):
        return {"success": False, "error": "hours_per_day must be a number."}
    if not 0.5 <= hours <= 12:
        return {"success": False, "error": "hours_per_day must be between 0.5 and 12."}

    # --- work out the days ---
    if exam <= start:
        return {"success": False, "error": "The exam date must be after the start date."}

    days = [start + timedelta(days=i) for i in range((exam - start).days)]
    revision_day = days.pop() if len(days) >= 3 else None  # keep last day for revision

    slots_per_day = int(hours * 2)  # work in 30-minute slots
    total_slots = len(days) * slots_per_day
    if total_slots < len(topics):
        return {"success": False, "error": "Not enough study time for this many topics. Add hours or remove topics."}

    # --- give each topic an equal number of slots, in order ---
    base, extra = divmod(total_slots, len(topics))
    slots = []
    for i, topic in enumerate(topics):
        slots += [topic] * (base + (1 if i < extra else 0))

    # --- fill each day ---
    plan = []
    for d_index, d in enumerate(days):
        day_slots = slots[d_index * slots_per_day:(d_index + 1) * slots_per_day]
        sessions = []
        for topic in dict.fromkeys(day_slots):  # unique topics, keeps order
            sessions.append({"topic": topic, "hours": day_slots.count(topic) / 2})
        plan.append({"date": d.isoformat(), "day": d.strftime("%a"), "sessions": sessions})

    if revision_day:
        plan.append({
            "date": revision_day.isoformat(),
            "day": revision_day.strftime("%a"),
            "sessions": [{"topic": "Revision of all topics", "hours": hours}],
        })

    return {"success": True, "subject": subject, "exam_date": exam.isoformat(), "plan": plan}


if __name__ == "__main__":
    result = generate_study_plan(
        "Data Structures", "2026-10-26", ["Arrays", "Linked Lists", "Trees"], 2,
        start_date="2026-10-22",
    )
    for item in result["plan"]:
        print(item)
    print(generate_study_plan("DS", "2026-10-01", ["Arrays"], 2, start_date="2026-10-22"))  # should fail