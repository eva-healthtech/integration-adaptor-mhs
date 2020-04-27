import unittest
from unittest import mock
from datetime import datetime
from fhir.resources.identifier import Identifier
from fhir.resources.organization import Organization
from fhir.resources.patient import Patient
from fhir.resources.practitioner import Practitioner

import re

from outbound.converter.interchange_translator import FhirToEdifactTranslator
from utilities.test_utilities import async_test


class TestFhirToEdifactTranslator(unittest.TestCase):

    UNB_PATTERN = r"^UNB\+UNOA:2\+(?P<sender>[a-zA-Z0-9]+)\+(?P<recipient>[a-zA-Z0-9]+)+\+(?P<timestamp>[0-9]{6}:[0-9]{4})\+(?P<sis>[0-9]{8})'$"
    UNH_PATTERN = r"^UNH\+(?P<sms>[0-9]{8})\+FHSREG:0:1:FH:FHS001'$"
    BGM_PATTERN = r"^BGM\+\+\+507'$"
    UNT_PATTERN = r"^UNT\+(?P<segment_count>[0-9]+)\+(?P<sms>[0-9]{8})'$"
    UNZ_PATTERN = r"^UNZ\+(?P<message_count>[0-9]+)\+(?P<sis>[0-9]{8})'$"

    # TODO: mock sequence generators
    @async_test
    async def test_message_translated(self):
        patient = Patient()
        gp = Practitioner()
        gp_id = Identifier()
        gp_id.value = 'GP123'
        gp.identifier = [gp_id]
        patient.generalPractitioner = [gp]
        ha = Organization()
        ha_id = Identifier()
        ha_id.value = 'HA456'
        ha.identifier = [ha_id]
        patient.managingOrganization = [ha]

        translator = FhirToEdifactTranslator()
        edifact = await translator.convert(patient)

        self.assertIsNotNone(edifact)
        self.assertTrue(len(edifact) > 0)
        print(edifact)
        segments = edifact.splitlines()

        unz = segments.pop()
        self.assertRegex(unz, self.UNZ_PATTERN)
        unz_match = re.match(self.UNZ_PATTERN, unz)
        self.assertEqual('1', unz_match.group('message_count'))
        self.assertEqual('00000001', unz_match.group('sis'))

        unt = segments.pop()
        self.assertRegex(unt, self.UNT_PATTERN)
        unt_match = re.match(self.UNT_PATTERN, unt)
        self.assertEqual('3', unt_match.group('segment_count'))
        self.assertEqual('00000001', unt_match.group('sms'))

        bgm = segments.pop()
        self.assertRegex(bgm, self.BGM_PATTERN)

        unh = segments.pop()
        self.assertRegex(unh, self.UNH_PATTERN)
        unh_match = re.match(self.UNH_PATTERN, unh)
        self.assertEqual('00000001', unh_match.group('sms'))

        unb = segments.pop()
        self.assertRegex(unb, self.UNB_PATTERN)
        unb_match = re.match(self.UNB_PATTERN, unb)
        self.assertEqual('GP123', unb_match.group('sender'))
        self.assertEqual('HA456', unb_match.group('recipient'))
        # TODO: timestamp
        self.assertEqual('00000001', unb_match.group('sis'))