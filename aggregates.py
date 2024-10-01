# aggregates.py
from events import LeadCreatedEvent

class User:
    def __init__(self, user_id, repository):
        self.user_id = user_id
        self.lead_count = 0
        self.repository = repository
        self.leads = []

    def create_lead(self, lead_id):
        self.leads.append(lead_id)
        self.lead_count += 1
        self.check_points_awarded()
        # Log the lead creation event
        self.repository.log_event(self.user_id, 'LeadCreated', lead_id)

    def check_points_awarded(self):
        if self.lead_count  % 5 == 0:
            self.award_points(100)

    def award_points(self, points):
        self.repository.update_points_and_lead_count(self.user_id, points, self.lead_count)
        # Log the points awarded event
        self.repository.log_event(self.user_id, 'PointsAwarded', points=points)
        print(f"User {self.user_id} awarded {points} points and has created {self.lead_count} leads.")
