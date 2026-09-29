# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.exceptions import ValidationError

from .common import PerfObligationCommon


class TestPerfObligationPartner(PerfObligationCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.child_contact = cls.env["res.partner"].create(
            {"name": "Test Partner Contact", "parent_id": cls.partner.id}
        )

    def test_parent_partner_accepted(self):
        po = self._create_obligation()
        po.partner_id = self.partner
        self.assertEqual(po.partner_id, self.partner)

    def test_child_contact_rejected(self):
        po = self._create_obligation()
        with self.assertRaisesRegex(ValidationError, r"must be a parent contact"):
            po.partner_id = self.child_contact

    def test_child_company_rejected(self):
        """A company is still rejected when it is a child of another contact,
        even though it is its own commercial partner."""
        child_company = self.env["res.partner"].create(
            {
                "name": "Test Child Company",
                "parent_id": self.partner.id,
                "is_company": True,
            }
        )
        self.assertEqual(child_company.commercial_partner_id, child_company)
        po = self._create_obligation()
        with self.assertRaisesRegex(ValidationError, r"must be a parent contact"):
            po.partner_id = child_company

    def test_partner_set_on_all_recognition_lines(self):
        po = self._create_obligation(perf_type="income", total_amount=300.0)
        po.partner_id = self.partner
        move = po._recognize(100, "2026-01-31", "Jan")
        self.assertEqual(len(move.line_ids), 2)
        self.assertEqual(move.line_ids.partner_id, self.partner)

    def test_no_partner_on_recognition_lines_when_unset(self):
        po = self._create_obligation(perf_type="income", total_amount=300.0)
        move = po._recognize(100, "2026-01-31", "Jan")
        self.assertFalse(move.line_ids.partner_id)
