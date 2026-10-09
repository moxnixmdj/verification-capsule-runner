from __future__ import annotations

import dataclasses
import unittest

import terminal_slot_start_cas_v1 as m


class MemoryStore:
    def __init__(self):
        self.rows = {}
        self.raise_create = False
        self.raise_read = False
    def create(self, key, value):
        if self.raise_create:
            raise RuntimeError("transport")
        if key in self.rows:
            return False
        self.rows[key] = value
        return True
    def read(self, key):
        if self.raise_read:
            raise RuntimeError("transport")
        return self.rows.get(key)


def intent(run="100", slot="science/x::trial-0", digest=None):
    return m.StartIntent(
        slot_id=slot,
        task_digest=digest or "sha256:" + "a"*64,
        logical_attempt_id="b"*64,
        workflow_git_blob_sha="c"*40,
        authority_git_blob_sha="d"*40,
        activation_git_blob_sha="e"*40,
        runtime_identity_sha256="f"*64,
        prestart_receipt_sha256="1"*64,
        github_run_id=run,
        github_sha="2"*40,
    )


class Tests(unittest.TestCase):
    def test_first_start_intent_wins(self):
        store=MemoryStore()
        out=m.reserve_start_once(store,intent())
        self.assertEqual(out["status"],"TASK_START_INTENT_COMMITTED")
        self.assertFalse(out["replay_authority"])
        self.assertFalse(out["replacement_carrier_authority"])

    def test_second_distinct_run_same_slot_is_rejected(self):
        store=MemoryStore()
        m.reserve_start_once(store,intent("100"))
        with self.assertRaisesRegex(m.StartAdmissionDenied,"START_ALREADY_RESERVED"):
            m.reserve_start_once(store,intent("101"))

    def test_same_run_rerun_is_also_rejected(self):
        store=MemoryStore()
        m.reserve_start_once(store,intent("100"))
        with self.assertRaisesRegex(m.StartAdmissionDenied,"NO_SECOND_START"):
            m.reserve_start_once(store,intent("100"))

    def test_authority_revision_cannot_create_second_slot_start(self):
        store=MemoryStore()
        first=intent("100")
        m.reserve_start_once(store,first)
        newer=dataclasses.replace(first,authority_git_blob_sha="9"*40,github_run_id="101")
        with self.assertRaisesRegex(m.StartAdmissionDenied,"START_ALREADY_RESERVED"):
            m.reserve_start_once(store,newer)

    def test_key_excludes_carrier_and_authority_identity(self):
        a=intent("100")
        b=dataclasses.replace(a,github_run_id="999",authority_git_blob_sha="9"*40,github_sha="8"*40)
        self.assertEqual(
            m.slot_start_key(a.slot_id,a.task_digest),
            m.slot_start_key(b.slot_id,b.task_digest),
        )

    def test_different_slot_gets_different_key(self):
        a=intent(slot="science/a::trial-0")
        b=intent(slot="science/b::trial-0")
        self.assertNotEqual(
            m.slot_start_key(a.slot_id,a.task_digest),
            m.slot_start_key(b.slot_id,b.task_digest),
        )

    def test_create_transport_uncertainty_fails_closed(self):
        store=MemoryStore(); store.raise_create=True
        with self.assertRaisesRegex(m.StartAdmissionDenied,"UNCONFIRMED__NO_START"):
            m.reserve_start_once(store,intent())

    def test_existing_ref_read_uncertainty_fails_closed(self):
        store=MemoryStore()
        m.reserve_start_once(store,intent("100"))
        store.raise_read=True
        with self.assertRaisesRegex(m.StartAdmissionDenied,"READ_UNCONFIRMED__NO_START"):
            m.reserve_start_once(store,intent("101"))

    def test_record_binds_prestart_and_runtime_identity(self):
        store=MemoryStore()
        i=intent()
        out=m.reserve_start_once(store,i)
        row=store.rows[out["key"]]
        self.assertEqual(row["prestart_receipt_sha256"],i.prestart_receipt_sha256)
        self.assertEqual(row["runtime_identity_sha256"],i.runtime_identity_sha256)
        self.assertFalse(row["replay_authority"])
        self.assertFalse(row["replacement_carrier_authority"])

    def test_invalid_digest_rejected_before_store(self):
        store=MemoryStore()
        with self.assertRaises(ValueError):
            m.reserve_start_once(store,dataclasses.replace(intent(),task_digest="bad"))
        self.assertEqual(store.rows,{})


if __name__=="__main__":
    unittest.main(verbosity=2)
