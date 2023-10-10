from odoo import fields, models, api, _
from datetime import timedelta, date
from odoo.exceptions import Warning

class ProjectProject(models.Model):
    _inherit = "project.project"

    #@api.multi Not needed in v16.0
    def create_invoice_line(self, invoice):
        project_task_obj = self.env['project.task']
        sale_order_obj = self.env['sale.order'].search([('analytic_account_id', '=', self.analytic_account_id.id)], limit=1)
        array = []
        today = date.today()
        idx = (today.weekday() + 1) % 7
        this_sunday = today - timedelta(days=idx)
        inv_start_date = self.env.user.company_id.inv_start_date

        if sale_order_obj.analytic_account_id.section_ids:
            for section in sale_order_obj.analytic_account_id.section_ids:
                okr = section.task_id
                task_ids = project_task_obj.search([
                    ('parent_task_id', 'child_of', okr.id),
                    ('active', '=', True)
                ], order='id asc')
                self._cr.execute('''
                    SELECT
                        distinct(user_id),
                        sum(unit_amount), id
                    FROM
                        account_analytic_line
                    WHERE
                        account_id = %s
                        AND invoiceable_analytic_line = 't'
                        AND date >= %s
                        AND date <= %s
                        AND project_id is not null
                        AND task_id in %s
                        AND project_invoice_line_id is null
                    GROUP BY
                        user_id, id
                    ORDER BY user_id asc
                    ''', (sale_order_obj.analytic_account_id.id, inv_start_date, this_sunday, tuple(task_ids.ids)))
                task_order_obj = self._cr.fetchall()
                array.append(task_order_obj)

                if len(array) > 0:
                    for euser in array:
                        emp_obj = self.env['hr.employee'].search([('user_id', '=', euser[0][0])])
                        temp_time = euser[0][1]

                        if not emp_obj:
                            employee_data = self.action_search_employee(euser[0][0])

                            if not employee_data['inhouse']:
                                raise Warning(_('Please fill field Inhouse Product ' + employee_data['position'] + ' in Job Position'))

                            if not employee_data['outsource']:
                                raise Warning(_('Please fill field Outsource Product ' + employee_data['position'] + ' in Job Position'))

                            if employee_data['company_id'] == self.env.user.company_id.id:
                                product_id = employee_data['inhouse']
                            else:
                                product_id = employee_data['outsource']

                            if sale_order_obj.pricelist_id and sale_order_obj.partner_id:
                                product = self.env['product.product'].search(
                                    [('id', '=', employee_data['product_id'])])
                                vals = self.env['account.tax']._fix_tax_included_price(
                                    product.price, product.taxes_id, so_line_obj.tax_id)
                            else:
                                vals = employee_data['list_price']

                            self.env['account.invoice.line'].create({
                                'layout_category_id': section.id,
                                'employee_id': employee_data['employee_id'],
                                'product_id': product_id.id,
                                'name': employee_data['product_name'] + ': ' + employee_data[
                                        'employee'],
                                'quantity': temp_time,
                                'price_unit': vals,
                                'invoice_id': invoice.id,
                                'account_id': product_id.property_account_income_id.id,
                                'uom_id': employee_data['uom_id'],
                                'l10n_mx_edi_sat_status': 'none',
                                'account_analytic_id': sale_order_obj.analytic_account_id.id,
                            })

                        else:
                            if not emp_obj.job_id.product_inhouse_id:
                                raise Warning(_('Please fill field Inhouse Product ' + emp_obj.job_id.name + ' in Job Position'))

                            if not emp_obj.job_id.product_outsource_id:
                                raise Warning(_('Please fill field Outsource Product ' + emp_obj.job_id.name + ' in Job Position'))

                            if emp_obj['company_id'].id == self.env.user.company_id.id:
                                product_id = emp_obj.job_id.product_inhouse_id
                            else:
                                product_id = emp_obj.job_id.product_outsource_id

                            so_line_obj = self.env['sale.order.line']
                            if sale_order_obj.pricelist_id and sale_order_obj.partner_id:
                                product = emp_obj.job_id.product_id.with_context(
                                    lang=sale_order_obj.partner_id.lang,
                                    partner=sale_order_obj.partner_id.id,
                                    quantity=1,
                                    date=sale_order_obj.date_order,
                                    pricelist=sale_order_obj.pricelist_id.id,
                                    uom=emp_obj.job_id.product_id.uom_id.id
                                )
                                vals = self.env['account.tax']._fix_tax_included_price(
                                    product.price, product.taxes_id, so_line_obj.tax_id)
                            else:
                                vals = emp_obj.job_id.product_id.list_price

                            self.env['account.invoice.line'].create({
                                'layout_category_id': section.id,
                                'employee_id': emp_obj.id,
                                'product_id': product_id.id,
                                'name': product_id.name + ': ' + emp_obj.name,
                                'quantity': temp_time,
                                'price_unit': vals,
                                'invoice_id': invoice.id,
                                'account_id': product_id.property_account_income_id.id,
                                'uom_id': emp_obj.job_id.product_id.uom_id.id,
                                'l10n_mx_edi_sat_status': 'none',
                                'account_analytic_id': sale_order_obj.analytic_account_id.id,
                            })
        else:
            self._cr.execute('''
                SELECT
                    distinct(user_id),
                    sum(unit_amount)
                FROM
                    account_analytic_line
                WHERE
                    account_id = %s
                    AND invoiceable_analytic_line = 't'
                    AND date >= %s
                    AND date <= %s
                    AND project_id is not null
                    AND project_invoice_line_id is null
                GROUP BY
                    user_id
                ''', (sale_order_obj.analytic_account_id.id, inv_start_date, this_sunday,))
            task_order_obj = self._cr.fetchall()
            array.append(task_order_obj)

            if len(array) > 0:
                for euser in array:
                    emp_obj = self.env['hr.employee'].search([('user_id', '=', euser[0][0])])
                    temp_time = euser[0][1]

                    if not emp_obj:
                        employee_data = self.action_search_employee(euser[0][0])

                        if not employee_data['inhouse']:
                            raise Warning(_('Please fill field Inhouse Product ' + employee_data['position'] + ' in Job Position'))

                        if not employee_data['outsource']:
                            raise Warning(_('Please fill field Outsource Product ' + employee_data['position'] + ' in Job Position'))

                        if employee_data['company_id'] == self.env.user.company_id.id:
                            product_id = employee_data['inhouse']
                        else:
                            product_id = employee_data['outsource']

                        if sale_order_obj.pricelist_id and sale_order_obj.partner_id:
                            product = self.env['product.product'].search(
                                [('id', '=', employee_data['product_id'])])
                            vals = self.env['account.tax']._fix_tax_included_price(
                                    product.price, product.taxes_id, so_line_obj.tax_id)
                        else:
                            vals = employee_data['list_price']

                        self.env['account.invoice.line'].create({
                            'employee_id': employee_data['employee_id'],
                            'product_id': product_id.id,
                            'name': employee_data['product_name'] + ': ' + employee_data[
                                    'employee'],
                            'quantity': temp_time,
                            'price_unit': vals,
                            'invoice_id': invoice.id,
                            'account_id': product_id.property_account_income_id.id,
                            'uom_id': employee_data['uom_id'],
                            'l10n_mx_edi_sat_status': 'none',
                            'account_analytic_id': sale_order_obj.analytic_account_id.id,
                        })
                    else:
                        if not emp_obj.job_id.product_inhouse_id:
                            raise Warning(_('Please fill field Inhouse Product ' + emp_obj.job_id.name + ' in Job Position'))

                        if not emp_obj.job_id.product_outsource_id:
                            raise Warning(_('Please fill field Outsource Product ' + emp_obj.job_id.name + ' in Job Position'))

                        if emp_obj['company_id'].id == self.env.user.company_id.id:
                            product_id = emp_obj.job_id.product_inhouse_id
                        else:
                            product_id = emp_obj.job_id.product_outsource_id

                        so_line_obj = self.env['sale.order.line']
                        if sale_order_obj.pricelist_id and sale_order_obj.partner_id:
                            product = emp_obj.job_id.product_id.with_context(
                                lang=sale_order_obj.partner_id.lang,
                                partner=sale_order_obj.partner_id.id,
                                quantity=1,
                                date=sale_order_obj.date_order,
                                pricelist=sale_order_obj.pricelist_id.id,
                                uom=emp_obj.job_id.product_id.uom_id.id
                            )
                            vals = self.env['account.tax']._fix_tax_included_price(
                                    product.price, product.taxes_id, so_line_obj.tax_id)
                        else:
                            vals = emp_obj.job_id.product_id.list_price

                        self.env['account.invoice.line'].create({
                            'employee_id': emp_obj.id,
                            'product_id': product_id.id,
                            'name': product_id.name + ': ' + emp_obj.name,
                            'quantity': temp_time,
                            'price_unit': vals,
                            'invoice_id': invoice.id,
                            'account_id': product_id.property_account_income_id.id,
                            'uom_id': emp_obj.job_id.product_id.uom_id.id,
                            'l10n_mx_edi_sat_status': 'none',
                            'account_analytic_id': sale_order_obj.analytic_account_id.id,
                        })
        timesheets = self.check_timesheet_on_project()
        for timesheet in timesheets:
            self.env['account.analytic.line'].search([('id', '=', timesheet[2])]).write({
                'project_invoice_line_id': invoice.id,
            })
