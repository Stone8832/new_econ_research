from otree.api import *
import random


doc = """
Treatment 1: Exogenous firms + internal constant returns (linear public good).
"""


class C(BaseConstants):
    NAME_IN_URL = 'pg_exogenous'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 30

    ENDOWMENT = 8

    #Table 2: MCPR alpha by firm size n (index = n)
    MPCR_CONSTANT = [0,0, 0.65, 0.55, 0.49, 0.45, 0.42]

    #Timing per period to allocate effort between firm and themselves
    DECISION_SECONDS = 60
    #Timing for information relay sub-period
    INFO_SECONDS =30

    #Exogenous block structure
    BLOCK_LENGTH = 10  #Number of rounds before reshuffle (30 rounds total)
    EXO_SIZES = [2,3,4,5,6] #Sums to 20

class Subsession(BaseSubsession):
    pass

#Need to implement code so there are no repeats
def creating_session(subsession: Subsession):
    # Regroup at rounds 1, 11, 21; fixed inside each block
    if subsession.round_number in [1, 11, 21]:
        players = subsession.get_players()
        if len(players) != sum(C.EXO_SIZES):
            raise Exception(
                f'T1 requires exactly 20 participants; currently {len(players)}'
            )

        random.shuffle(players)
        matrix = []
        idx = 0
        for size in C.EXO_SIZES:
            matrix.append(players[idx: idx + size])
            idx += size
        subsession.set_group_matrix(matrix)
    else:
        if subsession.round_number <= 10:
            subsession.group_like_round(1)
        elif subsession.round_number <= 20:
            subsession.group_like_round(11)
        else:
            subsession.group_like_round(21)


class Group(BaseGroup):
    total_effort = models.IntegerField(initial=0)
    firm_size = models.IntegerField(initial=0)
    per_capita_effort = models.FloatField(initial=0)
    per_capita_payout = models.FloatField(initial=0)


class Player(BasePlayer):
    effort_to_firm = models.IntegerField(
        min=0, max=C.ENDOWMENT,
        label = "How many units of effort do you allocate to your firm"
    )
    payoff_points = models.FloatField(initial=0)

#add your own functions here

#Payoff function
def set_payoffs(group: Group):
    players = group.get_players()
    n = len(players)
    group.firm_size = n

    total_effort = sum(p.effort_to_firm for p in players)
    group.total_effort = total_effort
    group.per_capita_effort = total_effort / n if n else 0

    alpha = C.MPCR_CONSTANT[n]
    group.per_capita_payout = alpha * total_effort

    for p in players:
        # payoff in points for now
        p.payoff = (C.ENDOWMENT - p.effort_to_firm) + group.per_capita_payout
# PAGES
class Decision(Page):
    form_model = 'player'
    form_fields = ['effort_to_firm']
    timeout_seconds = C.DECISION_SECONDS
    timeout_submission = {'effort_to_firm': 0}


class ResultsWaitPage(WaitPage):
    after_all_players_arrive = set_payoffs


class Results(Page):
    pass


page_sequence = [Decision, ResultsWaitPage, Results]