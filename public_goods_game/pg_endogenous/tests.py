from otree.api import Bot, Submission
import random
from . import C, Formation, FirmAssignment, Decision, Results, Relay


class PlayerBot(Bot):
    def play_round(self):

        # Formation is a live page with no submit button, so disable HTML check.
        yield Submission(Formation, timeout_happened=True, check_html=False)

        # FirmAssignment needs a Next button in its HTML (see note below).
        yield FirmAssignment

        # Decision only appears if group size > 1 (autarky skips it)
        if len(self.player.group.get_players()) > 1:
            yield Decision, dict(effort_to_firm=random.randint(0, C.ENDOWMENT))

        yield Results

        # Relay usually has no Next button (timeout page), so disable HTML check.
        yield Submission(Relay, timeout_happened=True, check_html=False)
