from operator import truediv

from otree.api import *
import random
import math

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

#Helper function to build valid groups
def build_exogenous_matrix(players, sizes, current_round, max_tries=5000):
    sizes_order = sorted(sizes, reverse=True)

    for _ in range(max_tries):
        remaining = players.copy()
        random.shuffle(remaining)
        chosen_groups = []
        ok = True

        for size in sizes_order:
            eligible = []
            for p in remaining:
                size_by_block = p.participant.vars.get('size_by_block', {})
                # only sizes from earlier blocks (keys < current_round)
                past_sizes = [v for k, v in size_by_block.items() if k < current_round]
                if size not in past_sizes:
                    eligible.append(p)

            if len(eligible) < size:
                ok = False
                break

            members = random.sample(eligible, size)
            chosen_groups.append((size, members))
            for p in members:
                remaining.remove(p)

        if ok and not remaining:
            size_to_members = {s: m for s, m in chosen_groups}
            return [size_to_members[s] for s in sizes]

    raise Exception("Could not find a valid grouping without repeated firm sizes.")



class Subsession(BaseSubsession):
    pass

def creating_session(subsession: Subsession):
    players = subsession.get_players()
    test_mode = subsession.session.config.get('test_mode', False)

    if subsession.round_number in [1, 11, 21]:

        if (not test_mode) and len(players) != sum(C.EXO_SIZES):
            raise Exception(
                f'T1 requires exactly 20 participants; currently {len(players)}'
            )

        if test_mode:
            # simple grouping for testing: groups of 2, last group may be smaller
            random.shuffle(players)
            matrix = []
            i = 0
            while i < len(players):
                matrix.append(players[i:i+2])
                i += 2
            subsession.set_group_matrix(matrix)
        else:
            matrix = build_exogenous_matrix(players, C.EXO_SIZES, subsession.round_number)
            subsession.set_group_matrix(matrix)

            # record each participant's size assignment for this block start
            for p in subsession.get_players():
                current_size = len(p.group.get_players())
                size_by_block = dict(p.participant.vars.get('size_by_block', {}))
                size_by_block[subsession.round_number] = current_size  # keys: 1, 11, 21
                p.participant.vars['size_by_block'] = size_by_block


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

    returns_type = group.session.config.get('returns_type', 'constant')

    #Payoffs for treatment 1 and 2, either constant or increasing
    if returns_type == 'constant':
        alpha = C.MPCR_CONSTANT[n]
        group.per_capita_payout = alpha * total_effort
    elif returns_type == 'increasing':
        a = float(group.session.config.get('a', 0.2496))
        b = float(group.session.config.get('b', 1.5952))

        output = a * (total_effort ** b) if total_effort > 0 else 0.0
        group.per_capita_payout = output / n
    else:
        raise Exception(f"Unknown returns_type: {returns_type}")

    for p in players:
        # payoff in points for now
        p.payoff = (C.ENDOWMENT - p.effort_to_firm) + group.per_capita_payout


#PAGES
class Decision(Page):
    form_model = 'player'
    form_fields = ['effort_to_firm']
    timeout_seconds = C.DECISION_SECONDS
    timeout_submission = {'effort_to_firm': 0}


class ResultsWaitPage(WaitPage):
    after_all_players_arrive = set_payoffs


class Results(Page):
    pass
class Relay(Page):
    timeout_seconds = C.INFO_SECONDS

    @staticmethod
    def vars_for_template(player: Player):
        rows = []
        for g in player.subsession.get_groups():
            rows.append(dict(
                firm_size=len(g.get_players()),
                per_capita_effort=g.per_capita_effort,
                per_capita_payout=g.per_capita_payout,
            ))
        rows.sort(key=lambda r: r["firm_size"])
        return dict(rows=rows)

page_sequence = [Decision, ResultsWaitPage, Results, Relay]
