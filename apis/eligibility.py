"""
Pre-Service Eligibility & Benefits API.
Port of: patient-cost-clarity-starter/lib/optum-eligibility.ts
"""

import os
import time
from uuid import uuid4

import httpx

from auth import get_optum_bearer_token


ELIGIBILITY_QUERY = """
query CheckEligibility($input: EligibilityInput!) {
  checkEligibility(input: $input) {
    eligibility {
      eligibilityInfo {
        trnId
        member {
          memberId
          firstName
          lastName
          middleName
          suffix
          dateOfBirth
          gender
          relationshipCode
          dependentSequenceNumber
          individualRelationship {
            code
            description
          }
          relationshipType {
            code
            description
          }
        }
        contact {
          addresses {
            type
            street1
            street2
            city
            state
            country
            zip
            zip4
          }
        }
        insuranceInfo {
          policyNumber
          eligibilityStartDate
          eligibilityEndDate
          planStartDate
          planEndDate
          policyStatus
          planTypeDescription
          groupName
          address {
            type
            street1
            street2
            city
            state
            country
            zip
            zip4
          }
          stateOfIssueCode
          productType
          productId
          productCode
          payerId
          lineOfBusinessCode
          governmentProgramCode
          coverageType
          insuranceTypeCode
          insuranceType
          paidThroughDate
          consumerName
        }
        associatedIds {
          alternateId
          medicaidRecipientId
          exchangeMemberId
          alternateSubscriberId
          hicNumber
          mbiNumber
          subscriberMemberFacingIdentifier
          survivingSpouseId
          subscriberId
          memberReplacementId
          legacyMemberId
          healthInsuranceExchangeId
        }
        planLevels {
          level
          family {
            networkStatus
            planAmount
            planAmountFrequency
            remainingAmount
          }
          individual {
            networkStatus
            planAmount
            planAmountFrequency
            remainingAmount
          }
        }
        delegatedInfo {
          entity
          payerId
          contact {
            phone
            fax
            email
          }
          addresses {
            type
            street1
            street2
            city
            state
            country
            zip
            zip4
          }
        }
      }
      primaryCarePhysician {
        lastName
        firstName
        middleName
        phoneNumber
        address {
          type
          street1
          street2
          city
          state
          country
          zip
          zip4
        }
        affiliateHospitalName
        providerGroupName
        pcpSpeciality
        pcpStartDate
        pcpEndDate
        providerNPI
        providerTIN
        acoNetworkDescription
        acoNetworkId
      }
      providerNetwork {
        status
        tier
        speciality
      }
      serviceLevels {
        vendorServices {
          key
          vendorName
          url
          phone
          serviceDescription
          serviceTypeCode
        }
        family {
          networkStatus
          services {
            service
            serviceCode
            serviceDate
            status
            planAmount
            remainingAmount
            metYearToDateAmount
            message {
              coPay {
                isSingleMessageDetail
                isViewDetail
                messages
                subMessages {
                  service
                  status
                  copay
                  frequency
                  msg
                  startDate
                  endDate
                  minCopay
                  minCopayMsg
                  maxCopay
                  maxCopayMsg
                  isPrimaryIndicator
                  exactCopay {
                    coveredStatus
                    copayDetails {
                      amount
                      serviceSetting
                    }
                  }
                }
                limitationInfo {
                  lmtPeriod
                  lmtType
                  lmtOccurPerPeriod
                  lmtDollarPerPeriod
                  messages
                }
                isMultipleCopaysFound
                isMultipleCoinsuranceFound
              }
              coInsurance {
                isSingleMessageDetail
                isViewDetail
                messages
                subMessages {
                  service
                  status
                  copay
                  msg
                  startDate
                  endDate
                  minCopay
                  minCopayMsg
                  maxCopay
                  maxCopayMsg
                  isPrimaryIndicator
                }
                limitationInfo {
                  lmtPeriod
                  lmtType
                  lmtOccurPerPeriod
                  lmtDollarPerPeriod
                  messages
                }
                isMultipleCopaysFound
                isMultipleCoinsuranceFound
              }
              deductible {
                isSingleMessageDetail
                isViewDetail
                messages
                subMessages {
                  service
                  status
                  copay
                  msg
                  startDate
                  endDate
                  minCopay
                  minCopayMsg
                  maxCopay
                  maxCopayMsg
                  isPrimaryIndicator
                }
                limitationInfo {
                  lmtPeriod
                  lmtType
                  lmtOccurPerPeriod
                  lmtDollarPerPeriod
                  messages
                }
                isMultipleCopaysFound
                isMultipleCoinsuranceFound
              }
              benefitsAllowed {
                isSingleMessageDetail
                isViewDetail
                messages
                subMessages {
                  service
                  status
                  copay
                  msg
                  startDate
                  endDate
                  minCopay
                  minCopayMsg
                  maxCopay
                  maxCopayMsg
                  isPrimaryIndicator
                }
                limitationInfo {
                  lmtPeriod
                  lmtType
                  lmtOccurPerPeriod
                  lmtDollarPerPeriod
                  messages
                }
                isMultipleCopaysFound
                isMultipleCoinsuranceFound
              }
              benefitsRemaining {
                isSingleMessageDetail
                isViewDetail
                messages
                subMessages {
                  service
                  status
                  copay
                  msg
                  startDate
                  endDate
                  minCopay
                  minCopayMsg
                  maxCopay
                  maxCopayMsg
                  isPrimaryIndicator
                }
                limitationInfo {
                  lmtPeriod
                  lmtType
                  lmtOccurPerPeriod
                  lmtDollarPerPeriod
                  messages
                }
                isMultipleCopaysFound
                isMultipleCoinsuranceFound
              }
              coPayList {
                placeOfService
                copay
                service
                startDate
                endDate
                messages
              }
              coInsuranceList {
                placeOfService
                coinsurancePercent
                service
                messages
                startDate
                endDate
              }
            }
          }
        }
        individual {
          networkStatus
          services {
            service
            serviceCode
            serviceDate
            status
            planAmount
            remainingAmount
            metYearToDateAmount
            message {
              coPay {
                isSingleMessageDetail
                isViewDetail
                messages
                subMessages {
                  service
                  status
                  copay
                  frequency
                  msg
                  startDate
                  endDate
                  minCopay
                  minCopayMsg
                  maxCopay
                  maxCopayMsg
                  isPrimaryIndicator
                  exactCopay {
                    coveredStatus
                    copayDetails {
                      amount
                      serviceSetting
                    }
                  }
                }
                limitationInfo {
                  lmtPeriod
                  lmtType
                  lmtOccurPerPeriod
                  lmtDollarPerPeriod
                  messages
                }
                isMultipleCopaysFound
                isMultipleCoinsuranceFound
              }
              coInsurance {
                isSingleMessageDetail
                isViewDetail
                messages
                subMessages {
                  service
                  status
                  copay
                  msg
                  startDate
                  endDate
                  minCopay
                  minCopayMsg
                  maxCopay
                  maxCopayMsg
                  isPrimaryIndicator
                }
                limitationInfo {
                  lmtPeriod
                  lmtType
                  lmtOccurPerPeriod
                  lmtDollarPerPeriod
                  messages
                }
                isMultipleCopaysFound
                isMultipleCoinsuranceFound
              }
              deductible {
                isSingleMessageDetail
                isViewDetail
                messages
                subMessages {
                  service
                  status
                  copay
                  msg
                  startDate
                  endDate
                  minCopay
                  minCopayMsg
                  maxCopay
                  maxCopayMsg
                  isPrimaryIndicator
                }
                limitationInfo {
                  lmtPeriod
                  lmtType
                  lmtOccurPerPeriod
                  lmtDollarPerPeriod
                  messages
                }
                isMultipleCopaysFound
                isMultipleCoinsuranceFound
              }
              benefitsAllowed {
                isSingleMessageDetail
                isViewDetail
                messages
                subMessages {
                  service
                  status
                  copay
                  msg
                  startDate
                  endDate
                  minCopay
                  minCopayMsg
                  maxCopay
                  maxCopayMsg
                  isPrimaryIndicator
                }
                limitationInfo {
                  lmtPeriod
                  lmtType
                  lmtOccurPerPeriod
                  lmtDollarPerPeriod
                  messages
                }
                isMultipleCopaysFound
                isMultipleCoinsuranceFound
              }
              benefitsRemaining {
                isSingleMessageDetail
                isViewDetail
                messages
                subMessages {
                  service
                  status
                  copay
                  msg
                  startDate
                  endDate
                  minCopay
                  minCopayMsg
                  maxCopay
                  maxCopayMsg
                  isPrimaryIndicator
                }
                limitationInfo {
                  lmtPeriod
                  lmtType
                  lmtOccurPerPeriod
                  lmtDollarPerPeriod
                  messages
                }
                isMultipleCopaysFound
                isMultipleCoinsuranceFound
              }
              coPayList {
                placeOfService
                copay
                service
                startDate
                endDate
                messages
              }
              coInsuranceList {
                placeOfService
                coinsurancePercent
                service
                messages
                startDate
                endDate
              }
            }
          }
        }
      }
      additionalInfo {
        fundingType
        fundingArrangementDescription
        businessSegment
        sizeDefinitionDescription
        revenueArrangementDescription
        hsa
        cdhp
        cmsHId
        cmsContractId
        benefitPlanId
        virtualVisit
        hraBalance
        hraMessage
        medicareGuidelines
        medicareEntitlementReason
      }
    }
  }
}
""".strip()


def build_variables(user_input: dict) -> dict:
    """Build GraphQL variables from user input."""
    service_codes = user_input.get("serviceLevelCodes", "30")
    if isinstance(service_codes, str):
        service_codes = [s.strip() for s in service_codes.split(",") if s.strip()]

    return {
        "input": {
            "memberId": user_input["memberId"],
            "firstName": user_input["firstName"],
            "lastName": user_input["lastName"],
            "groupNumber": user_input["groupNumber"],
            "dateOfBirth": user_input["dateOfBirth"],
            "serviceStartDate": user_input["serviceStartDate"],
            "serviceEndDate": user_input["serviceEndDate"],
            "payerId": user_input["payerId"],
            "providerNPI": user_input["providerNPI"],
            "providerFirstName": user_input.get("providerFirstName", "Sample"),
            "providerLastName": user_input.get("providerLastName", "Provider"),
            "serviceLevelCodes": service_codes,
        }
    }


def get_endpoint() -> str:
    url = os.environ.get("OPTUM_ELIGIBILITY_URL")
    if not url:
        raise RuntimeError("OPTUM_ELIGIBILITY_URL is not configured in .env")
    return url


def build_headers(token: str) -> dict:
    provider_tax_id = os.environ.get("OPTUM_PROVIDER_TAX_ID", "")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "x-optum-consumer-correlation-id": f"api-console-elig-{uuid4()}",
        "environment": "sandbox",
    }
    if provider_tax_id:
        headers["providerTaxId"] = provider_tax_id
    return headers


def execute(user_input: dict) -> dict:
    """
    Run the eligibility check. Returns dict with:
    endpoint, headers, request_body, response_status, response_headers, response_body, duration_ms
    """
    token = get_optum_bearer_token()
    endpoint = get_endpoint()
    headers = build_headers(token)
    variables = build_variables(user_input)

    request_body = {
        "query": ELIGIBILITY_QUERY,
        "variables": variables,
    }

    start = time.time()
    response = httpx.post(
        endpoint,
        json=request_body,
        headers=headers,
        timeout=60.0,
    )
    duration_ms = int((time.time() - start) * 1000)

    try:
        response_body = response.json()
    except Exception:
        response_body = {"raw_text": response.text}

    return {
        "api_name": "Pre-Service Eligibility & Benefits",
        "endpoint": endpoint,
        "headers": headers,
        "request_body": request_body,
        "response_status": response.status_code,
        "response_headers": dict(response.headers),
        "response_body": response_body,
        "duration_ms": duration_ms,
    }
