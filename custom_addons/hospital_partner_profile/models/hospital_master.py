# -*- coding: utf-8 -*-
from odoo import models, fields

class HospitalCity(models.Model):
    _name = 'hospital.partner.city'
    _description = 'Hospital Partner City'
    _order = 'name'

    name = fields.Char(string='City', required=True)
    active = fields.Boolean(default=True)

class HospitalOccupation(models.Model):
    _name = 'hospital.partner.occupation'
    _description = 'Hospital Partner Occupation'
    _order = 'name'

    name = fields.Char(string='Occupation', required=True)
    active = fields.Boolean(default=True)

class HospitalEmployer(models.Model):
    _name = 'hospital.partner.employer'
    _description = 'Hospital Partner Employer'
    _order = 'name'

    name = fields.Char(string='Employer', required=True)
    active = fields.Boolean(default=True)

class HospitalMedicalSpecialization(models.Model):
    _name = 'hospital.partner.medical.specialization'
    _description = 'Hospital Partner Medical Specialization'
    _order = 'name'

    name = fields.Char(string='Medical Specialization', required=True)
    active = fields.Boolean(default=True)
