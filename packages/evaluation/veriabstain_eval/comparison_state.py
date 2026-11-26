"""SQLite state for offline experiments only; not the production recovery journal."""

import sqlite3
from pathlib import Path

from .dataset import canonical
from .workers import digest, strict_json


class ComparisonState:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=10)
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS scopes (
                operation TEXT PRIMARY KEY, context_digest TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS requests (
                request_id TEXT PRIMARY KEY, operation TEXT NOT NULL REFERENCES scopes(operation),
                round_number INTEGER NOT NULL CHECK(round_number IN (0,1)),
                request_digest TEXT NOT NULL, payload TEXT NOT NULL,
                response TEXT, response_digest TEXT,
                UNIQUE(operation, round_number)
            );
        """)

    @staticmethod
    def _envelope_payload(envelope):
        if (not isinstance(envelope, dict)
                or set(envelope) != {"request_id", "request_digest", "request"}
                or not isinstance(envelope["request_id"], str)
                or not envelope["request_id"]
                or not isinstance(envelope["request_digest"], str)
                or not isinstance(envelope["request"], dict)):
            raise ValueError("Invalid comparison request envelope")
        if digest(envelope["request"]) != envelope["request_digest"]:
            raise ValueError("Comparison request body digest mismatch")
        return canonical(envelope)

    def _request(self, request_id):
        return self.db.execute(
            "SELECT operation,round_number,request_digest,payload,response,response_digest "
            "FROM requests WHERE request_id=?", (request_id,),
        ).fetchone()

    @classmethod
    def _checked_response(cls, request_id, row):
        """Detect malformed or inconsistent local records before resuming them.

        These hashes detect inconsistency; they do not authenticate a database
        against an attacker able to rewrite both content and its digest.
        """
        try:
            saved = strict_json(row[3])
            payload = cls._envelope_payload(saved)
        except (TypeError, ValueError) as error:
            raise ValueError("Corrupt stored request envelope") from error
        if (payload != row[3] or saved["request_id"] != request_id
                or saved["request_digest"] != row[2]):
            raise ValueError("Stored request integrity mismatch")
        response, response_digest = row[4], row[5]
        if response is None:
            if response_digest is not None:
                raise ValueError("Corrupt stored response digest")
        elif not isinstance(response, str) or digest(response) != response_digest:
            raise ValueError("Stored response digest mismatch")
        return response

    def prepare(self, operation, context, round_number, envelope):
        if not isinstance(operation, str) or not operation:
            raise ValueError("Invalid experiment operation")
        if type(round_number) is not int or round_number not in (0, 1):
            raise ValueError("Invalid comparison round")
        payload = self._envelope_payload(envelope)
        context_digest = digest(context)
        with self.db:
            # Reserve the write lock before checking slots. Separate connections
            # cannot both pass checks and silently share another operation's ID.
            self.db.execute("BEGIN IMMEDIATE")
            self.db.execute("INSERT OR IGNORE INTO scopes VALUES (?,?)", (operation, context_digest))
            saved = self.db.execute("SELECT context_digest FROM scopes WHERE operation=?", (operation,)).fetchone()
            if saved[0] != context_digest:
                raise ValueError("Original experiment context changed")
            slot = self.db.execute(
                "SELECT request_id FROM requests WHERE operation=? AND round_number=?",
                (operation, round_number),
            ).fetchone()
            if slot and slot[0] != envelope["request_id"]:
                raise ValueError("Existing comparison request changed")
            existing = self._request(envelope["request_id"])
            response = None
            if existing:
                response = self._checked_response(envelope["request_id"], existing)
                if existing[0] != operation or existing[1] != round_number:
                    raise ValueError("Comparison request ID already bound to another operation or round")
                if existing[2] != envelope["request_digest"] or existing[3] != payload:
                    raise ValueError("Existing comparison request changed")
            if round_number == 1:
                previous_id = self.db.execute(
                    "SELECT request_id FROM requests WHERE operation=? AND round_number=0", (operation,),
                ).fetchone()
                if previous_id is None:
                    raise ValueError("Retry requires an observed first decision")
                previous = self._request(previous_id[0])
                if self._checked_response(previous_id[0], previous) is None:
                    raise ValueError("Retry requires an observed first decision")
            if existing is None:
                self.db.execute(
                    "INSERT INTO requests(request_id,operation,round_number,request_digest,payload) VALUES (?,?,?,?,?)",
                    (envelope["request_id"], operation, round_number, envelope["request_digest"], payload),
                )
        return response

    def record(self, envelope, response):
        payload = self._envelope_payload(envelope)
        if not isinstance(response, str):
            raise ValueError("Comparison response must be a string")
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            row = self._request(envelope["request_id"])
            if row is None:
                raise ValueError("Conflicting or unprepared response")
            existing_response = self._checked_response(envelope["request_id"], row)
            if row[2] != envelope["request_digest"] or row[3] != payload:
                raise ValueError("Response request does not match the prepared request")
            if existing_response is not None:
                if existing_response != response:
                    raise ValueError("Conflicting or unprepared response")
                return
            self.db.execute(
                "UPDATE requests SET response=?,response_digest=? WHERE request_id=?",
                (response, digest(response), envelope["request_id"]),
            )

    def close(self):
        self.db.close()
