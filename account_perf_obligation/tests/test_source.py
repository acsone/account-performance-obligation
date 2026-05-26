# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from unittest.mock import patch

from odoo_test_helper import FakeModelLoader

from .common import PerfObligationCommon


class TestPerfObligationSourceMixin(PerfObligationCommon):
    def setUp(self):
        super().setUp()
        self.loader = FakeModelLoader(self.env, self.__module__)
        self.loader.backup_registry()
        from .source_test import PerfObligationTestSource

        self.loader.update_registry((PerfObligationTestSource,))
        self.Source = self.env["perf.obligation.test.source"]

    def _make_source(self, obligation, amount):
        return self.Source.create(
            {
                "perf_obligation_id": obligation.id,
                "amount": amount,
            }
        )

    def tearDown(self):
        self.loader.restore_registry()
        super().tearDown()

    def test_get_source_models_includes_test_source(self):
        """The mixin discovery must find our concrete test source model."""
        obligation = self._create_obligation()
        model_names = [m._name for m in obligation._get_source_models()]
        self.assertIn("perf.obligation.test.source", model_names)

    def test_get_source_models_excludes_abstract(self):
        """The mixin itself (abstract) must not appear in discovered models."""
        obligation = self._create_obligation()
        model_names = [m._name for m in obligation._get_source_models()]
        self.assertNotIn("perf.obligation.source.mixin", model_names)

    def test_get_sources_empty_when_no_source_linked(self):
        obligation = self._create_obligation(total_amount=500.0)
        self.assertEqual(obligation._get_sources(), [])

    def test_get_sources_returns_linked_records(self):
        obligation = self._create_obligation(total_amount=500.0)
        src = self._make_source(obligation, 500.0)
        sources = obligation._get_sources()
        all_records = self.Source.browse()
        for recordset in sources:
            all_records |= recordset
        self.assertIn(src, all_records)

    def test_get_sources_does_not_return_unlinked_records(self):
        obligation = self._create_obligation(total_amount=500.0)
        other_obligation = self._create_obligation(total_amount=200.0)
        self._make_source(other_obligation, 200.0)
        sources = obligation._get_sources()
        all_records = self.Source.browse()
        for recordset in sources:
            all_records |= recordset
        self.assertFalse(all_records)

    def test_compute_total_amount_single_source(self):
        obligation = self._create_obligation(total_amount=0.0)
        self._make_source(obligation, 800.0)
        self.assertEqual(obligation._compute_total_amount_from_sources(), 800.0)

    def test_compute_total_amount_multiple_sources(self):
        """Multiple sources pointing to the same obligation are summed."""
        obligation = self._create_obligation(total_amount=0.0)
        self._make_source(obligation, 400.0)
        self._make_source(obligation, 600.0)
        self.assertEqual(obligation._compute_total_amount_from_sources(), 1000.0)

    def test_compute_total_amount_zero_when_no_sources(self):
        obligation = self._create_obligation(total_amount=500.0)
        self.assertEqual(obligation._compute_total_amount_from_sources(), 0.0)

    def test_update_amount_writes_total_amount(self):
        obligation = self._create_obligation(total_amount=0.0)
        self._make_source(obligation, 1200.0)
        obligation._update_amount_from_sources()
        self.assertEqual(obligation.total_amount, 1200.0)

    def test_update_amount_sums_multiple_sources(self):
        obligation = self._create_obligation(total_amount=0.0)
        self._make_source(obligation, 300.0)
        self._make_source(obligation, 700.0)
        obligation._update_amount_from_sources()
        self.assertEqual(obligation.total_amount, 1000.0)

    def test_update_amount_no_write_when_unchanged(self):
        """No write should occur when the computed amount equals current total."""
        obligation = self._create_obligation(total_amount=500.0)
        self._make_source(obligation, 500.0)
        with patch.object(
            type(obligation), "write", wraps=obligation.write
        ) as mock_write:
            obligation._update_amount_from_sources()
            # write may be called for other reasons (e.g. tracking),
            # but total_amount must not be in the written vals
            for call in mock_write.call_args_list:
                self.assertNotIn("total_amount", call.args[0])

    def test_update_amount_noop_when_no_sources(self):
        """Manually managed obligation (no sources) must not be touched."""
        obligation = self._create_obligation(total_amount=999.0)
        obligation._update_amount_from_sources()
        self.assertEqual(obligation.total_amount, 999.0)

    def test_update_amount_posts_chatter_message(self):
        obligation = self._create_obligation(total_amount=0.0)
        self._make_source(obligation, 500.0)
        msg_count_before = len(obligation.message_ids)
        obligation._update_amount_from_sources()
        self.assertGreater(len(obligation.message_ids), msg_count_before)

    def test_update_amount_no_chatter_message_when_unchanged(self):
        obligation = self._create_obligation(total_amount=500.0)
        self._make_source(obligation, 500.0)
        msg_count_before = len(obligation.message_ids)
        obligation._update_amount_from_sources()
        self.assertEqual(len(obligation.message_ids), msg_count_before)

    def test_update_amount_with_reason_in_chatter(self):
        obligation = self._create_obligation(total_amount=0.0)
        self._make_source(obligation, 300.0)
        obligation._update_amount_from_sources(reason="Cancelled source")
        self.assertIn("Cancelled source", obligation.message_ids[0].body)

    def test_notify_triggers_update(self):
        obligation = self._create_obligation(total_amount=0.0)
        src = self._make_source(obligation, 750.0)
        src._notify_obligation_amount_changed()
        self.assertEqual(obligation.total_amount, 750.0)

    def test_notify_noop_when_no_obligation(self):
        """Source without an obligation must not raise."""
        src = self.Source.create({"amount": 100.0})
        src._notify_obligation_amount_changed()  # must not raise

    def test_notify_updates_all_obligations_in_recordset(self):
        """Calling _notify on a multi-record recordset updates all obligations."""
        ob1 = self._create_obligation(total_amount=0.0)
        ob2 = self._create_obligation(total_amount=0.0)
        src1 = self._make_source(ob1, 100.0)
        src2 = self._make_source(ob2, 200.0)
        (src1 | src2)._notify_obligation_amount_changed()
        self.assertEqual(ob1.total_amount, 100.0)
        self.assertEqual(ob2.total_amount, 200.0)
