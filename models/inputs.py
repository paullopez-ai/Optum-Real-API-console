"""
Input field definitions for each Optum API.
Each field has a name, type, required flag, default value, and description.
"""

from dataclasses import dataclass, field
from datetime import date


@dataclass
class InputField:
    name: str
    field_type: str  # "string", "string[]", "float", "int"
    required: bool
    default: str | None
    description: str
    group: str = ""  # for grouping (e.g., "Service Line 1")


# ── API 1: Pre-Service Eligibility & Benefits ──

ELIGIBILITY_FIELDS: list[InputField] = [
    InputField("memberId", "string", True, None, "Member ID (e.g., 963997463)"),
    InputField("firstName", "string", True, None, "Subscriber first name"),
    InputField("lastName", "string", True, None, "Subscriber last name"),
    InputField("groupNumber", "string", True, None, "Insurance group number"),
    InputField("dateOfBirth", "string", True, None, "Date of birth (YYYY-MM-DD)"),
    InputField("serviceStartDate", "string", True, None, "Service start date (YYYY-MM-DD)"),
    InputField("serviceEndDate", "string", True, None, "Service end date (YYYY-MM-DD)"),
    InputField("payerId", "string", True, None, "Payer ID (e.g., 87726)"),
    InputField("providerNPI", "string", True, None, "Provider NPI number (10 digits)"),
    InputField("providerFirstName", "string", True, "Sample", "Provider first name"),
    InputField("providerLastName", "string", True, "Provider", "Provider last name"),
    InputField("serviceLevelCodes", "string[]", False, "30", "Service type codes (comma-separated)"),
]

ELIGIBILITY_PRESETS: list[dict] = [
    {
        "name": "Aisha Rahman — Imaging (Bronze HSA)",
        "values": {
            "memberId": "963997463",
            "firstName": "Aisha",
            "lastName": "Rahman",
            "groupNumber": "GRP-2026-BRONZE",
            "dateOfBirth": "1985-06-15",
            "serviceStartDate": str(date.today()),
            "serviceEndDate": str(date.today()),
            "payerId": "87726",
            "providerNPI": "1234567890",
            "providerFirstName": "Sample",
            "providerLastName": "Provider",
            "serviceLevelCodes": "30",
        },
    },
    {
        "name": "Marcus Thompson — Office Visit (Gold PPO)",
        "values": {
            "memberId": "847291035",
            "firstName": "Marcus",
            "lastName": "Thompson",
            "groupNumber": "GRP-2026-GOLD",
            "dateOfBirth": "1972-11-20",
            "serviceStartDate": str(date.today()),
            "serviceEndDate": str(date.today()),
            "payerId": "87726",
            "providerNPI": "1234567890",
            "providerFirstName": "Sample",
            "providerLastName": "Provider",
            "serviceLevelCodes": "30",
        },
    },
]


# ── API 2: Prior Authorization Status ──

PA_STATUS_FIELDS: list[InputField] = [
    InputField("authorizationNumber", "string", True, None, "PA authorization number (e.g., AUTH-2026-0210-4471)"),
    InputField("tradingPartnerServiceId", "string", True, None, "Payer trading partner ID (e.g., UHC-87726)"),
]

PA_STATUS_PRESETS: list[dict] = [
    {
        "name": "Approved — Standard (Knee MRI)",
        "values": {
            "authorizationNumber": "AUTH-2026-0210-4471",
            "tradingPartnerServiceId": "UHC-87726",
        },
    },
    {
        "name": "Pending Clinical Review (Lumbar Fusion)",
        "values": {
            "authorizationNumber": "AUTH-2026-0215-8823",
            "tradingPartnerServiceId": "UHC-87726",
        },
    },
    {
        "name": "Denied — Medical Necessity (Spinal Stimulator)",
        "values": {
            "authorizationNumber": "AUTH-2026-0112-3309",
            "tradingPartnerServiceId": "UHC-87726",
        },
    },
]


# ── API 3: Claim Pre-Check ──

CLAIM_PRECHECK_RAW_FIELDS: list[InputField] = [
    InputField("x12RequestData", "string", True, None, "Complete X12 837P claim string"),
    InputField("payerId", "string", True, "87726", "Payer ID"),
]

CLAIM_PRECHECK_STRUCTURED_FIELDS: list[InputField] = [
    # Patient
    InputField("patientFirstName", "string", True, None, "Patient first name", "Patient"),
    InputField("patientLastName", "string", True, None, "Patient last name", "Patient"),
    InputField("patientDob", "string", True, None, "Patient DOB (YYYY-MM-DD)", "Patient"),
    InputField("patientGender", "string", True, None, "M or F", "Patient"),
    InputField("patientStreet", "string", True, None, "Patient street address", "Patient"),
    InputField("patientCity", "string", True, None, "Patient city", "Patient"),
    InputField("patientState", "string", True, None, "Patient state (2-letter)", "Patient"),
    InputField("patientZip", "string", True, None, "Patient ZIP code", "Patient"),
    InputField("memberId", "string", True, None, "Insurance member ID", "Patient"),
    # Payer
    InputField("payerId", "string", True, "87726", "Payer ID", "Payer"),
    InputField("payerName", "string", True, "UNITED HEALTHCARE", "Payer name", "Payer"),
    # Provider
    InputField("providerNpi", "string", True, None, "Provider NPI (10 digits)", "Provider"),
    InputField("providerTaxId", "string", True, None, "Provider TIN (from .env if blank)", "Provider"),
    InputField("providerOrganization", "string", True, None, "Provider organization name", "Provider"),
    InputField("providerLastName", "string", True, None, "Provider contact last name", "Provider"),
    InputField("providerStreet", "string", True, None, "Provider street", "Provider"),
    InputField("providerCity", "string", True, None, "Provider city", "Provider"),
    InputField("providerState", "string", True, None, "Provider state (2-letter)", "Provider"),
    InputField("providerZip", "string", True, None, "Provider ZIP", "Provider"),
    # Claim
    InputField("placeOfService", "string", True, "11", "Place of service code", "Claim"),
    InputField("claimFrequencyCode", "string", True, "1", "Frequency code (1=original)", "Claim"),
    InputField("totalChargeAmount", "float", True, None, "Total charge in dollars", "Claim"),
    InputField("diagnosisCodes", "string[]", True, None, "ICD-10 codes (comma-separated)", "Claim"),
    # Service line 1
    InputField("procedureCode", "string", True, None, "CPT code", "Service Line"),
    InputField("chargeAmount", "float", True, None, "Line charge amount", "Service Line"),
    InputField("units", "int", True, "1", "Number of units", "Service Line"),
    InputField("dateOfService", "string", True, None, "Date of service (YYYY-MM-DD)", "Service Line"),
    InputField("modifiers", "string[]", False, "", "Modifiers (comma-separated)", "Service Line"),
    InputField("diagnosisPointers", "string[]", False, "0", "0-based diagnosis indices (comma-separated)", "Service Line"),
]

CLAIM_PRECHECK_PRESETS: list[dict] = [
    {
        "name": "Office Visit — Simple (99213)",
        "values": {
            "patientFirstName": "Zia",
            "patientLastName": "Brown",
            "patientDob": "1980-06-05",
            "patientGender": "F",
            "patientStreet": "201 MONTGOMERY STREET",
            "patientCity": "JERSEY CITY",
            "patientState": "NJ",
            "patientZip": "07302",
            "memberId": "990313643",
            "payerId": "87726",
            "payerName": "UNITED HEALTHCARE",
            "providerNpi": "1942376918",
            "providerTaxId": "",
            "providerOrganization": "COVENANT MULTISPECIALTY GROUP LLC",
            "providerLastName": "DAVIS",
            "providerStreet": "3555 S VAL VISTA DR",
            "providerCity": "GILBERT",
            "providerState": "AZ",
            "providerZip": "85297",
            "placeOfService": "11",
            "claimFrequencyCode": "1",
            "totalChargeAmount": "165.00",
            "diagnosisCodes": "B351,D649,R600",
            "procedureCode": "99214",
            "chargeAmount": "165.00",
            "units": "1",
            "dateOfService": str(date.today()),
            "modifiers": "",
            "diagnosisPointers": "0,1,2",
        },
    },
]
