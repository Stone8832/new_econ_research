from otree.api import *
import json


doc = """
T3/T4: Endogenous firms (live formation) + constant/increasing returns.
"""


class C(BaseConstants):
    NAME_IN_URL = 'pg_endogenous'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 30

    ENDOWMENT = 8
    FORMATION_SECONDS = 120
    DECISION_SECONDS = 60
    INFO_SECONDS = 30

    MAX_FIRM_SIZE = 6

    # Table 2 MPCR (constant returns), indexed by firm size n
    MPCR_BY_SIZE = {2: 0.65, 3: 0.55, 4: 0.49, 5: 0.45, 6: 0.42}


class Subsession(BaseSubsession):
    formation_state = models.LongStringField(initial='')
    formation_finalized = models.BooleanField(initial=False)


class Group(BaseGroup):
    total_effort = models.IntegerField(initial=0)
    firm_size = models.IntegerField(initial=0)
    per_capita_effort = models.FloatField(initial=0)
    per_capita_payout = models.FloatField(initial=0)


class Player(BasePlayer):
    # set after formation
    firm_owner_id = models.IntegerField(initial=0)  # 0 => autarky
    is_autarkic = models.BooleanField(initial=True)

    # decision
    effort_to_firm = models.IntegerField(min=0, max=C.ENDOWMENT, initial=0)


# ---------------------------
# Formation state (JSON)
# ---------------------------

def _initial_state(n_players: int):
    owners = [str(i) for i in range(1, n_players + 1)]
    return dict(
        pending={o: [] for o in owners},      # owner -> [applicant ids]
        accepted={o: [] for o in owners},     # owner -> [employee ids]
        employer={str(i): None for i in range(1, n_players + 1)},  # person -> owner id (or None)
        rejections=[],
    )


def _get_state(subsession: Subsession):
    if not subsession.formation_state:
        state = _initial_state(len(subsession.get_players()))
        subsession.formation_state = json.dumps(state)
        return state
    return json.loads(subsession.formation_state)


def _set_state(subsession: Subsession, state):
    subsession.formation_state = json.dumps(state)


def _remove_from_all_pending(state, applicant_id: int):
    for owner_s, apps in state['pending'].items():
        if applicant_id in apps:
            apps.remove(applicant_id)


def _auto_reject_incoming_if_owner_becomes_inactive(state, owner_id: int):
    owner_s = str(owner_id)
    incoming = list(state['pending'][owner_s])
    if incoming:
        for a in incoming:
            state['rejections'].append(dict(applicant=a, owner=owner_id, reason='owner_became_inactive'))
        state['pending'][owner_s] = []


def _build_payload(subsession: Subsession, state):
    n = len(subsession.get_players())

    outgoing = {str(i): [] for i in range(1, n + 1)}
    for owner_s, apps in state['pending'].items():
        for a in apps:
            outgoing[str(a)].append(int(owner_s))

    firms = []
    for owner in range(1, n + 1):
        owner_s = str(owner)
        active = state['employer'][owner_s] is None
        employees = state['accepted'][owner_s]
        pending = state['pending'][owner_s]
        slots_left = C.MAX_FIRM_SIZE - (1 + len(employees))  # owner counts as 1
        firms.append(dict(
            owner=owner,
            active=active,
            members=[owner] + employees,
            pending=pending,
            slots_left=slots_left,
        ))

    return dict(firms=firms, employer=state['employer'], outgoing=outgoing)


# ---------------------------
# Session setup
# ---------------------------

def creating_session(subsession: Subsession):
    players = subsession.get_players()

    # real sessions: must be 18; test sessions can be smaller
    test_mode = subsession.session.config.get('test_mode', False)
    if (not test_mode) and len(players) != 18:
        raise Exception(f"T3/T4 require exactly 18 participants; currently {len(players)}")

    # one big group during formation
    subsession.set_group_matrix([players])

    subsession.formation_state = json.dumps(_initial_state(len(players)))
    subsession.formation_finalized = False


# ---------------------------
# Live formation
# ---------------------------

def live_formation(player: Player, data):
    subsession = player.subsession
    state = _get_state(subsession)
    n = len(subsession.get_players())

    pid = player.id_in_subsession
    msg_type = data.get('type')

    def deny(msg):
        return {player.id_in_group: dict(alert=msg), 0: dict(state=_build_payload(subsession, state))}

    if msg_type == 'ping':
        return {player.id_in_group: dict(state=_build_payload(subsession, state))}

    employer = state['employer']
    pending = state['pending']
    accepted = state['accepted']

    if msg_type == 'apply':
        owner = int(data.get('owner', 0))
        if owner <= 0 or owner > n:
            return deny("Invalid firm.")
        if owner == pid:
            return deny("You cannot apply to your own firm.")
        if employer[str(pid)] is not None:
            return deny("You are already employed; acceptance is binding.")
        if len(accepted[str(pid)]) > 0:
            return deny("You have hired someone, so you can no longer apply elsewhere.")
        if employer[str(owner)] is not None:
            return deny("That firm is inactive (owner is employed elsewhere).")
        if 1 + len(accepted[str(owner)]) >= C.MAX_FIRM_SIZE:
            return deny("That firm is full.")
        if pid in pending[str(owner)]:
            return deny("You already applied to that firm.")
        pending[str(owner)].append(pid)

    elif msg_type == 'withdraw':
        owner = int(data.get('owner', 0))
        if owner <= 0 or owner > n:
            return deny("Invalid firm.")
        if employer[str(pid)] is not None:
            return deny("You cannot withdraw after being accepted.")
        if pid not in pending[str(owner)]:
            return deny("No pending application to withdraw.")
        pending[str(owner)].remove(pid)

    elif msg_type == 'accept':
        owner = int(data.get('owner', 0))
        applicant = int(data.get('applicant', 0))
        if owner != pid:
            return deny("Only the firm owner can accept applicants to this firm.")
        if employer[str(owner)] is not None:
            return deny("Your firm is inactive because you are employed elsewhere.")
        if applicant not in pending[str(owner)]:
            return deny("That application is not pending.")
        if employer[str(applicant)] is not None:
            return deny("Applicant is already employed elsewhere.")
        if len(accepted[str(applicant)]) > 0:
            return deny("Applicant cannot join because they already hired someone.")
        if 1 + len(accepted[str(owner)]) >= C.MAX_FIRM_SIZE:
            return deny("Your firm is full.")

        pending[str(owner)].remove(applicant)
        accepted[str(owner)].append(applicant)
        employer[str(applicant)] = owner

        # binding acceptance cancels other applications
        _remove_from_all_pending(state, applicant)
        # owner becomes bound; cancel owner applications
        _remove_from_all_pending(state, owner)
        # applicant’s own firm becomes inactive; reject incoming apps
        _auto_reject_incoming_if_owner_becomes_inactive(state, applicant)

    elif msg_type == 'reject':
        owner = int(data.get('owner', 0))
        applicant = int(data.get('applicant', 0))
        if owner != pid:
            return deny("Only the firm owner can reject applicants to this firm.")
        if applicant not in pending[str(owner)]:
            return deny("That application is not pending.")
        pending[str(owner)].remove(applicant)
        state['rejections'].append(dict(applicant=applicant, owner=owner, reason='rejected'))

    else:
        return deny("Unknown action.")

    _set_state(subsession, state)
    return {0: dict(state=_build_payload(subsession, state))}


# ---------------------------
# Finalize + regroup
# ---------------------------

def finalize_formation(group: Group):
    subsession = group.subsession
    state = _get_state(subsession)
    n = len(subsession.get_players())

    # auto-reject remaining pending apps
    for owner_s, apps in state['pending'].items():
        owner = int(owner_s)
        for a in list(apps):
            state['rejections'].append(dict(applicant=a, owner=owner, reason='auto_end'))
        state['pending'][owner_s] = []

    players_by_id = {p.id_in_subsession: p for p in subsession.get_players()}

    for p in subsession.get_players():
        p.is_autarkic = True
        p.firm_owner_id = 0

    matrix = []
    assigned = set()

    # operating firms are those whose owner is not employed elsewhere
    for owner in range(1, n + 1):
        if state['employer'][str(owner)] is not None:
            continue
        employees = state['accepted'][str(owner)]
        if employees:
            member_ids = [owner] + employees
            matrix.append([players_by_id[i] for i in member_ids])
            for i in member_ids:
                assigned.add(i)
                players_by_id[i].is_autarkic = False
                players_by_id[i].firm_owner_id = owner

    # everyone else autarky singleton
    for pid, p in players_by_id.items():
        if pid not in assigned:
            matrix.append([p])
            p.is_autarkic = True
            p.firm_owner_id = 0

    subsession.set_group_matrix(matrix)
    _set_state(subsession, state)


# ---------------------------
# Payoffs
# ---------------------------

def set_payoffs(group: Group):
    players = group.get_players()
    n = len(players)
    group.firm_size = n

    # autarky
    if n == 1:
        group.total_effort = 0
        group.per_capita_effort = 0
        group.per_capita_payout = 0
        p = players[0]
        p.payoff = C.ENDOWMENT
        return

    total_effort = sum(p.effort_to_firm for p in players)
    group.total_effort = total_effort
    group.per_capita_effort = total_effort / n

    returns_type = group.session.config.get('returns_type', 'constant')

    if returns_type == 'constant':
        alpha = C.MPCR_BY_SIZE[n]
        group.per_capita_payout = alpha * total_effort

    elif returns_type == 'increasing':
        a = float(group.session.config.get('a', 0.2496))
        b = float(group.session.config.get('b', 1.5952))
        output = a * (total_effort ** b) if total_effort > 0 else 0.0
        group.per_capita_payout = output / n

    else:
        raise Exception(f"Unknown returns_type: {returns_type}")

    for p in players:
        p.payoff = (C.ENDOWMENT - p.effort_to_firm) + group.per_capita_payout


# ---------------------------
# Pages
# ---------------------------

class Formation(Page):
    live_method = live_formation

    @staticmethod
    def get_timeout_seconds(player: Player):
        # let you shorten in test sessions
        return player.session.config.get('formation_seconds', C.FORMATION_SECONDS)

    @staticmethod
    def js_vars(player: Player):
        return dict(my_id=player.id_in_subsession, max_size=C.MAX_FIRM_SIZE)

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        # In test_mode, skip the WaitPage and finalize here (once).
        if not player.session.config.get('test_mode', False):
            return
        subsession = player.subsession
        if not subsession.formation_finalized:
            subsession.formation_finalized = True
            finalize_formation(player.group)


class FormationWaitPage(WaitPage):
    after_all_players_arrive = finalize_formation

    @staticmethod
    def is_displayed(player: Player):
        return not player.session.config.get('test_mode', False)


class FirmAssignment(Page):
    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            is_autarkic=(len(player.group.get_players()) == 1),
            firm_owner_id=player.firm_owner_id,
            members=[p.id_in_subsession for p in player.group.get_players()],
        )


class Decision(Page):
    timeout_seconds = C.DECISION_SECONDS
    form_model = 'player'
    form_fields = ['effort_to_firm']
    timeout_submission = dict(effort_to_firm=0)

    @staticmethod
    def is_displayed(player: Player):
        return len(player.group.get_players()) > 1


class ResultsWaitPage(WaitPage):
    after_all_players_arrive = set_payoffs


class Results(Page):
    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            is_autarkic=(len(player.group.get_players()) == 1),
            firm_size=len(player.group.get_players()),
            members=[p.id_in_subsession for p in player.group.get_players()],
        )


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
        rows.sort(key=lambda r: r['firm_size'])
        return dict(rows=rows)


page_sequence = [
    Formation,
    FormationWaitPage,
    FirmAssignment,
    Decision,
    ResultsWaitPage,
    Results,
    Relay,
]
