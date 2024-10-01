# events.py
from dataclasses import dataclass
from datetime import datetime

@dataclass
class LeadCreatedEvent:
    user_id: str
    lead_id: str
    created_at: datetime
