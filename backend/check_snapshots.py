import sys
from app.db.database import SessionLocal
from app.models.snapshot import PhaseSnapshot
db = SessionLocal()
snapshots = db.query(PhaseSnapshot).all()
print(f'Total snapshots: {len(snapshots)}')
if snapshots:
    last = snapshots[-1]
    print('Last Snapshot Phase ID:', last.phase_id)
    print('Has snapshot_data:', bool(last.snapshot_data))
    if last.snapshot_data:
        print('Keys:', last.snapshot_data.keys())
        if 'totals' in last.snapshot_data:
            print('totals:', last.snapshot_data['totals'])
        elif 'global_totals' in last.snapshot_data:
            print('global_totals:', last.snapshot_data['global_totals'])
