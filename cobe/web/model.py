# Copyright (C) 2012 Peter Teichman

import datetime

from flask import g

class Exchange(object):
    @staticmethod
    def get_recent_unrated(user):
        # select recent exchanges this user hasn't already voted on
        q = "SELECT exchanges.id, input, output, exchanges.time, hash " \
            "FROM exchanges LEFT JOIN votes " \
            "ON votes.log_id = exchanges.id AND votes.voter_id = ? " \
            "WHERE votes.voter_id IS NULL GROUP BY exchanges.id " \
            "ORDER BY exchanges.time DESC LIMIT 30"

        return g.db.execute(q, (user["id"],))


class Vote(object):
    @staticmethod
    def vote(user, hash, vote):
        vote = cmp(vote, 0)

        q = "UPDATE votes SET vote = ? " \
            "WHERE log_id = (SELECT id FROM exchanges WHERE hash = ?)"

        c = g.db.cursor()
        c.execute(q, (vote, hash))

        if c.rowcount == 0:
            q = "INSERT INTO votes (voter_id, log_id, vote, time) VALUES " \
                "(?, (SELECT id FROM exchanges WHERE hash = ?), ?, ?)"
            c.execute(q, (user["id"], hash, vote, datetime.datetime.utcnow()))

        g.db.commit()
