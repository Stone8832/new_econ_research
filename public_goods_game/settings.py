from os import environ
import math


SESSION_CONFIGS = [
    dict(
        name='T1_exogenous_constant',
        display_name="T1: Exogenous + Constant returns",
        app_sequence=['pg_exogenous'],
        num_demo_participants=20,
        returns_type='constant'
    ),
    dict(
        name='T1_test_small',
        display_name="T1 TEST (small N)",
        app_sequence=['pg_exogenous'],
        num_demo_participants=6,
        returns_type='constant',
        test_mode=True,
    ),
    dict(
        name='T3_bots_small',
        display_name="T3 bots small",
        app_sequence=['pg_endogenous'],
        num_demo_participants=3,
        returns_type='constant',
        test_mode=True,
        formation_seconds=120,
        info_seconds=120,
    ),

    dict(
        name='T2_exogenous_increasing',
        display_name="T2: Exogenous + Increasing returns",
        app_sequence=['pg_exogenous'],
        num_demo_participants=20,
        returns_type='increasing',
        a = 20.8 / (16 ** (math.log(120/20.8) / math.log(3))),
        b = math.log(120/20.8) / math.log(3)
    ),
    dict(
        name='T3_endogenous_constant',
        display_name="T3: Endogenous + Constant returns",
        app_sequence=['pg_endogenous'],
        num_demo_participants=18,
        returns_type='constant',
    ),
    dict(
        name='T4_endogenous_increasing',
        display_name="T4: Endogenous + Increasing returns",
        app_sequence=['pg_endogenous'],
        num_demo_participants=18,
        returns_type='increasing',
        a=20.8 / (16 ** (math.log(120 / 20.8) / math.log(3))),
        b=math.log(120 / 20.8) / math.log(3),
    ),

]

# if you set a property in SESSION_CONFIG_DEFAULTS, it will be inherited by all configs
# in SESSION_CONFIGS, except those that explicitly override it.
# the session config can be accessed from methods in your apps as self.session.config,
# e.g. self.session.config['participation_fee']

SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1.00, participation_fee=0.00, doc=""
)

PARTICIPANT_FIELDS = []
SESSION_FIELDS = []

# ISO-639 code
# for example: de, fr, ja, ko, zh-hans
LANGUAGE_CODE = 'en'

# e.g. EUR, GBP, CNY, JPY
REAL_WORLD_CURRENCY_CODE = 'USD'
USE_POINTS = True

ROOMS = [
    dict(
        name='econ101',
        display_name='Econ 101 class',
        participant_label_file='_rooms/econ101.txt',
    ),
    dict(name='live_demo', display_name='Room for live demo (no participant labels)'),
]

ADMIN_USERNAME = 'admin'
# for security, best to set admin password in an environment variable
ADMIN_PASSWORD = environ.get('OTREE_ADMIN_PASSWORD')

DEMO_PAGE_INTRO_HTML = """
Here are some oTree games.
"""


SECRET_KEY = '1645500718759'

INSTALLED_APPS = ['otree']
