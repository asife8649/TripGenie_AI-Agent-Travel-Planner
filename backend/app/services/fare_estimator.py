"""Distance-based fare/duration ESTIMATES for train and bus.

Used only when no live fare is available (Google Routes rarely returns Indian
rail/bus fares and redBus has no public API). Every value produced here is
labelled as an estimate in the UI and PDF. Tune the constants for your region.
"""

# Approximate all-in fare per km (base + reservation + GST) for ordinary trains.
TRAIN_RATE_PER_KM = {"SL": 0.55, "3A": 1.45, "2A": 2.10}
TRAIN_MIN_FARE = {"SL": 120, "3A": 450, "2A": 650}

# Approximate bus fare per km.
BUS_RATE_PER_KM = {"Non-AC": 1.25, "AC Seater": 1.90, "AC Sleeper": 2.60}
BUS_MIN_FARE = {"Non-AC": 60, "AC Seater": 120, "AC Sleeper": 250}

AVG_SPEED_KMPH = {"train": 52.0, "bus": 42.0}


def _round_to_5(value: float) -> float:
    return float(int(round(value / 5.0) * 5))


def estimate_train_fares(distance_km):
    if not distance_km or distance_km <= 0:
        return []
    return [
        {"class": cls, "fare": _round_to_5(max(TRAIN_MIN_FARE[cls], distance_km * rate))}
        for cls, rate in TRAIN_RATE_PER_KM.items()
    ]


def estimate_bus_fares(distance_km):
    if not distance_km or distance_km <= 0:
        return []
    return [
        {"class": cls, "fare": _round_to_5(max(BUS_MIN_FARE[cls], distance_km * rate))}
        for cls, rate in BUS_RATE_PER_KM.items()
    ]


def estimate_duration_minutes(distance_km, mode):
    if not distance_km or distance_km <= 0:
        return None
    speed = AVG_SPEED_KMPH.get(mode, 45.0)
    return int(round(distance_km / speed * 60 / 5.0) * 5)


def format_minutes(value):
    try:
        minutes = int(round(float(value)))
    except (TypeError, ValueError):
        return None
    if minutes < 0:
        return None
    hours, mins = divmod(minutes, 60)
    if hours and mins:
        return f"{hours} hr {mins} min"
    if hours:
        return f"{hours} hr"
    return f"{mins} min"
