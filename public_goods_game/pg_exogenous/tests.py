import random
from otree.api import Bot, Submission, expect

from . import C, Decision, Results, Relay


class PlayerBot(Bot):
    def play_round(self):
        # submit the decision page
        yield Decision, dict(effort_to_firm=C.ENDOWMENT)

        # results page (no form, just click next)
        yield Results

        # Relay is auto-advanced by timeout and often has no Next button,
        # so we simulate a timeout submission and disable HTML checking.
        yield Submission(Relay, timeout_happened=True, check_html=False)

        # quick sanity checks on the paper constraint:
        size_by_block = self.participant.vars.get("size_by_block", {})
        block_starts = [1, 11, 21]

        sizes_so_far = [size_by_block[b] for b in block_starts if b in size_by_block and b <= self.round_number]

        expect(len(set(sizes_so_far)), len(sizes_so_far))  # no repeats among blocks so far

        if self.round_number <= 10:
            expect(len(sizes_so_far), 1)
        elif self.round_number <= 20:
            expect(len(sizes_so_far), 2)
        else:
            expect(len(sizes_so_far), 3)
