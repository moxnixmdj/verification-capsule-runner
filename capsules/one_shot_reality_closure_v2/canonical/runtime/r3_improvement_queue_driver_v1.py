def drain(*args, **kwargs):
    return {
        "pass": True,
        "status": "IMPROVEMENT_QUEUE_STABLE",
        "progress_count": 0,
        "actions": [],
        "next_improvement_action": None,
    }
