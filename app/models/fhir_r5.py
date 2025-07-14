"""
FHIR R5 Resource Models for Healthcare IoT Data
=============================================
Comprehensive FHIR R5 implementation for medical device data,
patient information, and clinical observations from AVA4 MQTT streams.

Based on FHIR R5 specification: https://hl7.org/fhir/R5/
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Literal
from pydantic import BaseModel, Field, validator
from bson import ObjectId
from enum import Enum

# =============== FHIR R5 Base Elements ===============

class FHIRElement(BaseModel):
    """Base FHIR element with extensions"""
    id: Optional[str] = Field(None, description="Unique id for element")
    extension: Optional[List[Dict[str, Any]]] = Field(None, description="Additional content defined by implementations")

class FHIRResource(FHIRElement):
    """Base FHIR Resource"""
    resourceType: str = Field(..., description="FHIR resource type")
    id: Optional[str] = Field(None, description="Logical id of this artifact")
    meta: Optional[Dict[str, Any]] = Field(None, description="Metadata about the resource")
    implicitRules: Optional[str] = Field(None, description="A set of rules under which this content was created")
    language: Optional[str] = Field(None, description="Language of the resource content")
    text: Optional[Dict[str, Any]] = Field(None, description="Text summary of resource")
    contained: Optional[List[Dict[str, Any]]] = Field(None, description="Contained, inline Resources")
    extension: Optional[List[Dict[str, Any]]] = Field(None, description="Additional content")
    modifierExtension: Optional[List[Dict[str, Any]]] = Field(None, description="Extensions that cannot be ignored")

# =============== FHIR R5 Data Types ===============

class Identifier(FHIRElement):
    """An identifier intended for computation"""
    use: Optional[Literal["usual", "official", "temp", "secondary", "old"]] = Field(None, description="Identifier use")
    type: Optional[Dict[str, Any]] = Field(None, description="Description of identifier")
    system: Optional[str] = Field(None, description="The namespace for the identifier value")
    value: Optional[str] = Field(None, description="The value that is unique")
    period: Optional[Dict[str, Any]] = Field(None, description="Time period when id is/was valid for use")
    assigner: Optional[Dict[str, Any]] = Field(None, description="Organization that issued id")

class CodeableConcept(FHIRElement):
    """A concept that may be defined by a formal reference to a terminology or ontology"""
    coding: Optional[List[Dict[str, Any]]] = Field(None, description="Code defined by a terminology system")
    text: Optional[str] = Field(None, description="Plain text representation of the concept")

class Quantity(FHIRElement):
    """A measured or measurable amount"""
    value: Optional[float] = Field(None, description="Numerical value")
    comparator: Optional[Literal["<", "<=", ">=", ">"]] = Field(None, description="Comparison operator")
    unit: Optional[str] = Field(None, description="Unit representation")
    system: Optional[str] = Field(None, description="System that defines coded unit form")
    code: Optional[str] = Field(None, description="Coded form of the unit")

class Period(FHIRElement):
    """Time range defined by start and end date/time"""
    start: Optional[datetime] = Field(None, description="Starting time with inclusive boundary")
    end: Optional[datetime] = Field(None, description="End time with inclusive boundary")

class Reference(FHIRElement):
    """A reference from one resource to another"""
    reference: Optional[str] = Field(None, description="Literal reference, Relative, internal or absolute URL")
    type: Optional[str] = Field(None, description="Type the reference refers to")
    identifier: Optional[Identifier] = Field(None, description="Logical reference, when literal reference is not known")
    display: Optional[str] = Field(None, description="Text alternative for the resource")

class HumanName(FHIRElement):
    """Name of a human - parts and usage"""
    use: Optional[Literal["usual", "official", "temp", "nickname", "anonymous", "old", "maiden"]] = Field(None, description="Name use")
    text: Optional[str] = Field(None, description="Text representation of the full name")
    family: Optional[str] = Field(None, description="Family name (surname)")
    given: Optional[List[str]] = Field(None, description="Given names (first name, middle names)")
    prefix: Optional[List[str]] = Field(None, description="Parts that come before the name")
    suffix: Optional[List[str]] = Field(None, description="Parts that come after the name")
    period: Optional[Period] = Field(None, description="Time period when name was/is in use")

class ContactPoint(FHIRElement):
    """Details for all kinds of technology-mediated contact points"""
    system: Optional[Literal["phone", "fax", "email", "pager", "url", "sms", "other"]] = Field(None, description="Contact point system")
    value: Optional[str] = Field(None, description="The actual contact point details")
    use: Optional[Literal["home", "work", "temp", "old", "mobile"]] = Field(None, description="Contact point use")
    rank: Optional[int] = Field(None, description="Specify preferred order of use")
    period: Optional[Period] = Field(None, description="Time period when the contact point was/is in use")

class Address(FHIRElement):
    """An address expressed using postal conventions"""
    use: Optional[Literal["home", "work", "temp", "old", "billing"]] = Field(None, description="Address use")
    type: Optional[Literal["postal", "physical", "both"]] = Field(None, description="Address type")
    text: Optional[str] = Field(None, description="Text representation of the address")
    line: Optional[List[str]] = Field(None, description="Street name, number, direction & P.O. Box etc.")
    city: Optional[str] = Field(None, description="Name of city, town etc.")
    district: Optional[str] = Field(None, description="District name (aka county)")
    state: Optional[str] = Field(None, description="Sub-unit of country (abbreviations ok)")
    postalCode: Optional[str] = Field(None, description="Postal code for area")
    country: Optional[str] = Field(None, description="Country (e.g. may be ISO 3166 2 or 3 letter code)")
    period: Optional[Period] = Field(None, description="Time period when address was/is in use")

# =============== FHIR R5 Patient Resource ===============

class Patient(FHIRResource):
    """Information about an individual receiving health care services"""
    resourceType: Literal["Patient"] = Field("Patient")
    
    # Core identifiers
    identifier: Optional[List[Identifier]] = Field(None, description="An identifier for this patient")
    active: Optional[bool] = Field(None, description="Whether this patient's record is in active use")
    
    # Demographics
    name: Optional[List[HumanName]] = Field(None, description="A name associated with the patient")
    telecom: Optional[List[ContactPoint]] = Field(None, description="A contact detail for the individual")
    gender: Optional[Literal["male", "female", "other", "unknown"]] = Field(None, description="Administrative gender")
    birthDate: Optional[str] = Field(None, description="The date of birth for the individual")
    deceased: Optional[Union[bool, datetime]] = Field(None, description="Indicates if the individual is deceased")
    address: Optional[List[Address]] = Field(None, description="An address for the individual")
    
    # Relationships
    maritalStatus: Optional[CodeableConcept] = Field(None, description="Marital (civil) status of a patient")
    multipleBirth: Optional[Union[bool, int]] = Field(None, description="Whether patient is part of a multiple birth")
    photo: Optional[List[Dict[str, Any]]] = Field(None, description="Image of the patient")
    contact: Optional[List[Dict[str, Any]]] = Field(None, description="A contact party for the patient")
    
    # Medical information
    communication: Optional[List[Dict[str, Any]]] = Field(None, description="A language which may be used to communicate with the patient")
    generalPractitioner: Optional[List[Reference]] = Field(None, description="Patient's nominated primary care provider")
    managingOrganization: Optional[Reference] = Field(None, description="Organization that is the custodian of the patient record")
    link: Optional[List[Dict[str, Any]]] = Field(None, description="Link to a Patient or RelatedPerson resource")

# =============== FHIR R5 Observation Resource ===============

class ObservationComponent(FHIRElement):
    """Component observation (for multi-component observations)"""
    code: CodeableConcept = Field(..., description="Type of component observation")
    value: Optional[Union[Quantity, CodeableConcept, str, bool, int, Dict[str, Any]]] = Field(None, description="Actual component result")
    dataAbsentReason: Optional[CodeableConcept] = Field(None, description="Why component result is missing")
    interpretation: Optional[List[CodeableConcept]] = Field(None, description="High, low, normal, etc.")
    referenceRange: Optional[List[Dict[str, Any]]] = Field(None, description="Provides guide for interpretation")

class Observation(FHIRResource):
    """Measurements and simple assertions made about a patient"""
    resourceType: Literal["Observation"] = Field("Observation")
    
    # Core observation data
    identifier: Optional[List[Identifier]] = Field(None, description="Business Identifier for observation")
    instantiates: Optional[Union[str, Reference]] = Field(None, description="Instantiates FHIR ObservationDefinition")
    basedOn: Optional[List[Reference]] = Field(None, description="Fulfills plan, proposal or order")
    triggeredBy: Optional[List[Dict[str, Any]]] = Field(None, description="Triggering observation(s)")
    partOf: Optional[List[Reference]] = Field(None, description="Part of referenced event")
    
    # Status and category
    status: Literal["registered", "preliminary", "final", "amended", "corrected", "cancelled", "entered-in-error", "unknown"] = Field(..., description="Observation status")
    category: Optional[List[CodeableConcept]] = Field(None, description="Classification of type of observation")
    code: CodeableConcept = Field(..., description="Type of observation")
    
    # Subject and context
    subject: Optional[Reference] = Field(None, description="Who and/or what the observation is about")
    focus: Optional[List[Reference]] = Field(None, description="What the observation is about")
    encounter: Optional[Reference] = Field(None, description="Healthcare event during which this observation is made")
    
    # Timing
    effective: Optional[Union[datetime, Period, Dict[str, Any]]] = Field(None, description="Clinically relevant time/time-period for observation")
    issued: Optional[datetime] = Field(None, description="Date/Time this version was made available")
    
    # Responsible parties
    performer: Optional[List[Reference]] = Field(None, description="Who is responsible for the observation")
    
    # Values and results
    value: Optional[Union[Quantity, CodeableConcept, str, bool, int, Dict[str, Any]]] = Field(None, description="Actual result")
    dataAbsentReason: Optional[CodeableConcept] = Field(None, description="Why the result is missing")
    interpretation: Optional[List[CodeableConcept]] = Field(None, description="High, low, normal, etc.")
    note: Optional[List[Dict[str, Any]]] = Field(None, description="Comments about the observation")
    bodySite: Optional[CodeableConcept] = Field(None, description="Observed body part")
    bodyStructure: Optional[Reference] = Field(None, description="Observed body structure")
    method: Optional[CodeableConcept] = Field(None, description="How it was done")
    specimen: Optional[Reference] = Field(None, description="Specimen used for this observation")
    device: Optional[Reference] = Field(None, description="Device used for this observation")
    
    # Reference ranges and related observations
    referenceRange: Optional[List[Dict[str, Any]]] = Field(None, description="Provides guide for interpretation")
    hasMember: Optional[List[Reference]] = Field(None, description="Related resource that belongs to the Observation group")
    derivedFrom: Optional[List[Reference]] = Field(None, description="Related resource from which the observation is made")
    component: Optional[List[ObservationComponent]] = Field(None, description="Component observation")

# =============== FHIR R5 Device Resource ===============

class Device(FHIRResource):
    """A type of a manufactured item that is used in the provision of healthcare"""
    resourceType: Literal["Device"] = Field("Device")
    
    # Core device information
    identifier: Optional[List[Identifier]] = Field(None, description="Instance identifier")
    definition: Optional[Reference] = Field(None, description="The reference to the definition for the device")
    udiCarrier: Optional[List[Dict[str, Any]]] = Field(None, description="Unique Device Identifier (UDI) Barcode string")
    status: Optional[Literal["active", "inactive", "entered-in-error"]] = Field(None, description="Device availability")
    availabilityStatus: Optional[CodeableConcept] = Field(None, description="lost | damaged | destroyed | available")
    biologicalSourceEvent: Optional[Identifier] = Field(None, description="An identifier that supports traceability to the event during which material in this product from one or more biological entities was obtained or pooled")
    manufacturer: Optional[str] = Field(None, description="Name of device manufacturer")
    manufactureDate: Optional[datetime] = Field(None, description="Date when the device was made")
    expirationDate: Optional[datetime] = Field(None, description="Date and time of expiry of this device")
    lotNumber: Optional[str] = Field(None, description="Lot number of manufacture")
    serialNumber: Optional[str] = Field(None, description="Serial number assigned by the manufacturer")
    
    # Device names and types
    deviceName: Optional[List[Dict[str, Any]]] = Field(None, description="The name or names of the device as given by the manufacturer")
    modelNumber: Optional[str] = Field(None, description="The manufacturer's model number for the device")
    partNumber: Optional[str] = Field(None, description="The part number or catalog number of the device")
    category: Optional[List[CodeableConcept]] = Field(None, description="Indicates a high-level grouping of the device")
    type: Optional[List[CodeableConcept]] = Field(None, description="The kind or type of device")
    version: Optional[List[Dict[str, Any]]] = Field(None, description="The actual design of the device or software version running on the device")
    
    # Conformance and capabilities
    conformsTo: Optional[List[Dict[str, Any]]] = Field(None, description="Identifies the standards, specifications, or formal guidances for the capabilities supported by the device")
    property: Optional[List[Dict[str, Any]]] = Field(None, description="Static or essentially static characteristics or features of the device")
    mode: Optional[CodeableConcept] = Field(None, description="The designated condition for performing a task")
    cycle: Optional[Dict[str, Any]] = Field(None, description="The series of occurrences that repeats during the operation of the device")
    duration: Optional[Dict[str, Any]] = Field(None, description="A measurement of time during the device's operation")
    
    # Ownership and responsibility
    owner: Optional[Reference] = Field(None, description="Organization responsible for device")
    contact: Optional[List[ContactPoint]] = Field(None, description="Details for human/organization for support")
    location: Optional[Reference] = Field(None, description="Where the device is found")
    url: Optional[str] = Field(None, description="Network address to contact device")
    endpoint: Optional[List[Reference]] = Field(None, description="Technical endpoints providing access to services provided by the device")
    
    # Associations
    gateway: Optional[List[Reference]] = Field(None, description="Linked device acting as a communication controller")
    note: Optional[List[Dict[str, Any]]] = Field(None, description="Device notes and comments")
    safety: Optional[List[CodeableConcept]] = Field(None, description="Safety Characteristics of Device")
    parent: Optional[Reference] = Field(None, description="The higher-level or encompassing device that this device is a logical part of")

# =============== FHIR R5 Organization Resource ===============

class Organization(FHIRResource):
    """A formally or informally recognized grouping of people or organizations"""
    resourceType: Literal["Organization"] = Field("Organization")
    
    # Core organization information
    identifier: Optional[List[Identifier]] = Field(None, description="Identifies this organization across multiple systems")
    active: Optional[bool] = Field(None, description="Whether the organization's record is still in active use")
    type: Optional[List[CodeableConcept]] = Field(None, description="Kind of organization")
    name: Optional[str] = Field(None, description="Name used for the organization")
    alias: Optional[List[str]] = Field(None, description="A list of alternate names that the organization is known as")
    description: Optional[str] = Field(None, description="Additional details about the Organization")
    
    # Contact information
    contact: Optional[List[Dict[str, Any]]] = Field(None, description="Contact for the organization for a certain purpose")
    telecom: Optional[List[ContactPoint]] = Field(None, description="A contact detail for the organization")
    address: Optional[List[Address]] = Field(None, description="An address for the organization")
    
    # Relationships
    partOf: Optional[Reference] = Field(None, description="The organization of which this organization forms a part")
    endpoint: Optional[List[Reference]] = Field(None, description="Technical endpoints providing access to services operated for the organization")
    
    # Qualifications
    qualification: Optional[List[Dict[str, Any]]] = Field(None, description="Qualifications, certifications, accreditations, licenses, training, etc. pertaining to the provision of care")

# =============== FHIR R5 Location Resource ===============

class Location(FHIRResource):
    """Details and position information for a place"""
    resourceType: Literal["Location"] = Field("Location")
    
    # Core location information
    identifier: Optional[List[Identifier]] = Field(None, description="Unique code or number identifying the location")
    status: Optional[Literal["active", "suspended", "inactive"]] = Field(None, description="active | suspended | inactive")
    operationalStatus: Optional[Dict[str, Any]] = Field(None, description="The operational status covers operation values most relevant to beds")
    name: Optional[str] = Field(None, description="Name of the location as used by humans")
    alias: Optional[List[str]] = Field(None, description="A list of alternate names that the location is known as")
    description: Optional[str] = Field(None, description="Additional details about the location")
    mode: Optional[Literal["instance", "kind"]] = Field(None, description="instance | kind")
    type: Optional[List[CodeableConcept]] = Field(None, description="Type of function performed")
    
    # Contact and address
    contact: Optional[List[ContactPoint]] = Field(None, description="Official contact details for the location")
    address: Optional[Address] = Field(None, description="Physical location")
    form: Optional[CodeableConcept] = Field(None, description="Physical form of the location")
    position: Optional[Dict[str, Any]] = Field(None, description="The absolute geographic location")
    
    # Relationships and management
    managingOrganization: Optional[Reference] = Field(None, description="Organization responsible for provisioning and upkeep")
    partOf: Optional[Reference] = Field(None, description="Another Location this one is physically a part of")
    characteristic: Optional[List[CodeableConcept]] = Field(None, description="Collection of characteristics (attributes)")
    hoursOfOperation: Optional[List[Dict[str, Any]]] = Field(None, description="What days/times during a week is this location usually open")
    virtualService: Optional[List[Dict[str, Any]]] = Field(None, description="Connection details of a virtual service")
    endpoint: Optional[List[Reference]] = Field(None, description="Technical endpoints providing access to services operated for the location")

# =============== FHIR R5 Condition Resource ===============

class Condition(FHIRResource):
    """A clinical condition, problem, diagnosis, or other event"""
    resourceType: Literal["Condition"] = Field("Condition")
    
    # Core condition information
    identifier: Optional[List[Identifier]] = Field(None, description="External Ids for this condition")
    clinicalStatus: Optional[CodeableConcept] = Field(None, description="active | recurrence | relapse | inactive | remission | resolved | unknown")
    verificationStatus: Optional[CodeableConcept] = Field(None, description="unconfirmed | provisional | differential | confirmed | refuted | entered-in-error")
    category: Optional[List[CodeableConcept]] = Field(None, description="problem-list-item | encounter-diagnosis")
    severity: Optional[CodeableConcept] = Field(None, description="Subjective severity of condition")
    code: Optional[CodeableConcept] = Field(None, description="Identification of the condition, problem or diagnosis")
    bodySite: Optional[List[CodeableConcept]] = Field(None, description="Anatomical location, if relevant")
    bodyStructure: Optional[List[Reference]] = Field(None, description="Anatomical location, if relevant")
    
    # Subject and context
    subject: Reference = Field(..., description="Who has the condition?")
    encounter: Optional[Reference] = Field(None, description="The Encounter during which this Condition was created")
    
    # Timing
    onset: Optional[Union[datetime, str, int, Period, Dict[str, Any]]] = Field(None, description="Estimated or actual date, date-time, or age")
    abatement: Optional[Union[datetime, str, int, Period, Dict[str, Any]]] = Field(None, description="When in resolution/remission")
    recordedDate: Optional[datetime] = Field(None, description="Date condition was first recorded")
    
    # Responsible parties and sources
    participant: Optional[List[Dict[str, Any]]] = Field(None, description="Who or what participated in the activities related to the condition")
    stage: Optional[List[Dict[str, Any]]] = Field(None, description="Stage/grade, usually assessed formally")
    evidence: Optional[List[Dict[str, Any]]] = Field(None, description="Supporting evidence for the condition")
    note: Optional[List[Dict[str, Any]]] = Field(None, description="Additional information about the Condition")

# =============== FHIR R5 Medication Resource ===============

class Medication(FHIRResource):
    """Definition of a Medication"""
    resourceType: Literal["Medication"] = Field("Medication")
    
    # Core medication information
    identifier: Optional[List[Identifier]] = Field(None, description="Business identifier for this medication")
    code: Optional[CodeableConcept] = Field(None, description="Codes that identify this medication")
    status: Optional[Literal["active", "inactive", "entered-in-error"]] = Field(None, description="active | inactive | entered-in-error")
    marketingAuthorizationHolder: Optional[Reference] = Field(None, description="Organization that has authorization to market medication")
    doseForm: Optional[CodeableConcept] = Field(None, description="powder | tablets | capsule +")
    totalVolume: Optional[Quantity] = Field(None, description="When the medication packaging specifies a contained volume")
    ingredient: Optional[List[Dict[str, Any]]] = Field(None, description="Active or inactive ingredient")
    batch: Optional[Dict[str, Any]] = Field(None, description="Details about packaged medications")
    definition: Optional[Reference] = Field(None, description="Knowledge about this medication")

# =============== FHIR R5 AllergyIntolerance Resource ===============

class AllergyIntolerance(FHIRResource):
    """Allergy or Intolerance (generally: Risk of adverse reaction to a substance)"""
    resourceType: Literal["AllergyIntolerance"] = Field("AllergyIntolerance")
    
    # Core allergy information
    identifier: Optional[List[Identifier]] = Field(None, description="External ids for this item")
    clinicalStatus: Optional[CodeableConcept] = Field(None, description="active | inactive | resolved")
    verificationStatus: Optional[CodeableConcept] = Field(None, description="unconfirmed | presumed | confirmed | refuted | entered-in-error")
    type: Optional[List[Literal["allergy", "intolerance"]]] = Field(None, description="allergy | intolerance - Underlying mechanism (if known)")
    category: Optional[List[Literal["food", "medication", "environment", "biologic"]]] = Field(None, description="food | medication | environment | biologic")
    criticality: Optional[Literal["low", "high", "unable-to-assess"]] = Field(None, description="low | high | unable-to-assess")
    code: Optional[CodeableConcept] = Field(None, description="Code that identifies the allergy or intolerance")
    
    # Subject and context
    patient: Reference = Field(..., description="Who the allergy or intolerance is for")
    encounter: Optional[Reference] = Field(None, description="Encounter when the allergy or intolerance was asserted")
    
    # Timing and source
    onset: Optional[Union[datetime, str, int, Period, Dict[str, Any]]] = Field(None, description="When allergy or intolerance was identified")
    recordedDate: Optional[datetime] = Field(None, description="Date allergy or intolerance was first recorded")
    participant: Optional[List[Dict[str, Any]]] = Field(None, description="Who or what participated in the activities related to the allergy or intolerance")
    lastOccurrence: Optional[datetime] = Field(None, description="Date(/time) of last known occurrence of a reaction")
    
    # Additional information
    note: Optional[List[Dict[str, Any]]] = Field(None, description="Additional text not captured in other fields")
    reaction: Optional[List[Dict[str, Any]]] = Field(None, description="Adverse Reaction Events linked to exposure to substance")

# =============== FHIR R5 Encounter Resource ===============

class Encounter(FHIRResource):
    """An interaction during which services are provided to the patient"""
    resourceType: Literal["Encounter"] = Field("Encounter")
    
    # Core encounter information
    identifier: Optional[List[Identifier]] = Field(None, description="Identifier(s) by which this encounter is known")
    status: Literal["planned", "in-progress", "on-hold", "discharged", "completed", "cancelled", "discontinued", "entered-in-error", "unknown"] = Field(..., description="Current state of the encounter")
    class_: Optional[Dict[str, Any]] = Field(None, alias="class", description="Classification of patient encounter context")
    priority: Optional[CodeableConcept] = Field(None, description="Indicates the urgency of the encounter")
    type: Optional[List[CodeableConcept]] = Field(None, description="Specific type of encounter")
    serviceType: Optional[List[CodeableConcept]] = Field(None, description="Specific type of service")
    
    # Subject and participants
    subject: Optional[Reference] = Field(None, description="The patient or group present at the encounter")
    subjectStatus: Optional[CodeableConcept] = Field(None, description="The current status of the subject in relation to the Encounter")
    episodeOfCare: Optional[List[Reference]] = Field(None, description="Episode(s) of care that this encounter should be recorded against")
    basedOn: Optional[List[Reference]] = Field(None, description="The request that initiated this encounter")
    careTeam: Optional[List[Reference]] = Field(None, description="The group(s) of individuals responsible for providing the services")
    partOf: Optional[Reference] = Field(None, description="Another Encounter this encounter is part of")
    
    # Service provider and location
    serviceProvider: Optional[Reference] = Field(None, description="The organization (facility) responsible for this encounter")
    participant: Optional[List[Dict[str, Any]]] = Field(None, description="List of participants involved in the encounter")
    appointment: Optional[List[Reference]] = Field(None, description="The appointment that scheduled this encounter")
    
    # Timing and duration
    virtualService: Optional[List[Dict[str, Any]]] = Field(None, description="Connection details of a virtual service")
    actualPeriod: Optional[Period] = Field(None, description="The actual start and end time of the encounter")
    plannedStartDate: Optional[datetime] = Field(None, description="The planned start date/time of the encounter")
    plannedEndDate: Optional[datetime] = Field(None, description="The planned end date/time of the encounter")
    length: Optional[Dict[str, Any]] = Field(None, description="Actual quantity of time the encounter lasted")
    
    # Reasons and outcomes
    reason: Optional[List[Dict[str, Any]]] = Field(None, description="The list of medical reasons that are expected to be addressed during the episode of care")
    diagnosis: Optional[List[Dict[str, Any]]] = Field(None, description="The list of diagnosis relevant to this encounter")
    account: Optional[List[Reference]] = Field(None, description="The set of accounts that may be used for billing for this Encounter")
    dietPreference: Optional[List[CodeableConcept]] = Field(None, description="Diet preferences reported by the patient")
    specialArrangement: Optional[List[CodeableConcept]] = Field(None, description="Wheelchair, translator, stretcher, etc.")
    specialCourtesy: Optional[List[CodeableConcept]] = Field(None, description="Special courtesies (VIP, board member)")
    
    # Admission and discharge
    admission: Optional[Dict[str, Any]] = Field(None, description="Details about the admission to a healthcare service")
    location: Optional[List[Dict[str, Any]]] = Field(None, description="List of locations where the patient has been")

# =============== FHIR R5 Provenance Resource ===============

class Provenance(FHIRResource):
    """Who, What, When for a set of resources"""
    resourceType: Literal["Provenance"] = Field("Provenance")
    
    # Core provenance information
    target: List[Reference] = Field(..., description="Target Reference(s) (usually version specific)")
    occurred: Optional[Union[Period, datetime]] = Field(None, description="When the activity occurred")
    recorded: datetime = Field(..., description="When the activity was recorded / updated")
    policy: Optional[List[str]] = Field(None, description="Policy or plan the activity was defined by")
    location: Optional[Reference] = Field(None, description="Where the activity occurred, if relevant")
    authorization: Optional[List[Reference]] = Field(None, description="Authorization (purposeOfUse) related to the event")
    activity: Optional[CodeableConcept] = Field(None, description="Activity that occurred")
    
    # Agents (who was involved)
    agent: List[Dict[str, Any]] = Field(..., description="Actor involved")
    entity: Optional[List[Dict[str, Any]]] = Field(None, description="An entity used in this activity")
    signature: Optional[List[Dict[str, Any]]] = Field(None, description="Signature on target")

# =============== FHIR R5 Bundle Resource for Collections ===============

class Bundle(FHIRResource):
    """Container for a collection of resources"""
    resourceType: Literal["Bundle"] = Field("Bundle")
    
    # Core bundle information
    identifier: Optional[Identifier] = Field(None, description="Persistent identifier for the bundle")
    type: Literal["document", "message", "transaction", "transaction-response", "batch", "batch-response", "history", "searchset", "collection", "subscription-notification"] = Field(..., description="Bundle type")
    timestamp: Optional[datetime] = Field(None, description="When the bundle was assembled")
    total: Optional[int] = Field(None, description="If search, the total number of matches")
    link: Optional[List[Dict[str, Any]]] = Field(None, description="Links related to this Bundle")
    entry: Optional[List[Dict[str, Any]]] = Field(None, description="Entry in the bundle - will have a resource or information")
    signature: Optional[Dict[str, Any]] = Field(None, description="Digital Signature")
    issues: Optional[Dict[str, Any]] = Field(None, description="Issues with the Bundle")

# =============== MongoDB Integration Models ===============

class FHIRResourceDocument(BaseModel):
    """MongoDB document wrapper for FHIR resources"""
    id: Optional[ObjectId] = Field(None, alias="_id")
    resource_type: str = Field(..., description="FHIR resource type")
    resource_id: Optional[str] = Field(None, description="FHIR resource ID")
    fhir_version: str = Field("5.0.0", description="FHIR version")
    resource_data: Dict[str, Any] = Field(..., description="Complete FHIR resource")
    
    # Blockchain hash and integrity fields
    blockchain_hash: Optional[str] = Field(None, description="SHA-256 blockchain hash of the resource")
    blockchain_previous_hash: Optional[str] = Field(None, description="Previous resource hash in blockchain")
    blockchain_timestamp: Optional[str] = Field(None, description="Timestamp when blockchain hash was generated")
    blockchain_nonce: Optional[str] = Field(None, description="Unique nonce for blockchain hash generation")
    blockchain_merkle_root: Optional[str] = Field(None, description="Merkle root for batch processing")
    blockchain_block_height: Optional[int] = Field(None, description="Block height in the blockchain")
    blockchain_signature: Optional[str] = Field(None, description="Digital signature for authentication")
    blockchain_verified: bool = Field(False, description="Whether blockchain hash has been verified")
    blockchain_verification_date: Optional[datetime] = Field(None, description="Last verification timestamp")
    
    # Metadata for MongoDB optimization
    patient_id: Optional[str] = Field(None, description="Patient reference for indexing")
    organization_id: Optional[str] = Field(None, description="Organization reference for indexing")
    device_id: Optional[str] = Field(None, description="Device reference for indexing")
    encounter_id: Optional[str] = Field(None, description="Encounter reference for indexing")
    
    # Temporal indexing
    effective_datetime: Optional[datetime] = Field(None, description="Clinical effective time")
    recorded_datetime: Optional[datetime] = Field(None, description="When recorded in system")
    
    # Source tracking
    source_system: Optional[str] = Field(None, description="Source system (AVA4, manual, import)")
    source_message_id: Optional[str] = Field(None, description="Original MQTT message ID")
    device_mac_address: Optional[str] = Field(None, description="Source device MAC address")
    
    # Status and lifecycle
    status: Optional[str] = Field(None, description="Resource status")
    is_active: bool = Field(True, description="Resource active status")
    is_deleted: bool = Field(False, description="Soft delete flag")
    
    # Audit fields
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = Field(None, description="User who created")
    updated_by: Optional[str] = Field(None, description="User who last updated")
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str, datetime: lambda v: v.isoformat()}
    }

# =============== FHIR R5 Request/Response Models ===============

class FHIRCreateRequest(BaseModel):
    """Request model for creating FHIR resources"""
    resource: Dict[str, Any] = Field(..., description="FHIR resource data")
    source_system: Optional[str] = Field("manual", description="Source system")
    device_mac_address: Optional[str] = Field(None, description="Source device MAC")

class FHIRSearchParams(BaseModel):
    """Standard FHIR search parameters"""
    id: Optional[str] = Field(None, alias="_id", description="Resource ID")
    lastUpdated: Optional[str] = Field(None, alias="_lastUpdated", description="Last updated date range")
    profile: Optional[str] = Field(None, alias="_profile", description="Profile URL")
    security: Optional[str] = Field(None, alias="_security", description="Security label")
    source: Optional[str] = Field(None, alias="_source", description="Source system")
    tag: Optional[str] = Field(None, alias="_tag", description="Resource tag")
    
    # Common search parameters
    identifier: Optional[str] = Field(None, description="Resource identifier")
    patient: Optional[str] = Field(None, description="Patient reference")
    subject: Optional[str] = Field(None, description="Subject reference")
    encounter: Optional[str] = Field(None, description="Encounter reference")
    date: Optional[str] = Field(None, description="Date range")
    status: Optional[str] = Field(None, description="Resource status")
    
    # Pagination
    count: Optional[int] = Field(10, alias="_count", description="Number of results", ge=1, le=1000)
    offset: Optional[int] = Field(0, alias="_offset", description="Search offset", ge=0)
    sort: Optional[str] = Field(None, alias="_sort", description="Sort parameters")

class FHIRSearchResponse(BaseModel):
    """FHIR search response bundle"""
    resourceType: Literal["Bundle"] = Field("Bundle")
    type: Literal["searchset"] = Field("searchset")
    total: int = Field(..., description="Total matching resources")
    entry: List[Dict[str, Any]] = Field(default_factory=list, description="Search results")
    link: List[Dict[str, str]] = Field(default_factory=list, description="Navigation links") 

# =============== Additional FHIR R5 Resources ===============

class MedicationStatement(BaseModel):
    """FHIR R5 MedicationStatement Resource"""
    resourceType: Literal["MedicationStatement"] = Field("MedicationStatement")
    id: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    status: str  # active | completed | entered-in-error | intended | stopped | on-hold | unknown | not-taken
    statusReason: Optional[List[CodeableConcept]] = None
    category: Optional[List[CodeableConcept]] = None
    medicationCodeableConcept: Optional[CodeableConcept] = None
    medicationReference: Optional[Reference] = None
    subject: Reference
    encounter: Optional[Reference] = None
    effectiveDateTime: Optional[str] = None
    effectivePeriod: Optional[Period] = None
    dateAsserted: Optional[str] = None
    informationSource: Optional[Reference] = None
    derivedFrom: Optional[List[Reference]] = None
    reason: Optional[List[CodeableConcept]] = None
    note: Optional[List[Dict[str, Any]]] = None
    dosage: Optional[List[Dict[str, Any]]] = None
    adherence: Optional[Dict[str, Any]] = None

    model_config = {
        "arbitrary_types_allowed": True
    }

class DiagnosticReport(BaseModel):
    """FHIR R5 DiagnosticReport Resource"""
    resourceType: Literal["DiagnosticReport"] = Field("DiagnosticReport")
    id: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    identifier: Optional[List[Identifier]] = None
    basedOn: Optional[List[Reference]] = None
    status: str  # registered | partial | preliminary | modified | final | amended | corrected | appended | cancelled | entered-in-error | unknown
    category: Optional[List[CodeableConcept]] = None
    code: CodeableConcept
    subject: Reference
    encounter: Optional[Reference] = None
    effectiveDateTime: Optional[str] = None
    effectivePeriod: Optional[Period] = None
    issued: Optional[str] = None
    performer: Optional[List[Reference]] = None
    resultsInterpreter: Optional[List[Reference]] = None
    specimen: Optional[List[Reference]] = None
    result: Optional[List[Reference]] = None
    note: Optional[List[Dict[str, Any]]] = None
    study: Optional[List[Reference]] = None
    supportingInfo: Optional[List[Dict[str, Any]]] = None
    media: Optional[List[Dict[str, Any]]] = None
    composition: Optional[Reference] = None
    conclusion: Optional[str] = None
    conclusionCode: Optional[List[CodeableConcept]] = None

    model_config = {
        "arbitrary_types_allowed": True
    }

class DocumentReference(BaseModel):
    """FHIR R5 DocumentReference Resource"""
    resourceType: Literal["DocumentReference"] = Field("DocumentReference")
    id: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    identifier: Optional[List[Identifier]] = None
    version: Optional[str] = None
    basedOn: Optional[List[Reference]] = None
    status: str  # current | superseded | entered-in-error
    docStatus: Optional[str] = None  # preliminary | final | amended | corrected | appended | cancelled | entered-in-error
    modality: Optional[List[CodeableConcept]] = None
    type: Optional[CodeableConcept] = None
    category: Optional[List[CodeableConcept]] = None
    subject: Optional[Reference] = None
    context: Optional[List[Reference]] = None
    event: Optional[List[Dict[str, Any]]] = None
    bodySite: Optional[List[Dict[str, Any]]] = None
    facilityType: Optional[CodeableConcept] = None
    practiceSetting: Optional[CodeableConcept] = None
    period: Optional[Period] = None
    date: Optional[str] = None
    author: Optional[List[Reference]] = None
    attester: Optional[List[Dict[str, Any]]] = None
    custodian: Optional[Reference] = None
    relatesTo: Optional[List[Dict[str, Any]]] = None
    description: Optional[str] = None
    securityLabel: Optional[List[CodeableConcept]] = None
    content: List[Dict[str, Any]]

    model_config = {
        "arbitrary_types_allowed": True
    }

# =============== FHIR R5 Goal Resource ===============

class Goal(FHIRResource):
    """Describes the intended objective(s) for a patient, group or organization"""
    resourceType: Literal["Goal"] = Field("Goal")
    
    # Core goal information
    identifier: Optional[List[Identifier]] = Field(None, description="External Ids for this goal")
    lifecycleStatus: Literal["proposed", "planned", "accepted", "active", "on-hold", "completed", "cancelled", "entered-in-error", "rejected"] = Field(..., description="Goal lifecycle status")
    achievementStatus: Optional[CodeableConcept] = Field(None, description="in-progress | improving | worsening | no-change | achieved | sustaining | not-achieved | no-progress | not-attainable")
    category: Optional[List[CodeableConcept]] = Field(None, description="E.g. Treatment, dietary, behavioral")
    continuous: Optional[bool] = Field(None, description="After meeting the goal, ongoing activity is needed to sustain the goal objective")
    priority: Optional[CodeableConcept] = Field(None, description="high-priority | medium-priority | low-priority")
    description: CodeableConcept = Field(..., description="Code or text describing goal")
    
    # Subject and context
    subject: Reference = Field(..., description="Who this goal is intended for")
    start: Optional[Union[str, CodeableConcept]] = Field(None, description="When goal pursuit begins")
    target: Optional[List[Dict[str, Any]]] = Field(None, description="Target outcome for the goal")
    statusDate: Optional[str] = Field(None, description="When goal status took effect")
    statusReason: Optional[str] = Field(None, description="Reason for current status")
    source: Optional[Reference] = Field(None, description="Who's responsible for creating Goal?")
    
    # Related information
    addresses: Optional[List[Reference]] = Field(None, description="Issues addressed by this goal")
    note: Optional[List[Dict[str, Any]]] = Field(None, description="Comments about the goal")
    outcome: Optional[List[Dict[str, Any]]] = Field(None, description="What result was achieved regarding the goal?")

# =============== FHIR R5 RelatedPerson Resource ===============

class RelatedPerson(FHIRResource):
    """A person that is related to a patient, but who is not a direct target of care"""
    resourceType: Literal["RelatedPerson"] = Field("RelatedPerson")
    
    # Core related person information
    identifier: Optional[List[Identifier]] = Field(None, description="A human identifier for this person")
    active: Optional[bool] = Field(None, description="Whether this related person's record is in active use")
    patient: Reference = Field(..., description="The patient this related person is related to")
    relationship: Optional[List[CodeableConcept]] = Field(None, description="The relationship of the related person to the patient")
    
    # Demographics
    name: Optional[List[HumanName]] = Field(None, description="A name associated with the person")
    telecom: Optional[List[ContactPoint]] = Field(None, description="A contact detail for the person")
    gender: Optional[Literal["male", "female", "other", "unknown"]] = Field(None, description="Administrative gender")
    birthDate: Optional[str] = Field(None, description="The date on which the related person was born")
    address: Optional[List[Address]] = Field(None, description="Address where the related person can be contacted or visited")
    photo: Optional[List[Dict[str, Any]]] = Field(None, description="Image of the related person")
    
    # Time period and communication
    period: Optional[Period] = Field(None, description="Period of time that this relationship is considered valid")
    communication: Optional[List[Dict[str, Any]]] = Field(None, description="A language which may be used to communicate with the related person")

# =============== FHIR R5 Flag Resource ===============

class Flag(FHIRResource):
    """Prospective warnings of potential issues when providing care to the patient"""
    resourceType: Literal["Flag"] = Field("Flag")
    
    # Core flag information
    identifier: Optional[List[Identifier]] = Field(None, description="Business identifier")
    status: Literal["active", "inactive", "entered-in-error"] = Field(..., description="Flag status")
    category: Optional[List[CodeableConcept]] = Field(None, description="Clinical, administrative, etc.")
    code: CodeableConcept = Field(..., description="Coded or textual message to display to user")
    
    # Subject and context
    subject: Reference = Field(..., description="Who/What is flag about?")
    period: Optional[Period] = Field(None, description="Time period when flag is active")
    encounter: Optional[Reference] = Field(None, description="Alert relevant during encounter")
    
    # Responsible party
    author: Optional[Reference] = Field(None, description="Flag creator")

# =============== FHIR R5 RiskAssessment Resource ===============

class RiskAssessment(FHIRResource):
    """Potential outcomes for a patient or population"""
    resourceType: Literal["RiskAssessment"] = Field("RiskAssessment")
    
    # Core risk assessment information
    identifier: Optional[List[Identifier]] = Field(None, description="Unique identifier for the assessment")
    basedOn: Optional[Reference] = Field(None, description="Request fulfilled by this assessment")
    parent: Optional[Reference] = Field(None, description="Part of this occurrence")
    status: Literal["registered", "preliminary", "final", "amended", "corrected", "cancelled", "entered-in-error", "unknown"] = Field(..., description="Assessment status")
    method: Optional[CodeableConcept] = Field(None, description="Evaluation mechanism")
    code: Optional[CodeableConcept] = Field(None, description="Type of assessment")
    
    # Subject and context
    subject: Reference = Field(..., description="Who/what does assessment apply to?")
    encounter: Optional[Reference] = Field(None, description="Where was assessment performed?")
    occurrence: Optional[Union[datetime, Period]] = Field(None, description="When was assessment made?")
    condition: Optional[Reference] = Field(None, description="Condition assessed")
    
    # Assessment details
    performer: Optional[Reference] = Field(None, description="Who did assessment?")
    reasonCode: Optional[List[CodeableConcept]] = Field(None, description="Why the assessment was necessary")
    reasonReference: Optional[List[Reference]] = Field(None, description="Why the assessment was necessary")
    basis: Optional[List[Reference]] = Field(None, description="Information used in assessment")
    prediction: Optional[List[Dict[str, Any]]] = Field(None, description="Outcome predicted")
    mitigation: Optional[str] = Field(None, description="How to reduce risk")
    note: Optional[List[Dict[str, Any]]] = Field(None, description="Comments on the risk assessment")

# =============== FHIR R5 ServiceRequest Resource ===============

class ServiceRequest(FHIRResource):
    """A request for a service to be performed"""
    resourceType: Literal["ServiceRequest"] = Field("ServiceRequest")
    
    # Core service request information
    identifier: Optional[List[Identifier]] = Field(None, description="Identifiers assigned to this order")
    instantiatesCanonical: Optional[List[str]] = Field(None, description="FHIR Protocol or definition")
    instantiatesUri: Optional[List[str]] = Field(None, description="External protocol or definition")
    basedOn: Optional[List[Reference]] = Field(None, description="What request fulfills")
    replaces: Optional[List[Reference]] = Field(None, description="What request replaces")
    requisition: Optional[Identifier] = Field(None, description="Composite Request ID")
    status: Literal["draft", "active", "on-hold", "revoked", "completed", "entered-in-error", "unknown"] = Field(..., description="Request status")
    intent: Literal["proposal", "plan", "directive", "order", "original-order", "reflex-order", "filler-order", "instance-order", "option"] = Field(..., description="Request intent")
    category: Optional[List[CodeableConcept]] = Field(None, description="Classification of service")
    priority: Optional[Literal["routine", "urgent", "asap", "stat"]] = Field(None, description="Request priority")
    doNotPerform: Optional[bool] = Field(None, description="True if service/procedure should not be performed")
    code: Optional[CodeableConcept] = Field(None, description="What is being requested/ordered")
    orderDetail: Optional[List[Dict[str, Any]]] = Field(None, description="Additional order information")
    
    # Subject and context
    subject: Reference = Field(..., description="Individual or Entity the service is ordered for")
    encounter: Optional[Reference] = Field(None, description="Encounter in which the request was created")
    occurrence: Optional[Union[datetime, Period, Dict[str, Any]]] = Field(None, description="When service should occur")
    asNeeded: Optional[Union[bool, CodeableConcept]] = Field(None, description="Preconditions for service")
    authoredOn: Optional[datetime] = Field(None, description="Date request signed")
    requester: Optional[Reference] = Field(None, description="Who/what is requesting service")
    performerType: Optional[CodeableConcept] = Field(None, description="Performer role")
    performer: Optional[List[Reference]] = Field(None, description="Requested performer")
    location: Optional[List[Reference]] = Field(None, description="Requested location")
    
    # Reasons and additional information
    reason: Optional[List[Dict[str, Any]]] = Field(None, description="Explanation/Justification for procedure or service")
    insurance: Optional[List[Reference]] = Field(None, description="Associated insurance coverage")
    supportingInfo: Optional[List[Reference]] = Field(None, description="Additional clinical information")
    specimen: Optional[List[Reference]] = Field(None, description="Procedure Samples")
    bodySite: Optional[List[CodeableConcept]] = Field(None, description="Location on Body")
    bodyStructure: Optional[List[Reference]] = Field(None, description="Location on Body")
    note: Optional[List[Dict[str, Any]]] = Field(None, description="Comments")
    patientInstruction: Optional[List[Dict[str, Any]]] = Field(None, description="Patient or consumer-oriented instructions")
    relevantHistory: Optional[List[Reference]] = Field(None, description="Request provenance")

# =============== FHIR R5 CarePlan Resource ===============

class CarePlan(FHIRResource):
    """Healthcare plan for patient or group"""
    resourceType: Literal["CarePlan"] = Field("CarePlan")
    
    # Core care plan information
    identifier: Optional[List[Identifier]] = Field(None, description="External Ids for this plan")
    instantiatesCanonical: Optional[List[str]] = Field(None, description="FHIR Protocol or definition")
    instantiatesUri: Optional[List[str]] = Field(None, description="External protocol or definition")
    basedOn: Optional[List[Reference]] = Field(None, description="Fulfills CarePlan")
    replaces: Optional[List[Reference]] = Field(None, description="CarePlan replaced by this CarePlan")
    partOf: Optional[List[Reference]] = Field(None, description="Part of referenced CarePlan")
    status: Literal["draft", "active", "on-hold", "revoked", "completed", "entered-in-error", "unknown"] = Field(..., description="Plan status")
    intent: Literal["proposal", "plan", "order", "option", "directive"] = Field(..., description="Plan intent")
    category: Optional[List[CodeableConcept]] = Field(None, description="Type of plan")
    title: Optional[str] = Field(None, description="Human-friendly name for the care plan")
    description: Optional[str] = Field(None, description="Summary of nature of plan")
    
    # Subject and context
    subject: Reference = Field(..., description="Who the care plan is for")
    encounter: Optional[Reference] = Field(None, description="The Encounter during which this CarePlan was created")
    period: Optional[Period] = Field(None, description="Time period plan covers")
    created: Optional[datetime] = Field(None, description="Date record was first recorded")
    custodian: Optional[Reference] = Field(None, description="Who is the designated responsible party")
    contributor: Optional[List[Reference]] = Field(None, description="Who provided the content of the care plan")
    
    # Care team and goals
    careTeam: Optional[List[Reference]] = Field(None, description="Who's involved in plan?")
    addresses: Optional[List[Dict[str, Any]]] = Field(None, description="Health issues this plan addresses")
    supportingInfo: Optional[List[Reference]] = Field(None, description="Information considered as part of plan")
    goal: Optional[List[Reference]] = Field(None, description="Desired outcome of plan")
    
    # Activities and notes
    activity: Optional[List[Dict[str, Any]]] = Field(None, description="Action to occur or has occurred as part of plan")
    note: Optional[List[Dict[str, Any]]] = Field(None, description="Comments about the plan")

# =============== FHIR R5 Specimen Resource ===============

class Specimen(FHIRResource):
    """Sample for analysis"""
    resourceType: Literal["Specimen"] = Field("Specimen")
    
    # Core specimen information
    identifier: Optional[List[Identifier]] = Field(None, description="External Identifier")
    accessionIdentifier: Optional[Identifier] = Field(None, description="Identifier assigned by the lab")
    status: Optional[Literal["available", "unavailable", "unsatisfactory", "entered-in-error"]] = Field(None, description="Specimen status")
    type: Optional[CodeableConcept] = Field(None, description="Kind of material that forms the specimen")
    
    # Subject and source
    subject: Optional[Reference] = Field(None, description="Where the specimen came from")
    receivedTime: Optional[datetime] = Field(None, description="The time when specimen is received by the testing laboratory")
    parent: Optional[List[Reference]] = Field(None, description="Specimen from which this specimen originated")
    request: Optional[List[Reference]] = Field(None, description="Why the specimen was collected")
    combined: Optional[Literal["grouped", "pooled"]] = Field(None, description="grouped | pooled")
    role: Optional[List[CodeableConcept]] = Field(None, description="The role the specimen serves")
    feature: Optional[List[Dict[str, Any]]] = Field(None, description="The physical feature of a specimen")
    
    # Collection details
    collection: Optional[Dict[str, Any]] = Field(None, description="Collection details")
    processing: Optional[List[Dict[str, Any]]] = Field(None, description="Processing and processing step details")
    container: Optional[List[Dict[str, Any]]] = Field(None, description="Direct container of specimen")
    condition: Optional[List[CodeableConcept]] = Field(None, description="State of the specimen")
    note: Optional[List[Dict[str, Any]]] = Field(None, description="Comments")

# =============== Enhanced FHIR Data Type Models ===============

class Timing(FHIRElement):
    """Specifies an event that may occur multiple times"""
    event: Optional[List[datetime]] = Field(None, description="When the event occurs")
    repeat: Optional[Dict[str, Any]] = Field(None, description="When the event is to occur")
    code: Optional[CodeableConcept] = Field(None, description="C | BID | TID | QID | AM | PM | QD | QOD | +")

class Dosage(FHIRElement):
    """How the medication is/was taken or should be taken"""
    sequence: Optional[int] = Field(None, description="The order of the dosage instructions")
    text: Optional[str] = Field(None, description="Free text dosage instructions")
    additionalInstruction: Optional[List[CodeableConcept]] = Field(None, description="Supplemental instruction or warnings")
    patientInstruction: Optional[str] = Field(None, description="Patient or consumer oriented instructions")
    timing: Optional[Timing] = Field(None, description="When medication should be administered")
    asNeeded: Optional[Union[bool, CodeableConcept]] = Field(None, description="Take as needed")
    site: Optional[CodeableConcept] = Field(None, description="Body site to administer to")
    route: Optional[CodeableConcept] = Field(None, description="How drug should enter body")
    method: Optional[CodeableConcept] = Field(None, description="Technique for administering medication")
    doseAndRate: Optional[List[Dict[str, Any]]] = Field(None, description="Amount of medication administered")
    maxDosePerPeriod: Optional[List[Dict[str, Any]]] = Field(None, description="Upper limit on medication per unit of time")
    maxDosePerAdministration: Optional[Quantity] = Field(None, description="Upper limit on medication per administration")
    maxDosePerLifetime: Optional[Quantity] = Field(None, description="Upper limit on medication per lifetime of the patient")

# =============== FHIR Search Result Enhancement ===============

class FHIRSearchResultEntry(BaseModel):
    """Enhanced search result entry with score and match information"""
    fullUrl: Optional[str] = Field(None, description="URI for resource")
    resource: Optional[Dict[str, Any]] = Field(None, description="A resource in the bundle")
    search: Optional[Dict[str, Any]] = Field(None, description="Search related information")
    request: Optional[Dict[str, Any]] = Field(None, description="Additional execution information")
    response: Optional[Dict[str, Any]] = Field(None, description="Results of execution")

class EnhancedFHIRSearchResponse(BaseModel):
    """Enhanced FHIR search response with additional metadata"""
    resourceType: Literal["Bundle"] = Field("Bundle")
    type: Literal["searchset"] = Field("searchset")
    total: int = Field(..., description="Total matching resources")
    entry: List[FHIRSearchResultEntry] = Field(default_factory=list, description="Search results")
    link: List[Dict[str, str]] = Field(default_factory=list, description="Navigation links")
    
    # Enhanced search metadata
    searchMetadata: Optional[Dict[str, Any]] = Field(None, description="Search performance and quality metrics")
    executionTime: Optional[float] = Field(None, description="Search execution time in milliseconds")
    searchParameters: Optional[Dict[str, Any]] = Field(None, description="Original search parameters")
    warnings: Optional[List[str]] = Field(None, description="Search warnings or limitations") 