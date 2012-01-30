# Copyright (C) 2012 Peter Teichman

from flask import g

class Exchange(object):
    @staticmethod
    def get_recent_unrated(user):
        # select recent exchanges this user hasn't already voted on
        q = "SELECT exchanges.id, input, output, exchanges.time, hash " \
            "FROM exchanges LEFT JOIN votes " \
            "ON votes.log_id = exchanges.id AND votes.voter_id = ? " \
            "WHERE votes.voter_id IS NULL GROUP BY exchanges.id " \
            "LIMIT 30"

        return g.db.execute(q, (user["id"],))
