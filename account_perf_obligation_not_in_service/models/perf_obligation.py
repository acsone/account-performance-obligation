# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PerfObligation(models.Model):
    _inherit = "perf.obligation"

    not_in_service = fields.Boolean(
        default=False,
        copy=False,
        tracking=True,
        help="Check while the service is not delivered yet. Nothing is "
        "recognized for such an obligation: when recognition entries are "
        "posted, its start date is postponed instead. Uncheck it once the "
        "service really starts.",
    )

    def _start(self):
        """Put the obligations in service (uncheck 'Not in Service').

        To be called by the modules that know when the service really starts
        (contract dates, activation event, ...). Obligations already in service
        are left untouched.
        """
        self.filtered("not_in_service").write({"not_in_service": False})

    def _get_postponed_dates(self, new_start_date):
        """Return the (start_date, end_date) of the obligation once postponed
        to *new_start_date*.

        When the start date equals the end date (one shot obligation recognized
        at once), both dates are postponed. Otherwise the end date is kept.
        """
        self.ensure_one()
        if self.start_date == self.end_date:
            return new_start_date, new_start_date
        return new_start_date, self.end_date

    def _postpone_not_in_service_obligations(self, date):
        """Obligations not in service are never recognized. When the posting date
        reaches their start date (the service did not start), the start date is
        moved to the first day of the month following the posting date and the
        schedule is recomputed, so the forecast stays as close as possible to
        reality. Obligations starting after *date* are ignored."""
        to_postpone = self.filtered(
            lambda po: po.state == "open"
            and po.not_in_service
            and po.start_date
            and po.start_date <= date
        )
        for po in to_postpone:
            new_start_date = date + relativedelta(months=1, day=1)
            start_date, end_date = po._get_postponed_dates(new_start_date)
            if end_date and start_date > end_date:
                raise UserError(
                    _(
                        "Cannot post recognition entries: the start date of "
                        "performance obligation %(name)s, which is not in service, "
                        "would have to be postponed to %(start)s, which is after "
                        "its end date (%(end)s). Please review its dates or put it "
                        "in service.",
                        name=po.display_name,
                        start=start_date,
                        end=end_date,
                    )
                )
            po.write({"start_date": start_date, "end_date": end_date})
            if po.schedule_needs_regeneration:
                po._regenerate_schedule()

    @api.model
    def _post_recognition_moves(self, date, obligations=None, companies=None):
        if companies is None:
            companies = obligations.company_id if obligations else self.env.companies
        not_in_service_domain = [
            ("state", "=", "open"),
            ("not_in_service", "=", True),
            ("company_id", "in", companies.ids),
        ]
        if obligations is not None:
            not_in_service_domain.append(("id", "in", obligations.ids))
        self.env["perf.obligation"].search(
            not_in_service_domain
        )._postpone_not_in_service_obligations(date)

        if obligations is None:
            in_service_obligations = self.env["perf.obligation"].search(
                [
                    ("state", "=", "open"),
                    ("not_in_service", "=", False),
                    ("company_id", "in", companies.ids),
                ]
            )
        else:
            in_service_obligations = obligations.filtered(
                lambda po: po.state == "open" and not po.not_in_service
            )
        if not in_service_obligations:
            return
        return super()._post_recognition_moves(
            date, obligations=in_service_obligations, companies=companies
        )
