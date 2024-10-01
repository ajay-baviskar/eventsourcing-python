from events import LeadCreatedEvent

class User:
    def __init__(self, user_id, repository):
        self.user_id = user_id
        self.lead_count = 0
        self.repository = repository
        self.leads = []

    def create_lead(self, lead_id):
        # Increment lead count first
        self.lead_count += 1
        self.leads.append(lead_id)

        # Generic event data for lead creation
        event_data = {
            "event_name": "LeadCreated",
            "lead_id": lead_id,
            "lead_count": self.lead_count,
            "points": 0  # Points for lead creation
        }

        # Save the LeadCreated event
        self.repository.save_event(self.user_id, event_data)

        # Check if the lead count is exactly 5
        if self.lead_count % 5 == 0:
            # Award points
            self.award_points(100, lead_id)  # Pass lead_id when awarding points

    def award_points(self, points, lead_id):
        # Update points and lead count in the database
        self.repository.update_points_and_lead_count(self.user_id, points, self.lead_count)

        # Generic event data for points awarded
        points_event_data = {
            "event_name": "PointsAwarded",
            "lead_id": lead_id,  # Include lead_id here
            "points": points,
            "lead_count": self.lead_count
        }
        
        # Save the PointsAwarded event
        self.repository.save_event(self.user_id, points_event_data)

        print(f"User {self.user_id} awarded {points} points after creating {self.lead_count} leads for lead {lead_id}.")
