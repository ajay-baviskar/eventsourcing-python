from eventsourcing.domain import Aggregate, event

class ReferralAggregate(Aggregate):
    def __init__(self, referrer_id):
        self.referrer_id = referrer_id
        self.referrals = []
        self.points = 0

    @event("ReferralMade")
    def make_referral(self, referred_user_id):
        self.referrals.append(referred_user_id)

    @event("PointsAwarded")
    def award_points(self):
        if len(self.referrals) >= 3:
            self.points += 50
