"""Vaccination scheduling logic: which vaccines are due/overdue/done per batch."""
from inventory.models import Batch

from .models import HealthRecord, VaccinationSchedule

# A vaccine counts as "due soon" if the batch will reach its day_of_age within
# this many days; "overdue" once the batch is past it and no record exists.
DUE_SOON_WINDOW_DAYS = 3


def _has_vaccination(batch, vaccine_name):
    return batch.health_records.filter(
        record_type=HealthRecord.RecordType.VACCINATION,
        name__iexact=vaccine_name,
    ).exists()


def batch_vaccination_status(batch):
    """List of {schedule, status, days} for every schedule entry applying to a
    batch. status ∈ {done, overdue, due_soon, upcoming}."""
    age = batch.age_in_days
    rows = []
    for sched in VaccinationSchedule.objects.all():
        if not sched.applies_to(batch):
            continue
        done = _has_vaccination(batch, sched.vaccine_name)
        days = sched.day_of_age - age  # +ve = days until due
        if done:
            status = 'done'
        elif days < 0:
            status = 'overdue'
        elif days <= DUE_SOON_WINDOW_DAYS:
            status = 'due_soon'
        else:
            status = 'upcoming'
        rows.append({'schedule': sched, 'status': status, 'days': days})
    return rows


def due_vaccinations(active_only=True):
    """Farm-wide list of (batch, schedule, status) needing attention now
    (overdue or due_soon), for the dashboard/health alerts."""
    batches = Batch.objects.all()
    if active_only:
        batches = batches.filter(status=Batch.Status.ACTIVE)
    alerts = []
    for batch in batches.select_related('breed'):
        for row in batch_vaccination_status(batch):
            if row['status'] in ('overdue', 'due_soon'):
                alerts.append({'batch': batch, **row})
    # Overdue first, then soonest due.
    alerts.sort(key=lambda a: (a['status'] != 'overdue', a['days']))
    return alerts
